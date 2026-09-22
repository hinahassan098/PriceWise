from __future__ import annotations

import json
import re
from collections.abc import Iterator
from urllib.parse import quote_plus

import httpx

from app.collectors.base import CollectedProduct, utcnow
from app.collectors.shopify import DEFAULT_QUERIES, clean_brand
from app.config import settings

try:
    from curl_cffi import requests as curl_requests
except Exception:  # pragma: no cover - optional at import time
    curl_requests = None  # type: ignore[assignment]


class CarrefourCollector:
    """
    Carrefour Pakistan (MAF / mafpak) live search.

    Decoded storefront API surface:
    - Headers required by MAF BFF: appId/appflavour=Reactweb, storeId=mafpak,
      langCode, currency, x-maf-env/revamp/tenant/account.
    - /api/v1/menu and /v1/auto-suggest work with those headers.
    - /api/v8/search is hard-blocked by Akamai (403) even in-browser.
    - Search product cards are delivered via Next.js RSC flight with the same
      product JSON schema (productId, productName, sellingPrice, …).

    Transport: curl_cffi Chrome impersonation + Akamai cookie warm-up.
    """

    retailer_id = "carrefour"
    base_url = "https://www.carrefour.pk"
    market = "mafpak"
    lang = "en"
    # Default guide location: Lahore Walton (matches storefront default).
    latitude = 31.4955
    longitude = 74.3587

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._httpx = client
        self._curl = None
        if client is None and curl_requests is not None:
            self._curl = curl_requests.Session(impersonate="chrome131")
        elif client is None:
            ua = (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            )
            self._httpx = httpx.Client(
                timeout=httpx.Timeout(12.0, connect=4.0),
                headers={
                    "User-Agent": ua,
                    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": f"{self.base_url}/{self.market}/{self.lang}",
                },
                follow_redirects=True,
            )

    def _maf_headers(self, *, accept: str = "application/json, text/plain, */*") -> dict[str, str]:
        """Headers decoded from the MAF React web client (chunk 3864 / 7435)."""
        return {
            "Accept": accept,
            "Origin": self.base_url,
            "Referer": f"{self.base_url}/{self.market}/{self.lang}/",
            "appId": "Reactweb",
            "appflavour": "Reactweb",
            "storeId": self.market,
            "langCode": self.lang,
            "lang": self.lang,
            "currency": "PKR",
            "channel": "web",
            "x-maf-env": "prod",
            "x-maf-revamp": "true",
            "x-maf-tenant": "mafretail",
            "x-maf-account": "c4online",
        }

    def collect(self, max_products: int | None = None) -> Iterator[CollectedProduct]:
        limit = max_products or settings.springs_max_products
        seen: set[str] = set()
        yielded = 0
        for query in DEFAULT_QUERIES:
            for product in self.search_live(query, limit=20):
                key = product.url or product.sku or product.name
                if key in seen:
                    continue
                seen.add(key)
                yield product
                yielded += 1
                if yielded >= limit:
                    return

    def search_live(self, query: str, limit: int = 20) -> list[CollectedProduct]:
        q = query.strip()
        if not q:
            return []
        self._warm_session()
        if getattr(self, "_last_blocked", False):
            return []

        # Prefer JSON APIs when Akamai allows them; fall back to RSC product JSON.
        products = self._search_api(q, limit=limit)
        if not products:
            products = self._search_rsc(q, limit=limit)
        if not products:
            products = self._search_html(q, limit=limit)
        return products[:limit]

    def suggest(self, query: str, limit: int = 10) -> list[str]:
        """MAF /v1/auto-suggest (works with decoded MAF headers)."""
        q = query.strip()
        if not q:
            return []
        self._warm_session()
        try:
            status, text = self._get(
                f"{self.base_url}/v1/auto-suggest",
                params={"query": q, "lang": self.lang, "storeId": self.market},
                headers=self._maf_headers(),
                timeout=15.0,
            )
        except Exception:
            return []
        if status >= 400 or not text:
            return []
        try:
            payload = json.loads(text)
        except Exception:
            return []
        rows = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            return []
        out: list[str] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            label = row.get("asg_text") or row.get("asg_docId")
            if isinstance(label, str) and label.strip():
                out.append(label.strip())
            if len(out) >= limit:
                break
        return out

    def search_url(self, query: str) -> str:
        return (
            f"{self.base_url}/{self.market}/{self.lang}/search"
            f"?keyword={quote_plus(query.strip())}"
        )

    def _warm_session(self) -> None:
        """Hit the homepage so Akamai/bot cookies are present."""
        if getattr(self, "_warmed", False):
            return
        try:
            status, body = self._get(
                f"{self.base_url}/{self.market}/{self.lang}",
                headers={"Accept": "text/html,application/xhtml+xml,*/*;q=0.8"},
                timeout=45.0,
            )
            self._last_blocked = (
                status >= 400
                or len(body) < 500
                or "<p></p>" in body[:120]
                or "Access Denied" in body[:200]
            )
        except Exception:
            self._last_blocked = True
        self._warmed = True

    def _search_rsc(self, query: str, *, limit: int) -> list[CollectedProduct]:
        """
        Next.js RSC flight carries the same product-card JSON the listing API uses.
        This is the working search data path while /api/v8/search stays Akamai-403.
        """
        url = f"{self.base_url}/{self.market}/{self.lang}/search"
        headers = {
            **self._maf_headers(accept="text/x-component"),
            "RSC": "1",
            "Next-Url": f"/{self.market}/{self.lang}/search?keyword={quote_plus(query)}",
        }
        try:
            status, body = self._get(
                url,
                params={"keyword": query, "_rsc": "pw"},
                headers=headers,
                timeout=30.0,
            )
        except Exception:
            return []
        if status >= 400 or len(body) < 200:
            return []
        if "sellingPrice" not in body and "productName" not in body:
            return []
        self._last_blocked = False
        products = self._parse_api_product_cards(body, limit=limit)
        if products:
            return products
        return self._parse_rsc_products(body, limit=limit)

    def _search_html(self, query: str, *, limit: int) -> list[CollectedProduct]:
        url = f"{self.base_url}/{self.market}/{self.lang}/search?keyword={quote_plus(query)}"
        try:
            status, html = self._get(
                url,
                headers={"Accept": "text/html,application/xhtml+xml,*/*;q=0.8"},
                timeout=45.0,
            )
        except Exception:
            self._last_blocked = True
            return []
        if status >= 400:
            self._last_blocked = True
            return []
        if len(html) < 500 or "<p></p>" in html[:120] or "Access Denied" in html[:200]:
            self._last_blocked = True
            return []
        self._last_blocked = False

        cards = self._parse_api_product_cards(html, limit=limit)
        if cards:
            return cards

        rsc = self._parse_rsc_products(html, limit=limit)
        if rsc:
            return rsc

        for blob in _extract_json_blobs(html):
            products = self._parse_api_payload(blob, limit=limit)
            if products:
                return products

        return self._parse_html_cards(html, limit=limit)

    def _search_api(self, query: str, *, limit: int) -> list[CollectedProduct]:
        """Try /api/v8/search with decoded MAF headers (often Akamai-403)."""
        params = {
            "keyword": query,
            "filter": "",
            "sortBy": "relevance",
            "currentPage": "0",
            "pageSize": str(max(limit, 20)),
            "maxPrice": "",
            "minPrice": "",
            "lang": self.lang,
            "displayCurr": "PKR",
            "latitude": str(self.latitude),
            "longitude": str(self.longitude),
            "needFilter": "false",
        }
        headers = {
            **self._maf_headers(),
            "Referer": f"{self.base_url}/{self.market}/{self.lang}/search?keyword={quote_plus(query)}",
            "X-Requested-With": "XMLHttpRequest",
        }
        url = f"{self.base_url}/api/v8/search"
        try:
            status, text = self._get(url, params=params, headers=headers, timeout=12.0)
        except Exception:
            return []
        if status >= 400:
            return []
        text = text.strip()
        if len(text) < 100 or text.startswith("<!DOCTYPE") or text.startswith("<html"):
            return []
        try:
            payload = json.loads(text)
        except Exception:
            return []
        return self._parse_api_payload(payload, limit=limit)

    def _parse_api_product_cards(self, text: str, *, limit: int) -> list[CollectedProduct]:
        """Decode MAF product-card JSON objects embedded in RSC/HTML payloads."""
        from dataclasses import replace

        normalized = text.replace('\\"', '"')
        out: list[CollectedProduct] = []
        seen: set[str] = set()
        for row in _extract_product_card_objects(normalized):
            item = self._row_to_product(row)
            if item is None:
                continue
            key = item.sku or item.url or item.name
            if key in seen:
                continue
            seen.add(key)
            out.append(replace(item, source="carrefour_api"))
            if len(out) >= limit:
                break
        return out

    def _get(
        self,
        url: str,
        *,
        params: dict | None = None,
        headers: dict | None = None,
        timeout: float = 20.0,
    ) -> tuple[int, str]:
        if self._curl is not None:
            response = self._curl.get(url, params=params, headers=headers, timeout=timeout)
            return int(response.status_code), response.text or ""
        assert self._httpx is not None
        response = self._httpx.get(url, params=params, headers=headers, timeout=timeout)
        return int(response.status_code), response.text or ""

    def _parse_rsc_products(self, html: str, *, limit: int) -> list[CollectedProduct]:
        text = html.replace('\\"', '"')
        out: list[CollectedProduct] = []
        seen: set[str] = set()
        for match in re.finditer(
            r'"productId"\s*:\s*"(?P<id>\d+)"(?P<body>.{0,1800}?)(?="productId"|"analytics"|$)',
            text,
            flags=re.S,
        ):
            pid = match.group("id")
            if pid in seen:
                continue
            body = match.group("body")
            name_m = re.search(r'"productName"\s*:\s*"(.*?)"', body)
            price_m = re.search(r'"sellingPrice"\s*:\s*(\d+(?:\.\d+)?)', body)
            if not name_m or not price_m:
                continue
            try:
                price = float(price_m.group(1))
            except Exception:
                continue
            if price <= 0:
                continue
            marked_m = re.search(r'"markedPrice"\s*:\s*(\d+(?:\.\d+)?)', body)
            compare_at = None
            try:
                if marked_m:
                    marked = float(marked_m.group(1))
                    if marked > price:
                        compare_at = marked
            except Exception:
                pass
            url_m = re.search(r'"productUrl"\s*:\s*"(.*?)"', body)
            path = url_m.group(1) if url_m else f"/{self.market}/{self.lang}/p/{pid}"
            url = path if path.startswith("http") else self.base_url + path
            brand_m = re.search(r'"brandName"\s*:\s*"(.*?)"', body)
            brand_raw = brand_m.group(1) if brand_m else None
            if brand_raw and brand_raw.startswith("food_"):
                brand_raw = brand_raw.replace("food_", "", 1).replace("_", " ").title()
            img_m = re.search(
                r'https://cdn\.mafrservices\.com/[^"\\]+\.(?:jpg|jpeg|png|webp)[^"\\]*',
                body,
            )
            seen.add(pid)
            out.append(
                CollectedProduct(
                    retailer=self.retailer_id,
                    name=name_m.group(1),
                    brand=clean_brand(brand_raw, name_m.group(1), self.retailer_id),
                    product_type=None,
                    sku=pid,
                    barcode=None,
                    price=price,
                    compare_at_price=compare_at,
                    currency="PKR",
                    availability=True,
                    url=url.split("?")[0],
                    image_url=img_m.group(0) if img_m else None,
                    city=settings.city,
                    collected_at=utcnow(),
                    source="carrefour_rsc",
                )
            )
            if len(out) >= limit:
                break
        return out

    def _parse_api_payload(self, payload: object, *, limit: int) -> list[CollectedProduct]:
        rows = _find_product_rows(payload)
        out: list[CollectedProduct] = []
        for row in rows:
            item = self._row_to_product(row)
            if item is None:
                continue
            out.append(item)
            if len(out) >= limit:
                break
        return out

    def _row_to_product(self, row: dict) -> CollectedProduct | None:
        name = (
            row.get("name")
            or row.get("title")
            or row.get("productName")
            or row.get("description")
        )
        if isinstance(name, dict):
            name = name.get("en") or name.get("name") or name.get("label")
        if not isinstance(name, str) or not name.strip():
            return None
        name = name.strip()

        price, compare_at, currency = _extract_price(row)
        if price is None or price <= 0:
            return None

        product_id = str(
            row.get("id")
            or row.get("productId")
            or row.get("sku")
            or row.get("ean")
            or row.get("gtin")
            or ""
        )
        url = _extract_url(row, self.base_url, self.market, self.lang, product_id)
        if not url:
            return None

        brand_raw = row.get("brand")
        if isinstance(brand_raw, dict):
            brand_raw = brand_raw.get("name") or brand_raw.get("label")
        brand = clean_brand(brand_raw if isinstance(brand_raw, str) else None, name, self.retailer_id)

        image = _extract_image(row)
        availability = _extract_availability(row)
        sku = product_id or None
        barcode = None
        for key in ("ean", "gtin", "barcode"):
            val = row.get(key)
            if val:
                barcode = str(val)
                break

        return CollectedProduct(
            retailer=self.retailer_id,
            name=name,
            brand=brand,
            product_type=None,
            sku=sku,
            barcode=barcode,
            price=price,
            compare_at_price=compare_at,
            currency=currency or "PKR",
            availability=availability,
            url=url,
            image_url=image,
            city=settings.city,
            collected_at=utcnow(),
            source="carrefour_maf",
        )

    def _parse_html_cards(self, html: str, *, limit: int) -> list[CollectedProduct]:
        out: list[CollectedProduct] = []
        pattern = re.compile(
            rf'href=["\']({re.escape(self.base_url)}/{self.market}/{self.lang}/[^"\']+/p/(\d+)|'
            rf'/{self.market}/{self.lang}/[^"\']+/p/(\d+))["\']',
            re.I,
        )
        seen: set[str] = set()
        for match in pattern.finditer(html):
            href = match.group(1)
            pid = match.group(2) or match.group(3)
            if not pid or pid in seen:
                continue
            seen.add(pid)
            if href.startswith("/"):
                href = self.base_url + href
            window = html[match.end() : match.end() + 800]
            price_m = re.search(r"PKR\s*([\d,]+(?:\.\d+)?)", window, re.I)
            if not price_m:
                continue
            try:
                price = float(price_m.group(1).replace(",", ""))
            except Exception:
                continue
            if price <= 0:
                continue
            name_m = re.search(
                r'(?:alt|title|aria-label)=["\']([^"\']{4,120})["\']',
                html[max(0, match.start() - 400) : match.end() + 400],
                re.I,
            )
            name = name_m.group(1).strip() if name_m else f"Carrefour product {pid}"
            out.append(
                CollectedProduct(
                    retailer=self.retailer_id,
                    name=name,
                    brand=clean_brand(None, name, self.retailer_id),
                    product_type=None,
                    sku=pid,
                    barcode=None,
                    price=price,
                    compare_at_price=None,
                    currency="PKR",
                    availability=True,
                    url=href.split("?")[0],
                    image_url=None,
                    city=settings.city,
                    collected_at=utcnow(),
                    source="carrefour_html",
                )
            )
            if len(out) >= limit:
                break
        return out


def _extract_product_card_objects(text: str) -> list[dict]:
    """
    Walk RSC/HTML text and json.loads MAF product-card objects.

    Cards look like:
      {..., "productId":"310516", "productName":"...", "sellingPrice":195, ...}
    """
    out: list[dict] = []
    seen: set[str] = set()
    for match in re.finditer(r'"productId"\s*:\s*"(\d+)"', text):
        pid = match.group(1)
        if pid in seen:
            continue
        start = None
        depth = 0
        j = match.start()
        while j >= 0:
            ch = text[j]
            if ch == "}":
                depth += 1
            elif ch == "{":
                if depth == 0:
                    start = j
                    break
                depth -= 1
            j -= 1
        if start is None:
            continue
        depth = 0
        end = None
        for k in range(start, min(len(text), start + 6000)):
            ch = text[k]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = k
                    break
        if end is None:
            continue
        try:
            obj = json.loads(text[start : end + 1])
        except Exception:
            continue
        if not isinstance(obj, dict):
            continue
        if "sellingPrice" not in obj and "productName" not in obj:
            continue
        seen.add(pid)
        out.append(obj)
    return out


def _extract_json_blobs(html: str) -> list[object]:
    blobs: list[object] = []
    for match in re.finditer(
        r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        html,
        flags=re.I | re.S,
    ):
        try:
            blobs.append(json.loads(match.group(1)))
        except Exception:
            pass
    for match in re.finditer(
        r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        flags=re.I | re.S,
    ):
        try:
            blobs.append(json.loads(match.group(1)))
        except Exception:
            pass
    for match in re.finditer(r'\{\s*"products"\s*:\s*\[', html):
        snippet = html[match.start() : match.start() + 500_000]
        end = _balanced_object_end(snippet)
        if end is None:
            continue
        try:
            blobs.append(json.loads(snippet[: end + 1]))
        except Exception:
            continue
    return blobs


def _balanced_object_end(text: str) -> int | None:
    depth = 0
    in_str = False
    escape = False
    for i, ch in enumerate(text):
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
    return None


def _find_product_rows(payload: object) -> list[dict]:
    rows: list[dict] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key in ("products", "productsList", "items", "hits", "results"):
                val = node.get(key)
                if isinstance(val, list):
                    for item in val:
                        if isinstance(item, dict) and _looks_like_product(item):
                            rows.append(item)
            if _looks_like_product(node):
                rows.append(node)
            for val in node.values():
                walk(val)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload)
    seen: set[str] = set()
    unique: list[dict] = []
    for row in rows:
        key = str(
            row.get("id")
            or row.get("productId")
            or row.get("sku")
            or row.get("url")
            or row.get("name")
            or id(row)
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def _looks_like_product(row: dict) -> bool:
    has_name = any(k in row for k in ("name", "title", "productName"))
    has_price = any(k in row for k in ("price", "priceValue", "offers", "sellingPrice"))
    has_id = any(k in row for k in ("id", "productId", "sku", "ean", "gtin"))
    return bool(has_name and (has_price or has_id))


def _extract_price(row: dict) -> tuple[float | None, float | None, str | None]:
    currency = str(row.get("currency") or "PKR")
    price = None
    compare = None

    raw = row.get("price")
    if isinstance(raw, (int, float, str)):
        try:
            price = float(str(raw).replace(",", ""))
        except Exception:
            price = None
    elif isinstance(raw, dict):
        currency = str(raw.get("currency") or raw.get("currencyCode") or currency)
        for key in ("price", "value", "amount", "sellingPrice", "discountedPrice"):
            if raw.get(key) is not None:
                try:
                    price = float(str(raw[key]).replace(",", ""))
                    break
                except Exception:
                    pass
        for key in ("originalPrice", "wasPrice", "regularPrice", "maxPrice", "markedPrice"):
            if raw.get(key) is not None:
                try:
                    compare = float(str(raw[key]).replace(",", ""))
                    break
                except Exception:
                    pass

    if price is None:
        for key in ("priceValue", "sellingPrice", "currentPrice"):
            if row.get(key) is not None:
                try:
                    price = float(str(row[key]).replace(",", ""))
                    break
                except Exception:
                    pass

    if compare is None:
        for key in ("originalPrice", "regularPrice", "compareAtPrice", "wasPrice", "markedPrice"):
            if row.get(key) is not None:
                try:
                    compare = float(str(row[key]).replace(",", ""))
                    break
                except Exception:
                    pass

    if compare is not None and price is not None and compare <= price:
        compare = None
    return price, compare, currency


def _extract_url(
    row: dict, base_url: str, market: str, lang: str, product_id: str
) -> str | None:
    for key in ("url", "productUrl", "canonicalUrl", "shareUrl"):
        val = row.get(key)
        if isinstance(val, str) and val.strip():
            url = val.strip()
            if url.startswith("/"):
                return base_url + url
            return url
    links = row.get("links")
    if isinstance(links, dict):
        for key in ("productUrl", "self", "product"):
            val = links.get(key)
            if isinstance(val, dict):
                href = val.get("href")
                if isinstance(href, str) and href:
                    return href if href.startswith("http") else base_url + href
            elif isinstance(val, str) and val:
                return val if val.startswith("http") else base_url + val
    if product_id:
        slug = _slugify(str(row.get("name") or row.get("title") or "product"))
        return f"{base_url}/{market}/{lang}/{slug}/p/{product_id}"
    return None


def _extract_image(row: dict) -> str | None:
    for key in ("image", "imageUrl", "image_url", "thumbnail", "thumb"):
        val = row.get(key)
        if isinstance(val, str) and val.startswith("http"):
            return val
        if isinstance(val, dict):
            for sub in ("url", "src", "href", "large", "medium"):
                if isinstance(val.get(sub), str) and val[sub].startswith("http"):
                    return val[sub]
        if isinstance(val, list) and val:
            first = val[0]
            if isinstance(first, str) and first.startswith("http"):
                return first
            if isinstance(first, dict):
                for sub in ("url", "src", "href"):
                    if isinstance(first.get(sub), str) and first[sub].startswith("http"):
                        return first[sub]
    images = row.get("images")
    if isinstance(images, list) and images:
        first = images[0]
        if isinstance(first, str) and first.startswith("http"):
            return first
        if isinstance(first, dict):
            for sub in ("url", "src", "href"):
                if isinstance(first.get(sub), str) and first[sub].startswith("http"):
                    return first[sub]
    return None


def _extract_availability(row: dict) -> bool:
    for key in ("isAvailable", "available", "inStock", "isInStock"):
        if key in row:
            return bool(row[key])
    avail = row.get("availability")
    if isinstance(avail, bool):
        return avail
    if isinstance(avail, str):
        low = avail.lower()
        if "outofstock" in low or "out_of_stock" in low:
            return False
        if "instock" in low or "in_stock" in low or "available" in low:
            return True
    if isinstance(avail, dict):
        for key in ("isAvailable", "available", "inStock"):
            if key in avail:
                return bool(avail[key])
    stock = row.get("stock")
    if isinstance(stock, (int, float)):
        return stock > 0
    return True


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "product"
