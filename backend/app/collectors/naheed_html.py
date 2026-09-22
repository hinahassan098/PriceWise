from __future__ import annotations

import html as html_lib
import json
import re
import time
from collections.abc import Iterator
from pathlib import Path

import httpx

from app.collectors.base import CollectedProduct, utcnow
from app.collectors.shopify import clean_brand
from app.collectors.spar_html import _slug_matches, _live_tokens
from app.config import settings

_URL_CACHE: dict[str, list[str]] = {}
_DISK_CACHE = Path(__file__).resolve().parents[2] / ".cache" / "naheed_urls.json"
_DISK_TTL_SECONDS = 6 * 60 * 60


class NaheedHtmlCollector:
    """
    Naheed Magento storefront via public sitemap + SEO product pages.
    Avoids robots-disallowed /catalogsearch/ and /catalog/product/view/ paths.
    """

    retailer_id = "naheed"
    base_url = "https://www.naheed.pk"
    sitemap_index = "https://www.naheed.pk/pub/media/sitemap.xml"

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(
            timeout=httpx.Timeout(12.0, connect=4.0),
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xml",
            },
            follow_redirects=True,
        )

    def collect(self, max_products: int | None = None) -> Iterator[CollectedProduct]:
        limit = max_products or settings.springs_max_products
        yielded = 0
        for url in self._product_urls():
            product = self._parse_product(url, pause=True)
            if product is None:
                continue
            yield product
            yielded += 1
            if yielded >= limit:
                return

    def search_live(self, query: str, limit: int = 20) -> list[CollectedProduct]:
        tokens = _live_tokens(query)
        if not tokens:
            return []
        out: list[CollectedProduct] = []
        # Cap how many product pages we hit during interactive search.
        max_fetches = max(limit, 8)
        fetches = 0
        for url in self._product_urls():
            if not _slug_matches(url, tokens):
                continue
            item = self._parse_product(url, pause=False)
            fetches += 1
            if item is not None:
                out.append(item)
            if len(out) >= limit or fetches >= max_fetches:
                break
        return out

    def warm_url_cache(self) -> int:
        return len(self._product_urls())

    def _product_urls(self) -> list[str]:
        cached = _URL_CACHE.get(self.retailer_id)
        if cached is not None:
            return cached
        disk = self._load_disk()
        if disk is not None:
            _URL_CACHE[self.retailer_id] = disk
            return disk

        urls: list[str] = []
        index = self._get_text(self.sitemap_index, pause=False)
        if not index:
            # Do not poison memory/disk with an empty failed fetch.
            return urls
        for sm in re.findall(r"<loc>(.*?)</loc>", index):
            # sitemap_001 is mostly category trees; products start later.
            if "sitemap_category" in sm or sm.rstrip("/").endswith("sitemap_001.xml"):
                continue
            xml = self._get_text(sm, pause=False)
            if not xml:
                continue
            for loc in re.findall(r"<loc>(.*?)</loc>", xml):
                loc = loc.strip()
                if not loc.startswith(self.base_url):
                    continue
                # Prefer flat SEO product URLs (avoid deep category trees).
                path = loc[len(self.base_url) :].strip("/")
                if not path or "/" in path:
                    continue
                if path.startswith("pub/") or "." in path.split("-")[0]:
                    continue
                urls.append(loc)
        if not urls:
            return urls
        _URL_CACHE[self.retailer_id] = urls
        self._save_disk(urls)
        return urls

    def _load_disk(self) -> list[str] | None:
        try:
            if not _DISK_CACHE.exists():
                return None
            payload = json.loads(_DISK_CACHE.read_text(encoding="utf-8"))
            if time.time() - float(payload.get("cached_at", 0)) > _DISK_TTL_SECONDS:
                return None
            urls = payload.get("urls")
            return urls if isinstance(urls, list) and urls else None
        except Exception:
            return None

    def _save_disk(self, urls: list[str]) -> None:
        try:
            _DISK_CACHE.parent.mkdir(parents=True, exist_ok=True)
            _DISK_CACHE.write_text(
                json.dumps({"cached_at": time.time(), "urls": urls}),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _parse_product(self, url: str, *, pause: bool) -> CollectedProduct | None:
        html = self._get_text(url, pause=pause)
        if not html:
            return None

        title_m = re.search(
            r'data-ui-id="page-title-wrapper"[^>]*>([^<]+)',
            html,
            flags=re.I,
        )
        name = title_m.group(1).strip() if title_m else None
        if not name:
            og = re.search(r'property="og:title" content="([^"]+)"', html, flags=re.I)
            name = og.group(1).strip() if og else None
        if not name:
            return None
        name = html_lib.unescape(name).strip()

        price_m = re.search(
            r'property="product:price:amount" content="([^"]+)"',
            html,
            flags=re.I,
        ) or re.search(r'itemprop="price" content="([^"]+)"', html, flags=re.I)
        if not price_m:
            return None
        try:
            price = float(price_m.group(1).replace(",", ""))
        except Exception:
            return None
        if price <= 0:
            return None

        image = None
        img_m = re.search(r'property="og:image" content="([^"]+)"', html, flags=re.I)
        if img_m:
            image = img_m.group(1)

        sku = None
        sku_m = re.search(r'itemprop="sku"[^>]*content="([^"]+)"', html, flags=re.I)
        if sku_m:
            sku = sku_m.group(1)
        else:
            sku_m = re.search(r'"sku"\s*:\s*"([^"]+)"', html)
            if sku_m:
                sku = sku_m.group(1)

        availability = True
        low = html.lower()
        if "out of stock" in low or 'availability">out of stock' in low:
            availability = False

        return CollectedProduct(
            retailer=self.retailer_id,
            name=name,
            brand=clean_brand(None, name, self.retailer_id),
            product_type=None,
            sku=sku,
            barcode=None,
            price=price,
            compare_at_price=None,
            currency="PKR",
            availability=availability,
            url=url.split("?")[0],
            image_url=image,
            city=settings.city,
            collected_at=utcnow(),
            source="naheed_html",
        )

    def _get_text(self, url: str, *, pause: bool) -> str | None:
        if pause:
            time.sleep(settings.request_delay_seconds)
        try:
            response = self.client.get(url)
        except Exception:
            return None
        if response.status_code >= 400:
            return None
        return response.text
