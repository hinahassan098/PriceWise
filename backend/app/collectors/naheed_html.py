from __future__ import annotations

import re
import time
from collections.abc import Iterator

import httpx

from app.collectors.base import CollectedProduct, utcnow
from app.collectors.shopify import clean_brand
from app.collectors.spar_html import _slug_matches
from app.config import settings

_URL_CACHE: dict[str, list[str]] = {}


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
            if "sitemap_category" in sm:
                continue
            xml = self._get_text(sm)
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
        _URL_CACHE[self.retailer_id] = urls
        return urls

    def _parse_product(self, url: str) -> CollectedProduct | None:
        html = self._get_text(url)
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

    def _get_text(self, url: str) -> str | None:
        time.sleep(settings.request_delay_seconds)
        try:
            response = self.client.get(url)
        except Exception:
            return None
        if response.status_code >= 400:
            return None
        return response.text
