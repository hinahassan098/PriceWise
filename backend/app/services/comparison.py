from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Price, ProductVariant, RetailerProduct
from app.services.freshness import freshness, unit_price


def comparison(db: Session, variant_id: int, sort: str = "cheapest") -> dict | None:
    variant = db.scalar(
        select(ProductVariant)
        .options(
            joinedload(ProductVariant.product),
            joinedload(ProductVariant.retailer_products).joinedload(RetailerProduct.retailer),
        )
        .where(ProductVariant.id == variant_id)
    )
    if variant is None:
        return None

    rows = []
    for rp in variant.retailer_products:
        if rp.current_price is None or float(rp.current_price) <= 0:
            continue
        if rp.match_decision not in {"auto"}:
            if rp.match_decision != "review" or not rp.match_confidence or float(rp.match_confidence) < 95:
                continue
        per = unit_price(float(rp.current_price), int(variant.pack_count), float(variant.size_value), variant.size_unit)
        discount = None
        if rp.current_compare_at and float(rp.current_compare_at) > float(rp.current_price):
            discount = round(float(rp.current_compare_at) - float(rp.current_price), 2)
        rows.append(
            {
                "retailer_id": rp.retailer_id,
                "retailer_name": rp.retailer.name,
                "product_name": rp.retailer_product_name,
                "price": float(rp.current_price),
                "compare_at_price": float(rp.current_compare_at) if rp.current_compare_at else None,
                "discount": discount,
                "availability": rp.availability,
                "url": rp.retailer_product_url,
                "image_url": rp.image_url,
                "match_confidence": float(rp.match_confidence) if rp.match_confidence is not None else None,
                "unit_price": per,
                "freshness": freshness(rp.last_checked_at),
            }
        )

    if sort == "expensive":
        rows.sort(key=lambda row: row["price"], reverse=True)
    elif sort == "store":
        rows.sort(key=lambda row: row["retailer_name"])
    elif sort == "availability":
        rows.sort(key=lambda row: (0 if row["availability"] == "in_stock" else 1, row["price"]))
    else:
        rows.sort(key=lambda row: (0 if row["availability"] == "in_stock" else 1, row["price"]))

    in_stock = [row for row in rows if row["availability"] == "in_stock"]
    cheapest = min(in_stock, key=lambda row: row["price"]) if in_stock else (rows[0] if rows else None)
    savings = None
    if cheapest and in_stock:
        highest = max(in_stock, key=lambda row: row["price"])
        gap = round(highest["price"] - cheapest["price"], 2)
        if gap > 0:
            savings = {
                "amount": gap,
                "from_store": highest["retailer_name"],
                "to_store": cheapest["retailer_name"],
            }

    product = variant.product
    return {
        "variant": {
            "id": variant.id,
            "product_id": product.id,
            "brand": product.brand,
            "name": product.name,
            "size_label": variant.size_label,
            "pack_count": variant.pack_count,
            "barcode": variant.barcode,
            "image_url": product.image_url,
        },
        "prices": rows,
        "cheapest": cheapest,
        "savings": savings,
        "store_count": len(rows),
    }


def history(db: Session, variant_id: int, retailer_id: str | None = None) -> list[dict]:
    query = (
        select(Price, RetailerProduct)
        .join(RetailerProduct, Price.retailer_product_id == RetailerProduct.id)
        .where(RetailerProduct.variant_id == variant_id)
        .order_by(Price.collected_at.asc())
    )
    if retailer_id:
        query = query.where(RetailerProduct.retailer_id == retailer_id)
    items = db.execute(query).all()
    return [
        {
            "retailer_id": rp.retailer_id,
            "price": float(price.price),
            "availability": price.availability,
            "collected_at": price.collected_at.isoformat() if price.collected_at else None,
            "suspicious": price.suspicious,
        }
        for price, rp in items
    ]
