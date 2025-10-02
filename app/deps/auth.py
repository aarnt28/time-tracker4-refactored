from __future__ import annotations
from fastapi import Header, HTTPException, status
from ..core.config import settings

def _unauthorized(detail: str = "Unauthorized"):
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

async def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    """
    Enforce API key for all /api/* routes.
    - If settings.API_TOKEN is unset/empty -> allow (dev mode).
    - Else, require X-API-Key to match exactly.
    """
    token = (settings.API_TOKEN or "").strip()
    if not token:
        return True  # dev mode
    if (x_api_key or "").strip() != token:
        _unauthorized("Invalid API key")
    return True

# -------- Backwards compatibility shim --------
# Older routers import `require_ui_or_token`. Keep it working by delegating to the new gate.
async def require_ui_or_token(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    return await require_api_key(x_api_key=x_api_key)
