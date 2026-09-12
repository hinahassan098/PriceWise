from __future__ import annotations

import re

from app.matching.units import parse_size

NOISE_WORDS = {
    "the",
    "and",
    "for",
    "with",
    "of",
    "new",
    "pack",
    "packet",
    "bottle",
    "pet",
    "imported",
    "original",
}

TOKEN_RE = re.compile(r"[^a-z0-9]+")


def normalize_barcode(sku: str | None) -> str | None:
    if not sku:
        return None
    digits = re.sub(r"\D", "", sku)
    if len(digits) in {8, 12, 13, 14}:
        return digits
    return None


def normalize_name(text: str, brand: str | None = None) -> str:
    parsed = parse_size(text or "")
    name = parsed.remainder.lower()
    if brand:
        brand_l = brand.lower().strip()
        if name.startswith(brand_l):
            name = name[len(brand_l) :].strip()
    tokens = [token for token in TOKEN_RE.sub(" ", name).split() if token and token not in NOISE_WORDS]
    return " ".join(tokens)


def search_blob(*parts: str | None) -> str:
    return " ".join(part.strip() for part in parts if part).lower()
