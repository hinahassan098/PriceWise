from app.database import Base, SessionLocal, engine
from app.services.collect import run_all_collections
from app.services.seed import seed


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed(db)
        jobs = run_all_collections(db, max_products=80)
        for job in jobs:
            print(f"{job['retailer_id']}: {job['status']} ({job['items_upserted']}) {job.get('error') or ''}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
