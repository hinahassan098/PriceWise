from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from rapidfuzz import fuzz
from sqlalchemy.orm import Session

from app.collectors.base import CollectedProduct
from app.collectors.registry import get_fast_live_collectors
from app.matching.normalize import normalize_name
from app.matching.units import PACK_RE, SIZE_RE, parse_size
from app.services.freshness import freshness, unit_price
from app.services.ingest import ingest_product


RETAILER_NAMES = {
    "springs": "Springs",
    "alfatah": "Al-Fatah",
    "green-valley": "Green Valley",
    "al-madina": "Al-Madina",
    "snapcart": "Snapcart",
    "spar": "SPAR",
    "nice-mart": "Nice Mart",
    "naheed": "Naheed",
    "metro": "Metro",
    "imtiaz": "Imtiaz",
    "carrefour": "Carrefour",
}


def _group_key(item: CollectedProduct) -> str:
    size = parse_size(item.name)
    brand = (item.brand or "").lower().strip()
    name = normalize_name(item.name, item.brand)
    return f"{brand}|{name}|{size.pack_count}|{size.value}|{size.unit}"


def _should_merge(a: dict, b: dict) -> bool:
    """Merge near-identical products across stores (same size, similar name)."""
    asize = parse_size(a["size_label"])
    bsize = parse_size(b["size_label"])
    if asize.pack_count != bsize.pack_count:
        return False
    if asize.unit != bsize.unit:
        return False
    # Allow small size label drift (20g vs 21g) within 10%.
    if asize.value and bsize.value:
        diff = abs(asize.value - bsize.value) / max(asize.value, bsize.value)
        if diff > 0.12:
            return False
    left = f"{a.get('brand') or ''} {a['name']}".lower()
    right = f"{b.get('brand') or ''} {b['name']}".lower()
    return fuzz.token_set_ratio(left, right) >= 86


def _merge_groups(groups: dict[str, dict]) -> dict[str, dict]:
    items = list(groups.values())
    merged: list[dict] = []
    for group in items:
        found = None
        for existing in merged:
            if _should_merge(existing, group):
                found = existing
                break
        if found is None:
            merged.append(group)
            continue
        # Prefer the richer name / image; combine offers.
        found["offers"].extend(group["offers"])
        if not found.get("image_url") and group.get("image_url"):
            found["image_url"] = group["image_url"]
        if found.get("variant_id") is None and group.get("variant_id"):
            found["variant_id"] = group["variant_id"]
        # Deduplicate offers by retailer.
        by_store: dict[str, dict] = {}
        for offer in found["offers"]:
            prev = by_store.get(offer["retailer_id"])
            if prev is None or offer["price"] < prev["price"]:
                by_store[offer["retailer_id"]] = offer
        found["offers"] = list(by_store.values())
    return {g["group_key"]: g for g in merged}


def _offer_dict(item: CollectedProduct, variant_id: int | None = None) -> dict:
    size = parse_size(item.name)
    per = unit_price(item.price, size.pack_count, size.value, size.unit)
    return {
        "retailer_id": item.retailer,
        "retailer_name": RETAILER_NAMES.get(
            item.retailer, item.retailer.replace("-", " ").title()
        ),
        "product_name": item.name,
        "price": item.price,
        "compare_at_price": item.compare_at_price,
        "availability": "in_stock" if item.availability else "out_of_stock",
        "url": item.url,
        "image_url": item.image_url,
        "size_label": size.label,
        "unit_price": per,
        "freshness": freshness(item.collected_at),
        "variant_id": variant_id,
        "source": "live",
    }


def live_search(
    db: Session,
    query: str,
    *,
    persist: bool = True,
    limit_per_store: int = 10,
    retailer_ids: set[str] | None = None,
) -> dict:
    """Query fast Pakistani Shopify storefronts and group offers by product."""
    collectors = get_fast_live_collectors(retailer_ids)
    if not collectors:
        return {
            "query": query,
            "mode": "live_multi_store",
            "parsed": {"name": query, "size_label": None, "pack_count": None},
            "store_errors": {},
            "stores_queried": [],
            "results": [],
            "all_store_prices": [],
        }
    gathered: list[CollectedProduct] = []
    store_errors: dict[str, str] = {}
    # Keep interactive search under Render limits; allow cold sitemap/menu warm.
    overall_timeout_s = 20

    def _run(retailer_id: str, collector):
        try:
            return retailer_id, collector.search_live(query, limit=limit_per_store), None
        except Exception as exc:  # noqa: BLE001
            return retailer_id, [], str(exc)

    pool = ThreadPoolExecutor(max_workers=len(collectors))
    futures = {pool.submit(_run, rid, col): rid for rid, col in collectors.items()}
    try:
        for fut in as_completed(futures, timeout=overall_timeout_s):
            try:
                rid, items, err = fut.result()
            except Exception as exc:  # noqa: BLE001
                rid = futures[fut]
                store_errors[rid] = str(exc)
                continue
            if err:
                store_errors[rid] = err
            gathered.extend(item for item in items if item.price and item.price > 0)
    except TimeoutError:
        for fut, rid in futures.items():
            if not fut.done():
                store_errors.setdefault(rid, "timed out")
    finally:
        pool.shutdown(wait=False, cancel_futures=True)

    # Persist so comparison pages and matching improve over time.
    variant_ids: dict[str, int] = {}
    if persist and gathered:
        for item in gathered[:40]:
            try:
                rp = ingest_product(db, item)
                if rp.variant_id:
                    variant_ids[_group_key(item)] = rp.variant_id
            except Exception:  # noqa: BLE001
                db.rollback()
                continue
        try:
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()

    groups: dict[str, dict] = {}
    for item in gathered:
        key = _group_key(item)
        size = parse_size(item.name)
        offer = _offer_dict(item, variant_ids.get(key))
        if key not in groups:
            groups[key] = {
                "group_key": key,
                "brand": item.brand,
                "name": normalize_name(item.name, item.brand).title() or item.name,
                "size_label": size.label,
                "image_url": item.image_url,
                "variant_id": variant_ids.get(key),
                "offers": [],
            }
        groups[key]["offers"].append(offer)
        if not groups[key]["image_url"] and item.image_url:
            groups[key]["image_url"] = item.image_url
        if groups[key]["variant_id"] is None and variant_ids.get(key):
            groups[key]["variant_id"] = variant_ids[key]

    groups = _merge_groups(groups)

    # Score groups against query.
    parsed = parse_size(query)
    q_has_size = bool(SIZE_RE.search(query) or PACK_RE.search(query))
    q_name = normalize_name(parsed.remainder or query)
    ranked = []
    for group in groups.values():
        blob = f"{group.get('brand') or ''} {group['name']} {group['size_label']}".lower()
        score = float(fuzz.token_set_ratio(query.lower(), blob))
        if q_name and all(tok in blob for tok in q_name.split()):
            score += 12
        if q_has_size:
            gsize = parse_size(group["size_label"])
            if gsize.value == parsed.value and gsize.unit == parsed.unit:
                score += 20
        offers = group["offers"]
        offers.sort(key=lambda o: (0 if o["availability"] == "in_stock" else 1, o["price"]))
        in_stock = [o for o in offers if o["availability"] == "in_stock"]
        pool = in_stock or offers
        cheapest = pool[0]
        group["store_count"] = len(offers)
        group["cheapest"] = cheapest
        group["score"] = round(score, 2)
        group["unit_price"] = cheapest.get("unit_price")
        group["freshness"] = cheapest.get("freshness")
        ranked.append(group)

    ranked.sort(key=lambda g: (-g["score"], g["cheapest"]["price"]))

    # Flat store list: priced product offers only (no "Search on store" placeholders).
    flat_offers = []
    for group in ranked[:20]:
        for offer in group["offers"]:
            if offer.get("price") is None:
                continue
            flat_offers.append(
                {
                    **offer,
                    "brand": group["brand"],
                    "canonical_name": group["name"],
                    "size_label": group["size_label"],
                    "group_key": group["group_key"],
                    "variant_id": group.get("variant_id"),
                }
            )

    flat_offers.sort(
        key=lambda o: (
            0 if o["availability"] == "in_stock" else 1,
            o["price"] if o.get("price") is not None else 10**12,
        )
    )

    return {
        "query": query,
        "mode": "live_multi_store",
        "parsed": {
            "name": parsed.remainder,
            "size_label": parsed.label if q_has_size else None,
            "pack_count": parsed.pack_count if q_has_size else None,
        },
        "store_errors": store_errors,
        "stores_queried": list(collectors.keys()),
        "results": [
            {
                "variant_id": g.get("variant_id"),
                "brand": g.get("brand"),
                "name": g["name"],
                "size_label": g["size_label"],
                "image_url": g.get("image_url"),
                "store_count": g["store_count"],
                "cheapest": {
                    "retailer_id": g["cheapest"]["retailer_id"],
                    "retailer_name": g["cheapest"]["retailer_name"],
                    "price": g["cheapest"]["price"],
                    "availability": g["cheapest"]["availability"],
                    "url": g["cheapest"]["url"],
                },
                "unit_price": g.get("unit_price"),
                "freshness": g.get("freshness"),
                "offers": g["offers"],
                "score": g["score"],
            }
            for g in ranked
        ],
        "all_store_prices": flat_offers,
    }
