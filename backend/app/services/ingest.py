from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.base import CollectedProduct
from app.matching.matcher import AUTO_MATCH, REVIEW_MATCH, create_canonical, match_variant
from app.matching.normalize import normalize_barcode, normalize_name
from app.matching.units import parse_size
from app.matching.validation import flag_price
from app.models import Category, MatchReview, Price, RetailerProduct

CATEGORY_MAP = {
    "laundry": "household",
    "household": "household",
    "beverages": "beverages",
    "drinks": "beverages",
    "dairy": "dairy",
    "baby": "baby-care",
    "baby care": "baby-care",
    "snacks": "snacks",
    "biscuits, wafers & cakes": "snacks",
    "face & skin care": "personal-care",
    "soap & hand wash": "personal-care",
    "hair care": "personal-care",
    "skincare": "personal-care",
    "food cupboard": "grocery",
    "cooking oil": "staples",
}


def _category_id(db: Session, product_type: str | None) -> int | None:
    if not product_type:
        return db.scalar(select(Category.id).where(Category.slug == "grocery"))
    slug = CATEGORY_MAP.get(product_type.lower())
    if slug:
        return db.scalar(select(Category.id).where(Category.slug == slug))
    return db.scalar(select(Category.id).where(Category.slug == "grocery"))


def ingest_product(db: Session, item: CollectedProduct) -> RetailerProduct:
    size = parse_size(item.name)
    barcode = item.barcode or normalize_barcode(item.sku)
    normalized = normalize_name(item.name, item.brand)

    existing = db.scalar(
        select(RetailerProduct).where(
            RetailerProduct.retailer_id == item.retailer,
            RetailerProduct.retailer_product_url == item.url,
        )
    )
    if existing is None and item.sku:
        existing = db.scalar(
            select(RetailerProduct).where(
                RetailerProduct.retailer_id == item.retailer,
                RetailerProduct.retailer_sku == item.sku,
                RetailerProduct.city == item.city,
            )
        )

    availability = "in_stock" if item.availability else "out_of_stock"
    if existing is None:
        existing = RetailerProduct(
            retailer_id=item.retailer,
            retailer_product_name=item.name,
            retailer_product_url=item.url,
            retailer_sku=item.sku,
            barcode=barcode,
            image_url=item.image_url,
            availability=availability,
            city=item.city,
            normalized_name=normalized,
        )
        db.add(existing)
        db.flush()
    else:
        existing.retailer_product_name = item.name
        existing.retailer_sku = item.sku
        existing.barcode = barcode
        existing.image_url = item.image_url
        existing.availability = availability
        existing.normalized_name = normalized

    candidate = match_variant(db, brand=item.brand, name=item.name, size=size, barcode=barcode)
    if candidate and candidate.confidence >= AUTO_MATCH:
        existing.variant_id = candidate.variant.id
        existing.product_id = candidate.variant.product_id
        existing.match_confidence = candidate.confidence
        existing.match_decision = "auto"
        if barcode and not candidate.variant.barcode:
            candidate.variant.barcode = barcode
    elif candidate and candidate.confidence >= REVIEW_MATCH:
        existing.match_confidence = candidate.confidence
        existing.match_decision = "review"
        db.add(
            MatchReview(
                retailer_product_id=existing.id,
                candidate_variant_id=candidate.variant.id,
                confidence=candidate.confidence,
                status="review",
            )
        )
        if existing.variant_id is None:
            variant = create_canonical(
                db,
                brand=item.brand,
                name=item.name,
                size=size,
                barcode=barcode,
                image_url=item.image_url,
                category_id=_category_id(db, item.product_type),
            )
            existing.variant_id = variant.id
            existing.product_id = variant.product_id
            existing.match_decision = "review"
    else:
        variant = create_canonical(
            db,
            brand=item.brand,
            name=item.name,
            size=size,
            barcode=barcode,
            image_url=item.image_url,
            category_id=_category_id(db, item.product_type),
        )
        existing.variant_id = variant.id
        existing.product_id = variant.product_id
        existing.match_confidence = 100.0
        existing.match_decision = "auto"

    suspicious, reason = flag_price(db, existing.id, item.price)
    changed = (
        existing.current_price is None
        or float(existing.current_price) != item.price
        or existing.availability != availability
        or existing.current_compare_at != item.compare_at_price
    )
    existing.current_price = item.price
    existing.current_compare_at = item.compare_at_price
    existing.last_checked_at = item.collected_at
    if changed:
        db.add(
            Price(
                retailer_product_id=existing.id,
                price=item.price,
                compare_at_price=item.compare_at_price,
                discount=item.discount(),
                currency=item.currency,
                availability=availability,
                collected_at=item.collected_at,
                source=item.source,
                suspicious=suspicious,
                suspicion_reason=reason,
            )
        )
    db.flush()
    return existing
