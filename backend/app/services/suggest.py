from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.matching.normalize import normalize_name
from app.matching.units import parse_size
from app.models import ProductVariant

# Instant autocomplete when catalog DB is empty / cold.
SEED_PRODUCTS: list[tuple[str, str, str | None]] = [
    ("Lays Classic Chips 40 g", "40 g", "Lays"),
    ("Lays Classic Chips 90 g", "90 g", "Lays"),
    ("Lays Masala Chips 18 g", "18 g", "Lays"),
    ("Lays Masala Chips 40 g", "40 g", "Lays"),
    ("Lays Masala Chips 90 g", "90 g", "Lays"),
    ("Lays Masala Chips 120 g", "120 g", "Lays"),
    ("Lays French Cheese Chips 40 g", "40 g", "Lays"),
    ("Lays Wavy Flamin Hot Chips 34 g", "34 g", "Lays"),
    ("Lays Wavy Mexican Chilli 40 g", "40 g", "Lays"),
    ("Lays Salted Chips 40 g", "40 g", "Lays"),
    ("Kurkure Chutney Chaska 22 g", "22 g", "Kurkure"),
    ("Kurkure Masala Munch 22 g", "22 g", "Kurkure"),
    ("Slanty Salted 60 g", "60 g", "Slanty"),
    ("Surf Excel Easy Wash 1 kg", "1 kg", "Surf Excel"),
    ("Surf Excel Easy Wash 2 kg", "2 kg", "Surf Excel"),
    ("Surf Excel Matic Front Load 1 kg", "1 kg", "Surf Excel"),
    ("Surf Excel Matic Top Load 1 kg", "1 kg", "Surf Excel"),
    ("Brite Max Power 1 kg", "1 kg", "Brite"),
    ("Brite Max Power 2 kg", "2 kg", "Brite"),
    ("Ariel Downy 1 kg", "1 kg", "Ariel"),
    ("Ariel Original 1 kg", "1 kg", "Ariel"),
    ("Bonus Washing Powder 1 kg", "1 kg", "Bonus"),
    ("Nestle Milkpak 1 L", "1 L", "Nestle"),
    ("Nestle Everyday Creamer 400 g", "400 g", "Nestle"),
    ("Olpers Milk 1 L", "1 L", "Olpers"),
    ("Dairy Milk Silk 60 g", "60 g", "Cadbury"),
    ("Pepsi 1.5 L", "1.5 L", "Pepsi"),
    ("Coca Cola 1.5 L", "1.5 L", "Coca Cola"),
    ("Sprite 1.5 L", "1.5 L", "Sprite"),
    ("Tapal Danedar 900 g", "900 g", "Tapal"),
    ("Lipton Yellow Label 900 g", "900 g", "Lipton"),
    ("Lifebuoy Total Soap 130 g", "130 g", "Lifebuoy"),
    ("Dettol Soap Original 120 g", "120 g", "Dettol"),
    ("Lux Soft Touch Soap 120 g", "120 g", "Lux"),
    ("Safeguard Soap 175 g", "175 g", "Safeguard"),
    ("Pampers Baby Dry Medium", "pack", "Pampers"),
    ("Huggies Dry Comfort Medium", "pack", "Huggies"),
    ("Sooper Biscuits Family Pack", "pack", "Sooper"),
    ("Prince Biscuits Chocolate", "pack", "Prince"),
    ("Atta Fine 5 kg", "5 kg", None),
    ("Atta Fine 10 kg", "10 kg", None),
    ("Sugar White 1 kg", "1 kg", None),
    ("Cooking Oil 5 L", "5 L", None),
    ("Shan Masala Biryani 60 g", "60 g", "Shan"),
    ("National Masala Biryani 50 g", "50 g", "National"),
]

LIVE_SUGGEST_URLS = (
    "https://springs.com.pk/search/suggest.json",
    "https://alfatah.pk/search/suggest.json",
)

_cache: dict[str, tuple[float, list[dict]]] = {}
_cache_lock = threading.Lock()
_CACHE_TTL_S = 90.0


def _row(
    *,
    label: str,
    size_label: str,
    query: str,
    brand: str | None = None,
    variant_id: int | None = None,
    source: str = "seed",
) -> dict:
    return {
        "variant_id": variant_id,
        "label": label,
        "size_label": size_label,
        "brand": brand,
        "query": query,
        "source": source,
    }


def _cache_get(key: str) -> list[dict] | None:
    with _cache_lock:
        hit = _cache.get(key)
        if not hit:
            return None
        ts, rows = hit
        if time.monotonic() - ts > _CACHE_TTL_S:
            _cache.pop(key, None)
            return None
        return list(rows)


def _cache_set(key: str, rows: list[dict]) -> None:
    with _cache_lock:
        _cache[key] = (time.monotonic(), list(rows))
        if len(_cache) > 400:
            oldest = sorted(_cache.items(), key=lambda kv: kv[1][0])[:80]
            for k, _ in oldest:
                _cache.pop(k, None)


def _seed_suggestions(query: str, limit: int) -> list[dict]:
    q = query.strip().lower()
    ranked: list[tuple[float, tuple[str, str, str | None]]] = []
    for label, size, brand in SEED_PRODUCTS:
        blob = f"{brand or ''} {label}".lower()
        brand_l = (brand or "").lower()
        if brand_l.startswith(q) or label.lower().startswith(q) or q in blob:
            score = 100.0 if brand_l.startswith(q) or label.lower().startswith(q) else 88.0
        elif len(q) <= 3:
            continue
        else:
            score = float(fuzz.partial_ratio(q, blob))
            if score < 78:
                continue
        ranked.append((score, (label, size, brand)))
    ranked.sort(key=lambda item: item[0], reverse=True)
    out: list[dict] = []
    seen: set[str] = set()
    for _, (label, size, brand) in ranked:
        key = label.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(_row(label=label, size_label=size, query=label, brand=brand, source="seed"))
        if len(out) >= limit:
            break
    return out


def _catalog_suggestions(db: Session, query: str, limit: int) -> list[dict]:
    q = query.strip().lower()
    variants = db.scalars(
        select(ProductVariant).options(joinedload(ProductVariant.product))
    ).unique().all()
    if not variants:
        return []

    ranked: list[tuple[float, ProductVariant]] = []
    for variant in variants:
        product = variant.product
        name = (product.name or "").lower()
        brand = (product.brand or "").lower()
        blob = f"{brand} {name} {variant.size_label}".lower()
        if brand.startswith(q) or name.startswith(q) or f" {q}" in f" {blob}":
            score = 100.0 + (20 if brand.startswith(q) else 0)
        elif len(q) <= 3:
            continue
        else:
            score = float(fuzz.token_set_ratio(q, blob))
            if score < 78:
                continue
        ranked.append((score, variant))

    ranked.sort(key=lambda item: item[0], reverse=True)
    if not ranked:
        return []

    seed_brands = {(v.product.brand or "").lower() for _, v in ranked[:4] if v.product.brand}
    if len(q) >= 3:
        seed_brands.add(q)

    out: list[dict] = []
    seen: set[str] = set()
    pool: list[ProductVariant] = [v for _, v in ranked]
    if seed_brands:
        for variant in variants:
            brand = (variant.product.brand or "").lower()
            name = (variant.product.name or "").lower()
            if variant in pool:
                continue
            if brand in seed_brands or any(b in name for b in seed_brands if len(b) >= 3):
                pool.append(variant)

    for variant in pool:
        product = variant.product
        label = f"{product.brand + ' ' if product.brand else ''}{product.name} {variant.size_label}".strip()
        key = label.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(
            _row(
                label=label,
                size_label=variant.size_label,
                query=label,
                brand=product.brand,
                variant_id=variant.id,
                source="catalog",
            )
        )
        if len(out) >= limit:
            break
    return out


def _fetch_shopify_suggest(url: str, query: str, limit: int) -> list[dict]:
    try:
        with httpx.Client(timeout=httpx.Timeout(0.9, connect=0.5)) as client:
            response = client.get(
                url,
                params={"q": query, "resources[type]": "product", "resources[limit]": limit},
                headers={"User-Agent": "PriceWiseSuggest/1.0"},
            )
            if response.status_code != 200:
                return []
            products = (
                response.json()
                .get("resources", {})
                .get("results", {})
                .get("products", [])
            )
    except Exception:  # noqa: BLE001
        return []

    out: list[dict] = []
    seen: set[str] = set()
    for item in products[:limit]:
        title = (item.get("title") or "").strip()
        if not title:
            continue
        key = normalize_name(title)
        if key in seen:
            continue
        seen.add(key)
        size = parse_size(title)
        out.append(
            _row(
                label=title,
                size_label=size.label,
                query=title,
                brand=item.get("vendor"),
                source="live",
            )
        )
    return out


def _live_suggestions(query: str, limit: int) -> list[dict]:
    """Race two Shopify suggest endpoints; keep under ~1s."""
    gathered: list[dict] = []
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [
            pool.submit(_fetch_shopify_suggest, url, query, limit)
            for url in LIVE_SUGGEST_URLS
        ]
        try:
            for fut in as_completed(futures, timeout=1.1):
                try:
                    rows = fut.result() or []
                except Exception:  # noqa: BLE001
                    continue
                if rows:
                    gathered.extend(rows)
                    break
        except TimeoutError:
            pass
        finally:
            for fut in futures:
                fut.cancel()

    ranked = sorted(
        gathered,
        key=lambda row: fuzz.partial_ratio(query.lower(), row["label"].lower()),
        reverse=True,
    )
    out: list[dict] = []
    seen: set[str] = set()
    for row in ranked:
        key = row["label"].lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
        if len(out) >= limit:
            break
    return out


def _is_brand_query(q: str) -> bool:
    ql = q.lower()
    return any(
        (brand or "").lower().startswith(ql) or label.lower().startswith(ql)
        for label, _, brand in SEED_PRODUCTS
    )


def suggest(db: Session, query: str, limit: int = 10) -> list[dict]:
    q = query.strip()
    if len(q) < 2:
        return []

    cache_key = q.lower()
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached[:limit]

    seed = _seed_suggestions(q, limit=limit)
    catalog = _catalog_suggestions(db, q, limit=limit)

    merged: list[dict] = []
    seen: set[str] = set()

    def _add(rows: list[dict]) -> None:
        for row in rows:
            key = row["label"].lower()
            if key in seen:
                continue
            seen.add(key)
            merged.append(row)
            if len(merged) >= limit:
                return

    # Brand queries (lays, surf…) → seed flavors first for instant autocomplete.
    if _is_brand_query(q):
        _add(seed)
        _add(catalog)
    else:
        _add(catalog)
        _add(seed)

    if len(merged) < 4:
        _add(_live_suggestions(q, limit=limit))

    _cache_set(cache_key, merged)
    return merged[:limit]
