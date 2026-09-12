from __future__ import annotations

from datetime import datetime, timezone

from app.matching.units import ParsedSize, price_per_canonical_unit


def freshness(checked_at: datetime | None) -> dict:
    if checked_at is None:
        return {
            "level": "unknown",
            "label": "No timestamp",
            "checked_at": None,
        }
    if checked_at.tzinfo is None:
        checked_at = checked_at.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    seconds = max(0, (now - checked_at).total_seconds())
    minutes = int(seconds // 60)
    hours = int(seconds // 3600)
    if minutes < 1:
        label = "Updated just now"
        level = "live"
    elif minutes < 30:
        label = f"Updated {minutes} min ago"
        level = "live"
    elif hours < 24 and checked_at.date() == now.date():
        label = f"Updated {hours}h ago" if hours else f"Updated {minutes} min ago"
        level = "today"
    elif hours < 24:
        label = f"Updated {hours}h ago"
        level = "today"
    else:
        days = max(1, hours // 24)
        label = f"Updated {days}d ago"
        level = "stale"
    return {"level": level, "label": label, "checked_at": checked_at.isoformat()}


def unit_price(price: float | None, pack_count: int, size_value: float, size_unit: str) -> dict | None:
    if price is None:
        return None
    parsed = ParsedSize(pack_count, float(size_value), size_unit, "", "")
    amount, unit = price_per_canonical_unit(float(price), parsed)
    if amount is None:
        return None
    return {"amount": amount, "unit": unit}
