from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    app_name: str = "PriceWise"
    city: str = "Karachi"
    database_url: str = f"sqlite:///{(BACKEND_DIR / 'hina.db').as_posix()}"
    cors_origins: str = (
        "http://localhost:3000,http://localhost:3001,http://localhost:3020,"
        "http://127.0.0.1:3000,http://127.0.0.1:3001,http://127.0.0.1:3020,"
        "https://pricewise-78on.onrender.com,"
        "https://pricewise-web.onrender.com"
    )
    user_agent: str = "PriceWise/0.1 (grocery comparison; local research collector)"
    springs_max_products: int = 900
    request_delay_seconds: float = 0.12
    # Shared secret for POST /api/admin/collect* (send as X-Admin-Key).
    admin_api_key: str = ""


settings = Settings()
