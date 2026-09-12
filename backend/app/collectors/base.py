from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class CollectedProduct:
    retailer: str
    name: str
    brand: str | None
    product_type: str | None
    sku: str | None
    barcode: str | None
    price: float
    compare_at_price: float | None
    currency: str
    availability: bool
    url: str
    image_url: str | None
    city: str
    collected_at: datetime
    source: str

    def discount(self) -> float | None:
        if self.compare_at_price and self.compare_at_price > self.price:
            return round(self.compare_at_price - self.price, 2)
        return None


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
