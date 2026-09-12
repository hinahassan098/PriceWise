from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import ROOT_DIR
from app.models import Category, Retailer, RetailerCity

CATEGORIES = [
    ("grocery", "Grocery"),
    ("beverages", "Beverages"),
    ("personal-care", "Personal Care"),
    ("household", "Household"),
    ("snacks", "Snacks"),
    ("baby-care", "Baby Care"),
    ("dairy", "Dairy"),
    ("staples", "Staples"),
]


def seed(db: Session) -> None:
    for slug, name in CATEGORIES:
        if db.scalar(select(Category).where(Category.slug == slug)) is None:
            db.add(Category(slug=slug, name=name))

    payload = json.loads((ROOT_DIR / "data" / "retailers.json").read_text(encoding="utf-8"))
    active_ids = {row["id"] for row in payload["retailers"]}
    for row in payload["retailers"]:
        retailer = db.get(Retailer, row["id"])
        if retailer is None:
            retailer = Retailer(id=row["id"])
            db.add(retailer)
        retailer.name = row["name"]
        retailer.slug = row["slug"]
        retailer.website_url = row["website_url"]
        retailer.platform = row.get("platform")
        retailer.scraping_method = row["scraping_method"]
        retailer.status = row.get("status") or "connected"
        existing_cities = {city.city for city in retailer.cities}
        for city in row.get("cities") or []:
            city_name = city.split(" +")[0].replace("Nationwide shipping", "Nationwide")
            if city_name not in existing_cities:
                db.add(RetailerCity(retailer_id=row["id"], city=city_name))

    # Hide retailers that are no longer in the connected registry.
    for retailer in db.scalars(select(Retailer)).all():
        if retailer.id not in active_ids:
            retailer.status = "planned"
    db.commit()
