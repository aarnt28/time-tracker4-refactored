from __future__ import annotations

import hmac

from fastapi import APIRouter, Header, HTTPException, status

from ..core.config import settings
from ..core.security import issue_token_pair, refresh_access_token
from ..schemas.auth import RefreshRequest, TokenRequest, TokenResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/token", response_model=TokenResponse, summary="Exchange API key for JWTs")
async def exchange_token(
    payload: TokenRequest,
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    configured_key = (settings.API_KEY_VALUE or "").strip()
    if not configured_key:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="API key authentication is disabled")
    provided = payload.api_key or (x_api_key or "")
    if not provided or not hmac.compare_digest(provided.strip(), configured_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    pair = issue_token_pair(subject="api-client")
    return TokenResponse(**pair.model_dump())


@router.post("/refresh", response_model=TokenResponse, summary="Refresh access token")
async def refresh_token(payload: RefreshRequest):
    try:
        pair = refresh_access_token(payload.refresh_token)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return TokenResponse(**pair.model_dump())
