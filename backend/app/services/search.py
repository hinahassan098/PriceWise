from __future__ import annotations

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.matching.normalize import normalize_name
from app.matching.units import PACK_RE, SIZE_RE, parse_size
from app.models import ProductVariant, RetailerProduct
from app.services.freshness import freshness, unit_price


def _tokens(query: str) -> list[str]:
    size = parse_size(query)
    name = normalize_name(size.remainder or query)
    return [token for token in name.split() if token]


def search_variants(
    db: Session,
    query: str,
    *,
    retailer_id: str | None = None,
    in_stock: bool | None = None,
    limit: int = 30,
) -> dict:
    parsed = parse_size(query)
    tokens = _tokens(query)
    q_has_size = bool(SIZE_RE.search(query) or PACK_RE.search(query))

    variants = db.scalars(
        select(ProductVariant).options(
            joinedload(ProductVariant.product),
            joinedload(ProductVariant.retailer_products).joinedload(RetailerProduct.retailer),
        )
    ).unique().all()

    ranked: list[tuple[float, ProductVariant]] = []
    for variant in variants:
        blob = variant.search_text or ""
        if tokens and not all(token in blob for token in tokens):
            score = fuzz.token_set_ratio(query.lower(), blob)
            if score < 70:
                continue
        else:
            score = 90 + fuzz.token_set_ratio(query.lower(), blob) / 10
        if q_has_size:
            if float(variant.size_value) == float(parsed.value) and variant.size_unit == parsed.unit:
                score += 15
            elif parsed.unit != variant.size_unit:
                score -= 8
        ranked.append((score, variant))

    ranked.sort(key=lambda item: item[0], reverse=True)
    results = []
    for score, variant in ranked[:limit]:
        card = _variant_card(variant, retailer_id=retailer_id, in_stock=in_stock)
        if card is None:
            continue
        card["score"] = round(score, 2)
        results.append(card)

    flat_offers = []
    for row in results:
        for offer in row.get("offers") or []:
            flat_offers.append(
                {
                    **offer,
                    "brand": row.get("brand"),
                    "canonical_name": row["name"],
                    "size_label": row["size_label"],
                    "variant_id": row.get("variant_id"),
                }
            )
    flat_offers.sort(key=lambda o: (0 if o["availability"] == "in_stock" else 1, o["price"]))

    return {
        "query": query,
        "mode": "catalog",
        "parsed": {
            "name": parsed.remainder,
            "size_label": parsed.label if q_has_size else None,
            "pack_count": parsed.pack_count if q_has_size else None,
        },
        "results": results,
        "all_store_prices": flat_offers,
    }


def suggest(db: Session, query: str, limit: int = 8) -> list[dict]:
    if not query.strip():
        return []
    data = search_variants(db, query, limit=limit)
    return [
        {
            "variant_id": row["variant_id"],
            "label": f"{row['brand'] + ' ' if row['brand'] else ''}{row['name']} {row['size_label']}".strip(),
            "size_label": row["size_label"],
        }
        for row in data["results"][:limit]
    ]


def _variant_card(
    variant: ProductVariant,
    *,
    retailer_id: str | None = None,
    in_stock: bool | None = None,
) -> dict | None:
    offers = []
    for rp in variant.retailer_products:
        if rp.match_decision not in {"auto", "review"} or rp.variant_id != variant.id:
            continue
        if rp.match_decision == "review" and rp.match_confidence and float(rp.match_confidence) < 95:
            continue
        if retailer_id and rp.retailer_id != retailer_id:
            continue
        if in_stock is True and rp.availability != "in_stock":
            continue
        if in_stock is False and rp.availability == "in_stock":
            continue
        if rp.current_price is None:
            continue
        if float(rp.current_price) <= 0:
            continue
        offers.append(rp)
    if not offers:
        return None
    in_stock_offers = [o for o in offers if o.availability == "in_stock"]
    pool = in_stock_offers or offers
    cheapest = min(pool, key=lambda row: float(row.current_price))
    per = unit_price(float(cheapest.current_price), int(variant.pack_count), float(variant.size_value), variant.size_unit)
    product = variant.product
    offer_rows = []
    for rp in offers:
        offer_rows.append(
            {
                "retailer_id": rp.retailer_id,
                "retailer_name": rp.retailer.name,
                "product_name": rp.retailer_product_name,
                "price": float(rp.current_price),
                "availability": rp.availability,
                "url": rp.retailer_product_url,
                "image_url": rp.image_url,
                "unit_price": unit_price(
                    float(rp.current_price),
                    int(variant.pack_count),
                    float(variant.size_value),
                    variant.size_unit,
                ),
                "freshness": freshness(rp.last_checked_at),
            }
        )
    offer_rows.sort(key=lambda row: (0 if row["availability"] == "in_stock" else 1, row["price"]))
    return {
        "variant_id": variant.id,
        "product_id": product.id,
        "brand": product.brand,
        "name": product.name,
        "size_label": variant.size_label,
        "image_url": product.image_url,
        "store_count": len(offer_rows),
        "cheapest": {
            "retailer_id": cheapest.retailer_id,
            "retailer_name": cheapest.retailer.name,
            "price": float(cheapest.current_price),
            "availability": cheapest.availability,
            "url": cheapest.retailer_product_url,
        },
        "unit_price": per,
        "freshness": freshness(cheapest.last_checked_at),
        "offers": offer_rows,
    }
