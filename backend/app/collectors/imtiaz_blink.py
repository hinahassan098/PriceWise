from __future__ import annotations

import json
import re
import time
from collections.abc import Iterator
from pathlib import Path

import httpx

from app.collectors.base import CollectedProduct, utcnow
from app.collectors.shopify import clean_brand
from app.config import settings

_MENU_CACHE: dict[str, list[dict]] = {}
_MENU_CACHED_AT: dict[str, float] = {}
_MENU_TTL_SECONDS = 15 * 60
_DISK_CACHE_PATH = Path(__file__).resolve().parents[2] / ".cache" / "imtiaz_menu.json"


class ImtiazCollector:
    """
    Imtiaz (Blink / EatMubarak) via public storefront JSON.

    Uses the same /api/menu payload the website loads after city/area selection.
    No robots.txt is published; does not scrape login or checkout paths.
    """

    retailer_id = "imtiaz"
    base_url = "https://shop.imtiaz.com.pk"
    rest_id = "55126"
    app_name = "imtiazsuperstore"
    # Karachi Express branch used by the public storefront.
    rest_br_id = "54943"
    delivery_type = 0

    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client or httpx.Client(
            timeout=httpx.Timeout(20.0, connect=5.0),
            headers={
                "User-Agent": settings.user_agent,
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate",
                "Referer": f"{self.base_url}/",
                "Rest-Id": self.rest_id,
                "App-Name": self.app_name,
                "Host-Name": "shop.imtiaz.com.pk",
            },
            follow_redirects=True,
        )

    def collect(self, max_products: int | None = None) -> Iterator[CollectedProduct]:
        limit = max_products or settings.springs_max_products
        yielded = 0
        for dish in self._dishes():
            product = self._to_product(dish)
            if product is None:
                continue
            yield product
            yielded += 1
            if yielded >= limit:
                return

    def search_live(self, query: str, limit: int = 20) -> list[CollectedProduct]:
        tokens = _search_tokens(query)
        if not tokens:
            return []

        scored: list[tuple[int, CollectedProduct]] = []
        for dish in self._dishes():
            hay = " ".join(
                str(dish.get(k) or "")
                for k in ("name", "brand_name", "desc", "search_tags", "tp_product_code")
            ).lower()
            hay = hay.replace("'", "").replace("'", "")
            # Require brand/name tokens; size tokens (1l, 250ml) are optional boosts.
            if not all(tok in hay for tok in tokens):
                continue
            item = self._to_product(dish)
            if item is None:
                continue
            score = sum(hay.count(tok) for tok in tokens)
            scored.append((score, item))
            if len(scored) >= max(limit * 4, 40):
                # Enough candidates; rank below.
                break

        scored.sort(key=lambda pair: (-pair[0], pair[1].price or 0))
        return [item for _, item in scored[:limit]]

    def _dishes(self) -> list[dict]:
        cached = _MENU_CACHE.get(self.retailer_id)
        cached_at = _MENU_CACHED_AT.get(self.retailer_id, 0.0)
        now = time.time()
        if cached is not None and (now - cached_at) < _MENU_TTL_SECONDS:
            return cached

        disk = self._load_disk_cache(now)
        if disk is not None:
            _MENU_CACHE[self.retailer_id] = disk
            _MENU_CACHED_AT[self.retailer_id] = now
            return disk

        url = (
            f"{self.base_url}/api/menu"
            f"?restId={self.rest_id}&rest_brId={self.rest_br_id}"
            f"&delivery_type={self.delivery_type}"
        )
        try:
            response = self.client.get(url)
        except Exception:
            return cached or []
        if response.status_code >= 400:
            return cached or []
        try:
            payload = response.json()
        except Exception:
            return cached or []
        data = payload.get("data")
        dishes: list[dict] = []
        self._walk_dishes(data, dishes)
        # Prefer unique dish ids; keep first occurrence.
        by_id: dict[int, dict] = {}
        for dish in dishes:
            dish_id = dish.get("id")
            if dish_id is None:
                continue
            by_id.setdefault(int(dish_id), dish)
        unique = list(by_id.values())
        _MENU_CACHE[self.retailer_id] = unique
        _MENU_CACHED_AT[self.retailer_id] = now
        self._save_disk_cache(unique, now)
        return unique

    def _load_disk_cache(self, now: float) -> list[dict] | None:
        try:
            if not _DISK_CACHE_PATH.exists():
                return None
            payload = json.loads(_DISK_CACHE_PATH.read_text(encoding="utf-8"))
            if now - float(payload.get("cached_at", 0)) > _MENU_TTL_SECONDS:
                return None
            dishes = payload.get("dishes")
            return dishes if isinstance(dishes, list) else None
        except Exception:
            return None

    def _save_disk_cache(self, dishes: list[dict], now: float) -> None:
        try:
            _DISK_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            _DISK_CACHE_PATH.write_text(
                json.dumps({"cached_at": now, "dishes": dishes}, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _walk_dishes(self, node: object, out: list[dict]) -> None:
        if isinstance(node, dict):
            if "price" in node and "name" in node and (
                "img_url" in node or "dish_images" in node or "tp_product_code" in node
            ):
                out.append(node)
            for value in node.values():
                self._walk_dishes(value, out)
        elif isinstance(node, list):
            for item in node:
                self._walk_dishes(item, out)

    def _to_product(self, dish: dict) -> CollectedProduct | None:
        name = (dish.get("name") or "").strip()
        if not name:
            return None
        try:
            price = float(dish.get("price"))
        except Exception:
            return None
        if price <= 0:
            return None

        compare_at = None
        try:
            base = float(dish.get("base_price") or 0)
            if base > price:
                compare_at = base
            else:
                discount = float(dish.get("discount_price") or 0)
                if discount > 0:
                    compare_at = round(price + discount, 2)
        except Exception:
            pass

        availability = bool(dish.get("availability", True)) and int(dish.get("status") or 0) == 1
        branch_stock = dish.get("dish_branch_stock")
        if isinstance(branch_stock, dict) and branch_stock.get("stock") is not None:
            try:
                availability = availability and float(branch_stock["stock"]) > 0
            except Exception:
                pass
        elif dish.get("stock") is not None:
            try:
                availability = availability and float(dish["stock"]) > 0
            except Exception:
                pass

        dish_id = dish.get("id")
        sku = str(dish.get("tp_product_code") or dish_id or "") or None
        brand = clean_brand(dish.get("brand_name"), name, self.retailer_id)
        image = dish.get("img_url")
        if not image:
            images = dish.get("dish_images")
            if isinstance(images, list) and images:
                first = images[0]
                if isinstance(first, dict):
                    image = first.get("img_url") or first.get("url")
                elif isinstance(first, str):
                    image = first

        slug = (dish.get("slug") or "").strip() or _slugify(name)
        if dish_id is not None and not slug.endswith(f"-{dish_id}"):
            slug = f"{slug}-{dish_id}"
        url = f"{self.base_url}/product/{slug}"

        return CollectedProduct(
            retailer=self.retailer_id,
            name=name,
            brand=brand,
            product_type=None,
            sku=sku,
            barcode=None,
            price=price,
            compare_at_price=compare_at,
            currency="PKR",
            availability=availability,
            url=url,
            image_url=image,
            city=settings.city,
            collected_at=utcnow(),
            source="imtiaz_menu_json",
        )


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "product"


_SIZE_TOKEN_RE = re.compile(
    r"^(\d+([./]\d+)?)\s*(ml|l|ltr|liter|litre|g|kg|gm|grams?|kgm|pcs?|pack|x)?$",
    re.I,
)
_STOP = {"the", "a", "an", "and", "or", "of", "for", "with", "in", "pk", "pkr"}


def _search_tokens(query: str) -> list[str]:
    """Name/brand tokens only — drop bare sizes like '1', 'l', '1l', '250ml'."""
    raw = query.lower().replace("'", "").replace("'", "")
    parts = [tok for tok in re.split(r"\s+", raw.strip()) if tok]
    out: list[str] = []
    for tok in parts:
        if tok in _STOP:
            continue
        if _SIZE_TOKEN_RE.match(tok):
            continue
        # Join split size like "1" + "l" already handled when separate;
        # also skip pure numeric leftovers.
        if tok.isdigit():
            continue
        if len(tok) == 1 and tok.isalpha():
            continue
        out.append(tok)
    return out
