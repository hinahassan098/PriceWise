from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.matching.normalize import normalize_name
from app.matching.units import ParsedSize
from app.models import Product, ProductVariant

AUTO_MATCH = 88.0
REVIEW_MATCH = 75.0
LINE_TOKENS = {
    "matic",
    "auto",
    "comfort",
    "expert",
    "pearls",
    "liquid",
    "bar",
    "front",
    "top",
    "automatic",
}


def _line_conflict(left: str, right: str) -> bool:
    left_bits = set(left.split()) & LINE_TOKENS
    right_bits = set(right.split()) & LINE_TOKENS
    return bool(left_bits.symmetric_difference(right_bits))


@dataclass
class MatchCandidate:
    variant: ProductVariant
    confidence: float
    reason: str


def match_variant(
    db: Session,
    *,
    brand: str | None,
    name: str,
    size: ParsedSize,
    barcode: str | None,
) -> MatchCandidate | None:
    if barcode:
        variant = db.scalar(select(ProductVariant).where(ProductVariant.barcode == barcode))
        if variant:
            return MatchCandidate(variant, 100.0, "barcode")

    normalized = normalize_name(name, brand)
    variants = db.scalars(select(ProductVariant)).all()
    best: MatchCandidate | None = None
    for variant in variants:
        if int(variant.pack_count) != size.pack_count:
            continue
        if float(variant.size_value) != float(size.value) or variant.size_unit != size.unit:
            continue
        product = variant.product
        brand_ok = True
        if brand and product.brand:
            brand_ok = product.brand.lower() == brand.lower()
        if not brand_ok:
            continue
        other = normalize_name(product.name, product.brand)
        if _line_conflict(normalized, other):
            continue
        score = fuzz.token_set_ratio(normalized, other)
        if best is None or score > best.confidence:
            reason = "brand_name_size" if score >= AUTO_MATCH else "fuzzy_size"
            best = MatchCandidate(variant, float(score), reason)
    return best


def create_canonical(
    db: Session,
    *,
    brand: str | None,
    name: str,
    size: ParsedSize,
    barcode: str | None,
    image_url: str | None,
    category_id: int | None,
) -> ProductVariant:
    normalized = normalize_name(name, brand) or name
    product = Product(
        brand=brand,
        name=normalized.title() if normalized else name,
        category_id=category_id,
        image_url=image_url,
        search_text="",
    )
    db.add(product)
    db.flush()
    variant = ProductVariant(
        product_id=product.id,
        variant_name=f"{product.name} {size.label}".strip(),
        pack_count=size.pack_count,
        size_value=size.value,
        size_unit=size.unit,
        size_label=size.label,
        barcode=barcode,
        search_text="",
    )
    db.add(variant)
    db.flush()
    product.search_text = " ".join(filter(None, [brand, product.name, size.label])).lower()
    variant.search_text = " ".join(filter(None, [brand, product.name, size.label, barcode])).lower()
    return variant
