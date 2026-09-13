from __future__ import annotations

import secrets

from fastapi import Header, HTTPException

from app.config import settings


def require_admin_key(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")) -> None:
    """Require a shared admin API key for mutation endpoints."""
    expected = (settings.admin_api_key or "").strip()
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Admin API key is not configured on the server",
        )
    if not x_admin_key or not secrets.compare_digest(x_admin_key, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing admin API key")
