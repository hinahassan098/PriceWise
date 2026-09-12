from __future__ import annotations

import time
from collections.abc import Iterator

import httpx

from app.collectors.base import CollectedProduct, utcnow
from app.config import settings
from app.matching.normalize import normalize_barcode

DEFAULT_QUERIES = [
    "lays",
    "brite",
    "surf excel",
    "ariel",
    "bonus",
    "coke",
    "coca cola",
    "pepsi",
    "sprite",
    "olper",
    "milkpack",
    "nestle milk",
    "nido",
    "tapal",
    "lipton",
    "lifebuoy",
    "dove soap",
    "lux",
    "safeguard",
    "dettol",
    "colgate",
    "pantene",
    "sunsilk",
    "dalda",
    "sundrop",
    "pampers",
    "huggies",
    "sooper",
    "lu biscuits",
    "harpic",
    "fairy",
    "national salt",
    "shan masala",
    "every day milk",
    "nestle yogurt",
]


def clean_brand(vendor: str | None, title: str, retailer_id: str) -> str | None:
    vendor_l = (vendor or "").strip()
    bad = {
        "",
        retailer_id.lower(),
        "alfatah",
        "alfatahstore",
        "al-fatah",
        "springs",
        "store",
    }
    if vendor_l and vendor_l.lower() not in bad:
        return vendor_l
    tokens = [t for t in title.replace("_", " ").split() if t]
    if not tokens:
        return None
    brand = tokens[0].title()
    if len(tokens) > 1 and tokens[1].lower() in {"excel", "cola", "body", "castle"}:
        brand = f"{tokens[0]} {tokens[1]}".title()
    return brand


class ShopifyCollector:
    """Public Shopify storefront JSON collector (products.json + suggest)."""

    def __init__(
        self,
        *,
        retailer_id: str,
        base_url: str,
        client: httpx.Client | None = None,
        search_queries: list[str] | None = None,
        collection_handles: list[str] | None = None,
    ) -> None:
        self.retailer = retailer_id
        self.base = base_url.rstrip("/")
        self.search_queries = search_queries or DEFAULT_QUERIES
        self.collection_handles = collection_handles or []
        self.client = client or httpx.Client(
            timeout=30.0,
            headers={"User-Agent": settings.user_agent, "Accept": "application/json"},
            follow_redirects=True,
        )

    def collect(self, max_products: int | None = None) -> Iterator[CollectedProduct]:
        limit = max_products or settings.springs_max_products
        seen: set[str] = set()
        yielded = 0

        for handle in self.collection_handles:
            for product in self._collection(handle):
                if product.url in seen:
                    continue
                seen.add(product.url)
                yield product
                yielded += 1
                if yielded >= limit:
                    return

        for query in self.search_queries:
            for handle in self.search_handles(query, limit=20):
                if yielded >= limit:
                    return
                product = self._product(handle)
                if product is None or product.url in seen:
                    continue
                seen.add(product.url)
                yield product
                yielded += 1

    def search_live(self, query: str, limit: int = 20) -> list[CollectedProduct]:
        # Prefer suggest.json: it includes the storefront availability customers see,
        # and many product.json payloads omit the `available` field (treated as False).
        suggest_items = self._from_suggest(query, limit=limit)
        if suggest_items:
            return suggest_items

        out: list[CollectedProduct] = []
        seen: set[str] = set()
        for handle in self.search_handles(query, limit=limit):
            product = self._product(handle)
            if product is None or product.url in seen:
                continue
            seen.add(product.url)
            out.append(product)
            if len(out) >= limit:
                break
        return out

    def search_handles(self, query: str, limit: int = 20) -> list[str]:
        payload = self._get_params(
            f"{self.base}/search/suggest.json",
            {"q": query, "resources[type]": "product", "resources[limit]": limit},
        )
        if not payload:
            return []
        products = payload.get("resources", {}).get("results", {}).get("products", [])
        handles: list[str] = []
        for item in products:
            url = item.get("url") or ""
            handle = item.get("handle")
            if not handle and "/products/" in url:
                handle = url.split("/products/")[1].split("?")[0]
            if handle:
                handles.append(handle)
        return handles

    def _from_suggest(self, query: str, limit: int = 20) -> list[CollectedProduct]:
        payload = self._get_params(
            f"{self.base}/search/suggest.json",
            {"q": query, "resources[type]": "product", "resources[limit]": limit},
        )
        if not payload:
            return []
        products = payload.get("resources", {}).get("results", {}).get("products", [])
        out: list[CollectedProduct] = []
        for item in products[:limit]:
            handle = item.get("handle")
            url = item.get("url") or ""
            if not handle and "/products/" in url:
                handle = url.split("/products/")[1].split("?")[0]
            if not handle:
                continue
            title = item.get("title") or handle
            raw_price = item.get("price") if item.get("price") not in (None, "") else item.get("price_min")
            try:
                price = float(raw_price)
            except Exception:
                continue
            if price <= 0:
                continue
            compare = item.get("compare_at_price_min")
            image = None
            if item.get("image"):
                image = item["image"]
            elif item.get("featured_image"):
                image = item["featured_image"].get("url")
            out.append(
                CollectedProduct(
                    retailer=self.retailer,
                    name=title,
                    brand=clean_brand(item.get("vendor"), title, self.retailer),
                    product_type=item.get("type"),
                    sku=f"{self.retailer}-{item.get('id')}",
                    barcode=None,
                    price=price,
                    compare_at_price=float(compare) if compare else None,
                    currency="PKR",
                    availability=bool(item.get("available", True)),
                    url=f"{self.base}/products/{handle}",
                    image_url=image,
                    city=settings.city,
                    collected_at=utcnow(),
                    source="shopify_suggest",
                )
            )
        return out

    def _get(self, url: str) -> dict | list | None:
        return self._get_params(url)

    def _get_params(self, url: str, params: dict | None = None) -> dict | list | None:
        time.sleep(settings.request_delay_seconds)
        response = self.client.get(url, params=params)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        return response.json()

    def _collection(self, handle: str) -> Iterator[CollectedProduct]:
        page = 1
        while True:
            payload = self._get(f"{self.base}/collections/{handle}/products.json?limit=250&page={page}")
            if not payload or not payload.get("products"):
                return
            for raw in payload["products"]:
                yield from self._from_shopify_product(raw)
            page += 1
            if page > 4:
                return

    def _product(self, handle: str) -> CollectedProduct | None:
        payload = self._get(f"{self.base}/products/{handle}.json")
        if not payload or "product" not in payload:
            return None
        items = list(self._from_shopify_product(payload["product"]))
        return items[0] if items else None

    def _from_shopify_product(self, raw: dict) -> Iterator[CollectedProduct]:
        title = raw.get("title") or ""
        handle = raw.get("handle")
        vendor = raw.get("vendor") or None
        product_type = raw.get("product_type")
        image = None
        images = raw.get("images") or []
        if images:
            image = images[0].get("src")
        for variant in raw.get("variants") or []:
            sku = variant.get("sku") or f"{self.retailer}-{raw.get('id')}-{variant.get('id')}"
            try:
                price = float(variant.get("price"))
            except Exception:
                continue
            if price <= 0:
                continue
            compare = variant.get("compare_at_price")
            compare_at = float(compare) if compare else None
            # Shopify often omits `available` on products.json; missing != out of stock.
            if "available" in variant:
                is_available = bool(variant.get("available"))
            else:
                is_available = True
            yield CollectedProduct(
                retailer=self.retailer,
                name=title if variant.get("title") in {None, "Default Title"} else f"{title} {variant.get('title')}",
                brand=clean_brand(vendor, title, self.retailer),
                product_type=product_type,
                sku=sku,
                barcode=normalize_barcode(sku) or normalize_barcode(variant.get("barcode")),
                price=price,
                compare_at_price=compare_at,
                currency="PKR",
                availability=is_available,
                url=f"{self.base}/products/{handle}?variant={variant.get('id')}",
                image_url=image,
                city=settings.city,
                collected_at=utcnow(),
                source="shopify_json",
            )
