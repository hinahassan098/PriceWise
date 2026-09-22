from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Retailer, RetailerCity

NATIONWIDE_TOKENS = ("nationwide", "pakistan", "all pakistan")

# Approx centers for "Use my location" nearest-city mapping (web client).
CITY_COORDS: dict[str, tuple[float, float]] = {
    "Karachi": (24.8607, 67.0011),
    "Lahore": (31.5204, 74.3587),
    "Islamabad": (33.6844, 73.0479),
    "Rawalpindi": (33.5651, 73.0169),
    "Faisalabad": (31.4504, 73.1350),
    "Multan": (30.1575, 71.5249),
}


def _is_nationwide(city: str) -> bool:
    low = city.lower().strip()
    return any(token in low for token in NATIONWIDE_TOKENS)


def normalize_city_name(city: str) -> str | None:
    raw = city.split(" +")[0].strip()
    if not raw or _is_nationwide(raw):
        return None
    return raw.title() if raw.lower() != "islamabad" else "Islamabad"


def list_cities(db: Session) -> list[dict]:
    rows = db.scalars(select(RetailerCity)).all()
    names: set[str] = set()
    for row in rows:
        name = normalize_city_name(row.city)
        if name:
            names.add(name)
    # Always expose major metros even if seed is thin.
    names.update(CITY_COORDS.keys())
    ordered = sorted(names)
    return [
        {"id": "all", "name": "All Pakistan", "nationwide": True},
        *[{"id": c.lower().replace(" ", "-"), "name": c, "nationwide": False} for c in ordered],
    ]


def _physical_cities(entries: list[str]) -> list[str]:
    """City names where the retailer has a real local presence (not shipping flags)."""
    out: list[str] = []
    for entry in entries:
        normalized = normalize_city_name(entry)
        if normalized:
            out.append(normalized.lower())
    return out


def retailer_ids_for_city(db: Session, city: str | None) -> set[str] | None:
    """Return connected retailer ids serving city, or None for all Pakistan.

    Physical store cities win. "Nationwide shipping" alone does not put a
    Lahore-only chain into every city filter — those shippers still appear
    under All Pakistan, and pure-online retailers (no physical cities) stay
    available in every city as delivery options.
    """
    if not city or city.strip().lower() in {"all", "all-pakistan", "pakistan", "nationwide"}:
        return None

    target = city.strip().lower().replace("-", " ")
    retailers = db.scalars(
        select(Retailer)
        .where(Retailer.status == "connected")
        .options(joinedload(Retailer.cities))
    ).unique().all()

    matched: set[str] = set()
    for retailer in retailers:
        entries = [c.city for c in retailer.cities]
        physical = _physical_cities(entries)
        has_nationwide = any(_is_nationwide(e) for e in entries)

        if physical:
            if target in physical:
                matched.add(retailer.id)
            continue

        # No physical cities listed: online-only or unknown → include everywhere.
        if has_nationwide or not entries:
            matched.add(retailer.id)

    return matched
