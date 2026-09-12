from __future__ import annotations

import re
from dataclasses import dataclass

PACK_RE = re.compile(
    r"(?P<count>\d+)\s*[x×]\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>[a-zA-Z]+)",
    re.IGNORECASE,
)
SIZE_RE = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>kg|kgs|kilogram|kilograms|g|gm|gms|gr|gram|grams|l|ltr|ltrs|lt|liter|litre|liters|litres|ml|mls|millilitre|millilitres|pc|pcs|piece|pieces|tab|tabs|tablet|tablets)\b",
    re.IGNORECASE,
)
TRAILING_PUNCT_RE = re.compile(r"[.,]+$")

MASS_UNITS = {
    "kg": ("g", 1000),
    "kgs": ("g", 1000),
    "kilogram": ("g", 1000),
    "kilograms": ("g", 1000),
    "g": ("g", 1),
    "gm": ("g", 1),
    "gms": ("g", 1),
    "gr": ("g", 1),
    "gram": ("g", 1),
    "grams": ("g", 1),
}
VOLUME_UNITS = {
    "l": ("ml", 1000),
    "ltr": ("ml", 1000),
    "ltrs": ("ml", 1000),
    "lt": ("ml", 1000),
    "liter": ("ml", 1000),
    "litre": ("ml", 1000),
    "liters": ("ml", 1000),
    "litres": ("ml", 1000),
    "ml": ("ml", 1),
    "mls": ("ml", 1),
    "millilitre": ("ml", 1),
    "millilitres": ("ml", 1),
}
COUNT_UNITS = {
    "pc": ("piece", 1),
    "pcs": ("piece", 1),
    "piece": ("piece", 1),
    "pieces": ("piece", 1),
    "tab": ("piece", 1),
    "tabs": ("piece", 1),
    "tablet": ("piece", 1),
    "tablets": ("piece", 1),
}


@dataclass(frozen=True)
class ParsedSize:
    pack_count: int
    value: float
    unit: str
    label: str
    remainder: str

    @property
    def key(self) -> tuple[int, float, str]:
        return (self.pack_count, round(float(self.value), 4), self.unit)


def _canonical_unit(raw_unit: str) -> tuple[str, float] | None:
    unit = raw_unit.lower().rstrip(".")
    if unit in MASS_UNITS:
        return MASS_UNITS[unit]
    if unit in VOLUME_UNITS:
        return VOLUME_UNITS[unit]
    if unit in COUNT_UNITS:
        return COUNT_UNITS[unit]
    return None


def display_label(pack_count: int, value: float, unit: str) -> str:
    amount = _pretty_amount(value, unit)
    if pack_count > 1:
        return f"{pack_count} × {amount}"
    return amount


def _pretty_amount(value: float, unit: str) -> str:
    if unit == "g":
        if value >= 1000 and abs(value % 1000) < 0.001:
            return f"{_trim(value / 1000)} kg"
        return f"{_trim(value)} g"
    if unit == "ml":
        if value >= 1000:
            return f"{_trim(value / 1000)} L"
        return f"{_trim(value)} ml"
    if unit == "piece":
        return f"{_trim(value)} pcs" if value != 1 else "1 pc"
    return f"{_trim(value)} {unit}"


def _trim(value: float) -> str:
    if abs(value - round(value)) < 0.001:
        return str(int(round(value)))
    return f"{value:.2f}".rstrip("0").rstrip(".")


def parse_size(text: str) -> ParsedSize:
    if not text:
        return ParsedSize(1, 1, "piece", "1 pc", "")

    pack = PACK_RE.search(text)
    if pack:
        mapped = _canonical_unit(pack.group("unit"))
        if mapped:
            unit, multiplier = mapped
            value = float(pack.group("value")) * multiplier
            count = int(pack.group("count"))
            remainder = (text[: pack.start()] + text[pack.end() :]).strip()
            remainder = TRAILING_PUNCT_RE.sub("", remainder).strip()
            return ParsedSize(count, value, unit, display_label(count, value, unit), remainder)

    matches = list(SIZE_RE.finditer(text))
    if not matches:
        remainder = TRAILING_PUNCT_RE.sub("", text).strip()
        return ParsedSize(1, 1, "piece", "1 pc", remainder)

    match = matches[-1]
    mapped = _canonical_unit(match.group("unit"))
    if not mapped:
        remainder = TRAILING_PUNCT_RE.sub("", text).strip()
        return ParsedSize(1, 1, "piece", "1 pc", remainder)

    unit, multiplier = mapped
    value = float(match.group("value")) * multiplier
    remainder = (text[: match.start()] + text[match.end() :]).strip()
    remainder = TRAILING_PUNCT_RE.sub("", remainder).strip()
    return ParsedSize(1, value, unit, display_label(1, value, unit), remainder)


def price_per_canonical_unit(price: float, size: ParsedSize) -> tuple[float | None, str]:
    total = float(size.value) * size.pack_count
    if total <= 0:
        return None, ""
    if size.unit == "g":
        return round(price / (total / 1000), 2), "Rs/kg"
    if size.unit == "ml":
        return round(price / (total / 1000), 2), "Rs/L"
    if size.unit == "piece":
        return round(price / total, 2), "Rs/pc"
    return None, ""
