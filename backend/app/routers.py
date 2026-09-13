from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import require_admin_key
from app.models import CollectionJob, MatchReview, Price, Product, ProductVariant, Retailer, RetailerProduct
from app.services.collect import run_all_collections, run_retailer_collection, run_springs_collection
from app.services.comparison import comparison, history
from app.services.live_search import live_search
from app.services.search import search_variants, suggest

router = APIRouter(prefix="/api")


def retailer_id(store: str | None) -> str | None:
    return store.lower() if store else None


@router.get("/health")
def health() -> dict:
    return {"ok": True, "service": "pricewise"}


@router.get("/retailers")
def retailers(db: Session = Depends(get_db)) -> dict:
    rows = db.scalars(
        select(Retailer)
        .where(Retailer.status == "connected")
        .order_by(Retailer.name)
    ).all()
    return {
        "retailers": [
            {
                "id": row.id,
                "name": row.name,
                "slug": row.slug,
                "website_url": row.website_url,
                "status": row.status,
                "platform": row.platform,
                "last_successful_sync": row.last_successful_sync.isoformat() if row.last_successful_sync else None,
            }
            for row in rows
        ]
    }


@router.get("/categories")
def categories(db: Session = Depends(get_db)) -> dict:
    from app.models import Category

    rows = db.scalars(select(Category).order_by(Category.name)).all()
    return {"categories": [{"id": row.id, "slug": row.slug, "name": row.name} for row in rows]}


@router.get("/search")
def search(
    q: str = Query(..., min_length=1),
    store: str | None = None,
    in_stock: bool | None = None,
    live: bool = Query(True),
    db: Session = Depends(get_db),
) -> dict:
    def _apply_stock(data: dict) -> dict:
        if in_stock is None:
            return data
        want = "in_stock" if in_stock else "out_of_stock"
        filtered_results = []
        for row in data["results"]:
            offers = [o for o in (row.get("offers") or []) if o.get("availability") == want]
            if not offers:
                continue
            offers.sort(key=lambda o: o["price"])
            cheapest = offers[0]
            row["offers"] = offers
            row["store_count"] = len(offers)
            row["cheapest"] = {
                "retailer_id": cheapest["retailer_id"],
                "retailer_name": cheapest["retailer_name"],
                "price": cheapest["price"],
                "availability": cheapest["availability"],
                "url": cheapest["url"],
            }
            row["unit_price"] = cheapest.get("unit_price")
            row["freshness"] = cheapest.get("freshness")
            filtered_results.append(row)
        data["results"] = filtered_results
        data["all_store_prices"] = [
            o for o in data.get("all_store_prices") or [] if o.get("availability") == want
        ]
        return data

    if live and not store:
        # Skip ingest during request so search stays under Render timeouts.
        data = live_search(db, q, persist=False)
        if data.get("results"):
            return _apply_stock(data)
        # Live scrapes can time out on free hosts; fall back to catalog data.
        data = search_variants(db, q, retailer_id=None, in_stock=in_stock)
        data["mode"] = "catalog_fallback"
        return data

    data = search_variants(db, q, retailer_id=retailer_id(store), in_stock=in_stock)
    # Render free disks are ephemeral — after redeploy the catalog is empty.
    if not store and not data.get("results"):
        live_data = live_search(db, q)
        if live_data.get("results"):
            return _apply_stock(live_data)
    return data


@router.get("/search/suggest")
def search_suggest(q: str = Query("", min_length=0), db: Session = Depends(get_db)) -> dict:
    return {"suggestions": suggest(db, q)}


@router.get("/variants/{variant_id}")
def variant_detail(
    variant_id: int,
    sort: str = Query("cheapest"),
    db: Session = Depends(get_db),
) -> dict:
    data = comparison(db, variant_id, sort=sort)
    if data is None:
        raise HTTPException(status_code=404, detail="Variant not found")
    return data


@router.get("/variants/{variant_id}/prices")
def variant_prices(variant_id: int, db: Session = Depends(get_db)) -> dict:
    data = comparison(db, variant_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Variant not found")
    return {
        "product": f"{data['variant']['brand']} {data['variant']['name']} {data['variant']['size_label']}",
        "prices": data["prices"],
    }


@router.get("/variants/{variant_id}/history")
def variant_history(variant_id: int, store: str | None = None, db: Session = Depends(get_db)) -> dict:
    return {"history": history(db, variant_id, retailer_id=retailer_id(store))}


@router.get("/admin/stats")
def admin_stats(db: Session = Depends(get_db)) -> dict:
    return {
        "products": db.scalar(select(func.count(Product.id))) or 0,
        "variants": db.scalar(select(func.count(ProductVariant.id))) or 0,
        "retailer_products": db.scalar(select(func.count(RetailerProduct.id))) or 0,
        "prices": db.scalar(select(func.count(Price.id))) or 0,
        "matching_reviews": db.scalar(select(func.count(MatchReview.id)).where(MatchReview.status == "review"))
        or 0,
        "jobs_error": db.scalar(select(func.count(CollectionJob.id)).where(CollectionJob.status == "error")) or 0,
        "updated_today": db.scalar(
            select(func.count(RetailerProduct.id)).where(RetailerProduct.last_checked_at.is_not(None))
        )
        or 0,
    }


@router.get("/admin/jobs")
def admin_jobs(db: Session = Depends(get_db)) -> dict:
    rows = db.scalars(select(CollectionJob).order_by(CollectionJob.id.desc()).limit(20)).all()
    return {
        "jobs": [
            {
                "id": row.id,
                "retailer_id": row.retailer_id,
                "status": row.status,
                "items_upserted": row.items_upserted,
                "error": row.error,
                "started_at": row.started_at.isoformat() if row.started_at else None,
                "finished_at": row.finished_at.isoformat() if row.finished_at else None,
            }
            for row in rows
        ]
    }


@router.get("/admin/matching")
def admin_matching(db: Session = Depends(get_db)) -> dict:
    rows = db.scalars(select(MatchReview).where(MatchReview.status == "review").limit(50)).all()
    items = []
    for row in rows:
        rp = db.get(RetailerProduct, row.retailer_product_id)
        variant = db.get(ProductVariant, row.candidate_variant_id) if row.candidate_variant_id else None
        items.append(
            {
                "id": row.id,
                "confidence": float(row.confidence),
                "retailer_product": rp.retailer_product_name if rp else None,
                "retailer": rp.retailer_id if rp else None,
                "candidate": variant.variant_name if variant else None,
            }
        )
    return {"reviews": items}


@router.post("/admin/collect/springs")
def collect_springs(
    max_products: int | None = None,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_key),
) -> dict:
    job = run_springs_collection(db, max_products=max_products)
    return {"job_id": job.id, "status": job.status, "items_upserted": job.items_upserted}


@router.post("/admin/collect/all")
def collect_all(
    max_products: int | None = 100,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_key),
) -> dict:
    return {"jobs": run_all_collections(db, max_products=max_products)}


@router.post("/admin/collect/{retailer_id}")
def collect_retailer(
    retailer_id: str,
    max_products: int | None = 120,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_key),
) -> dict:
    try:
        job = run_retailer_collection(db, retailer_id, max_products=max_products)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "job_id": job.id,
        "retailer_id": retailer_id,
        "status": job.status,
        "items_upserted": job.items_upserted,
        "error": job.error,
    }
