from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.collectors.registry import LIVE_COLLECTORS
from app.models import CollectionJob, Retailer
from app.services.ingest import ingest_product


def run_retailer_collection(
    db: Session,
    retailer_id: str,
    max_products: int | None = None,
) -> CollectionJob:
    if retailer_id not in LIVE_COLLECTORS:
        raise ValueError(f"No live collector for {retailer_id}")

    job = CollectionJob(
        retailer_id=retailer_id,
        job_type="catalog",
        tier="popular",
        status="running",
        started_at=datetime.now(timezone.utc),
        items_upserted=0,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    try:
        collector = LIVE_COLLECTORS[retailer_id]()
        count = 0
        for item in collector.collect(max_products=max_products):
            ingest_product(db, item)
            count += 1
            if count % 20 == 0:
                db.commit()
        db.commit()
        retailer = db.get(Retailer, retailer_id)
        if retailer:
            retailer.status = "connected"
            retailer.last_successful_sync = datetime.now(timezone.utc)
        job.status = "ok"
        job.items_upserted = count
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as exc:
        db.rollback()
        job = db.get(CollectionJob, job.id)
        if job:
            job.status = "error"
            job.error = str(exc)
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
        retailer = db.get(Retailer, retailer_id)
        if retailer:
            retailer.status = "error"
            db.commit()
        raise
    return job


def run_springs_collection(db: Session, max_products: int | None = None) -> CollectionJob:
    return run_retailer_collection(db, "springs", max_products=max_products)


def run_all_collections(db: Session, max_products: int | None = 120) -> list[dict]:
    results = []
    for retailer_id in LIVE_COLLECTORS:
        try:
            job = run_retailer_collection(db, retailer_id, max_products=max_products)
            results.append(
                {
                    "retailer_id": retailer_id,
                    "job_id": job.id,
                    "status": job.status,
                    "items_upserted": job.items_upserted,
                    "error": job.error,
                }
            )
        except Exception as exc:  # noqa: BLE001
            results.append(
                {
                    "retailer_id": retailer_id,
                    "job_id": None,
                    "status": "error",
                    "items_upserted": 0,
                    "error": str(exc),
                }
            )
    return results
