from __future__ import annotations

from statistics import median

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Price


def flag_price(db: Session, retailer_product_id: int, new_price: float) -> tuple[bool, str | None]:
    history = db.scalars(
        select(Price.price)
        .where(Price.retailer_product_id == retailer_product_id, Price.suspicious.is_(False))
        .order_by(Price.collected_at.desc())
        .limit(14)
    ).all()
    if len(history) < 3:
        return False, None
    mid = float(median([float(p) for p in history]))
    if mid <= 0:
        return False, None
    if new_price < mid * 0.4:
        return True, f"new price {new_price} is below 40% of median {mid:.0f}"
    if new_price > mid * 2.5:
        return True, f"new price {new_price} is above 250% of median {mid:.0f}"
    return False, None
