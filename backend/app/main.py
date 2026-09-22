from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import Base, engine
from app.database import SessionLocal
from app.routers import router
from app.services.seed import seed

app = FastAPI(title=settings.app_name, version="0.2.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin],
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


def _warm_live_caches() -> None:
    """Prefetch Imtiaz menu + Naheed/SPAR sitemap URL lists for snappy first search."""
    try:
        from app.collectors.imtiaz_blink import ImtiazCollector

        ImtiazCollector().search_live("milk", limit=1)
    except Exception:
        pass
    try:
        from app.collectors.naheed_html import NaheedHtmlCollector

        NaheedHtmlCollector().warm_url_cache()
    except Exception:
        pass
    try:
        from app.collectors.spar_html import SparHtmlCollector

        SparHtmlCollector().warm_url_cache()
    except Exception:
        pass


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
    # Warm in the background so boot stays fast.
    import threading

    threading.Thread(target=_warm_live_caches, daemon=True).start()
