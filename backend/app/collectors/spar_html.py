from __future__ import annotations

import json
import re
import time
from collections.abc import Iterator

import httpx

from app.collectors.base import CollectedProduct, utcnow
from app.collectors.shopify import clean_brand
from app.config import settings
from app.matching.normalize import normalize_barcode


_URL_CACHE: dict[str, list[str]] = {}


class BlinkSitemapCollector:
    """
    Blink-powered storefronts (SPAR, Nice Mart): public sitemap + product pages.
    Does not call disallowed /api/* endpoints.
    """

    retailer_id = "blink"
    base_url = ""
    sitemap_index = ""

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(
            timeout=30.0,
            headers={"User-Agent": settings.user_agent, "Accept": "text/html,application/xml"},
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
            if not _slug_matches(url, tokens):
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
        index = self._get_text(self.sitemap_index)
        if not index:
            _URL_CACHE[self.retailer_id] = urls
            return urls
        for sm in re.findall(r"<loc>(.*?)</loc>", index):
            if "sitemap-products" not in sm:
                continue
            xml = self._get_text(sm)
            if not xml:
                continue
            for loc in re.findall(r"<loc>(.*?)</loc>", xml):
                if "/product/" in loc:
                    urls.append(loc.strip())
        _URL_CACHE[self.retailer_id] = urls
        return urls

    def _parse_product(self, url: str) -> CollectedProduct | None:
        html = self._get_text(url)
        if not html:
            return None
        data = self._extract_product_jsonld(html)
        if not data:
            return None

        name = data.get("name")
        if not name:
            return None

        offers = data.get("offers") or {}
        if isinstance(offers, list):
            offers = offers[0] if offers else {}
        if not isinstance(offers, dict):
            offers = {}

        try:
            price = float(offers.get("price"))
        except Exception:
            return None
        if price <= 0:
            return None

        compare_at = None
        try:
            high = offers.get("highPrice")
            if high is not None:
                h = float(high)
                if h > price:
                    compare_at = h
        except Exception:
            pass

        avail_raw = str(offers.get("availability", "")).lower()
        # Be explicit: "outofstock" must not match a naive "instock" substring check.
        if "outofstock" in avail_raw or "out_of_stock" in avail_raw:
            availability = False
        elif "instock" in avail_raw or "in_stock" in avail_raw:
            availability = True
        else:
            availability = False

        sku = data.get("sku")
        barcode = normalize_barcode(
            data.get("gtin13") or data.get("gtin12") or data.get("gtin8") or sku
        )
        image = None
        img = data.get("image")
        if isinstance(img, list) and img:
            image = img[0]
        elif isinstance(img, str):
            image = img

        brand_obj = data.get("brand")
        brand = None
        if isinstance(brand_obj, dict):
            brand = brand_obj.get("name")
        elif isinstance(brand_obj, str):
            brand = brand_obj
        brand = clean_brand(brand, name, self.retailer_id)

        return CollectedProduct(
            retailer=self.retailer_id,
            name=name,
            brand=brand,
            product_type=None,
            sku=sku,
            barcode=barcode,
            price=price,
            compare_at_price=compare_at,
            currency="PKR",
            availability=availability,
            url=url,
            image_url=image,
            city=settings.city,
            collected_at=utcnow(),
            source="blink_html",
        )

    def _extract_product_jsonld(self, html: str) -> dict | None:
        scripts = re.findall(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            html,
            flags=re.IGNORECASE | re.DOTALL,
        )
        for block in scripts:
            block = block.strip()
            if not block:
                continue
            try:
                payload = json.loads(block)
            except Exception:
                continue
            items = payload if isinstance(payload, list) else [payload]
            for item in items:
                if isinstance(item, dict) and str(item.get("@type", "")).lower() == "product":
                    return item
        return None

    def _get_text(self, url: str) -> str | None:
        time.sleep(settings.request_delay_seconds)
        try:
            response = self.client.get(url)
        except Exception:
            return None
        if response.status_code >= 400:
            return None
        return response.text


def _slug_matches(url: str, tokens: list[str]) -> bool:
    """Match query tokens as whole hyphen segments in the product slug."""
    slug = url.rstrip("/").split("/")[-1].lower().replace("_", "-")
    for tok in tokens:
        if not re.search(rf"(^|-){re.escape(tok)}(-|$)", slug):
            return False
    return True


class SparHtmlCollector(BlinkSitemapCollector):
    retailer_id = "spar"
    base_url = "https://store.spar.pk"
    sitemap_index = "https://store.spar.pk/sitemap.xml"


class NiceMartCollector(BlinkSitemapCollector):
    retailer_id = "nice-mart"
    base_url = "https://www.nicemart.pk"
    sitemap_index = "https://www.nicemart.pk/sitemap.xml"
