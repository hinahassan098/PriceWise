from __future__ import annotations

import json
import re
import time
from collections.abc import Iterator

import httpx

from app.collectors.base import CollectedProduct, utcnow
from app.collectors.shopify import clean_brand
from app.config import settings

_URL_CACHE: dict[str, list[str]] = {}
_BUILD_ID: str | None = None


class MetroNextCollector:
    """
    Metro Online via public sitemap + product page / Next.js data.
    Uses only www.metro-online.pk (not admin hosts).
    """

    retailer_id = "metro"
    base_url = "https://www.metro-online.pk"
    sitemap_index = "https://www.metro-online.pk/sitemap.xml"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(
            timeout=30.0,
            headers={"User-Agent": settings.user_agent, "Accept": "text/html,application/json"},
            follow_redirects=True,
        )

    def collect(self, max_products: int | None = None) -> Iterator[CollectedProduct]:
        limit = max_products or settings.springs_max_products
        yielded = 0
        for url in self._product_urls():
            product = self._parse_product(url)
            if product is None:
                continue
            yield product
            yielded += 1
            if yielded >= limit:
                return

    def search_live(self, query: str, limit: int = 20) -> list[CollectedProduct]:
        tokens = [tok for tok in re.split(r"\s+", query.lower().strip()) if tok]
        if not tokens:
            return []
        out: list[CollectedProduct] = []
        for url in self._product_urls():
            # Detail URLs include product name path segments before the numeric id.
            low = url.lower().replace("-", " ").replace("/", " ")
            if not all(tok in low for tok in tokens):
                continue
            item = self._parse_product(url)
            if item is None:
                continue
            out.append(item)
            if len(out) >= limit:
                break
        return out

    def _product_urls(self) -> list[str]:
        cached = _URL_CACHE.get(self.retailer_id)
        if cached is not None:
            return cached
        urls: list[str] = []
        xml = self._get_text(self.sitemap_index)
        if not xml:
            _URL_CACHE[self.retailer_id] = urls
            return urls
        for loc in re.findall(r"<loc>(.*?)</loc>", xml):
            loc = loc.strip()
            if "/detail/" in loc:
                urls.append(loc)
        _URL_CACHE[self.retailer_id] = urls
        return urls

    def _parse_product(self, url: str) -> CollectedProduct | None:
        repo = self._fetch_repo(url)
        if not isinstance(repo, dict):
            return None
        name = repo.get("product_name")
        if not name:
            return None

        price = repo.get("sell_price")
        if price is None:
            price = repo.get("price")
        try:
            price_f = float(price)
        except Exception:
            return None
        if price_f <= 0:
            return None

        compare = repo.get("price")
        compare_at = None
        try:
            if compare is not None and float(compare) > price_f:
                compare_at = float(compare)
        except Exception:
            pass

        active = bool(repo.get("active", True))
        stock = repo.get("available_stock")
        try:
            stock_n = float(stock) if stock is not None else 1
        except Exception:
            stock_n = 1
        availability = active and stock_n > 0

        image = repo.get("url") or repo.get("url_r2")
        sku = str(repo.get("product_code_app") or repo.get("id") or "")
        brand = clean_brand(repo.get("brand_name"), name, self.retailer_id)

        return CollectedProduct(
            retailer=self.retailer_id,
            name=name,
            brand=brand,
            product_type=repo.get("product_assortment_type"),
            sku=sku or None,
            barcode=None,
            price=price_f,
            compare_at_price=compare_at,
            currency="PKR",
            availability=availability,
            url=url,
            image_url=image,
            city=settings.city,
            collected_at=utcnow(),
            source="metro_next",
        )

    def _fetch_repo(self, url: str) -> dict | None:
        build = self._ensure_build_id()
        if build:
            path = url.replace(self.base_url, "")
            if not path.startswith("/"):
                path = "/" + path
            next_url = f"{self.base_url}/_next/data/{build}{path}.json"
            payload = self._get_json(next_url)
            if isinstance(payload, dict):
                repo = payload.get("pageProps", {}).get("repo")
                if isinstance(repo, dict) and repo.get("product_name"):
                    return repo

        html = self._get_text(url)
        if not html:
            return None
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
        if not m:
            return None
        try:
            data = json.loads(m.group(1))
        except Exception:
            return None
        if not self._build_cached():
            self._set_build(data.get("buildId"))
        repo = data.get("props", {}).get("pageProps", {}).get("repo")
        return repo if isinstance(repo, dict) else None

    def _build_cached(self) -> str | None:
        return _BUILD_ID

    def _set_build(self, build_id: str | None) -> None:
        global _BUILD_ID
        if build_id:
            _BUILD_ID = build_id

    def _ensure_build_id(self) -> str | None:
        if _BUILD_ID:
            return _BUILD_ID
        html = self._get_text(f"{self.base_url}/")
        if not html:
            return None
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
        if not m:
            return None
        try:
            self._set_build(json.loads(m.group(1)).get("buildId"))
        except Exception:
            return None
        return _BUILD_ID

    def _get_text(self, url: str) -> str | None:
        time.sleep(settings.request_delay_seconds)
        try:
            response = self.client.get(url)
        except Exception:
            return None
        if response.status_code >= 400:
            return None
        return response.text

    def _get_json(self, url: str) -> dict | list | None:
        time.sleep(settings.request_delay_seconds)
        try:
            response = self.client.get(url)
        except Exception:
            return None
        if response.status_code >= 400:
            return None
        ctype = response.headers.get("content-type", "")
        if "json" not in ctype and not response.text.lstrip().startswith("{"):
            return None
        try:
            return response.json()
        except Exception:
            return None
