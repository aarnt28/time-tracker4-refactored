from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, Request, status
from fastapi.security.utils import get_authorization_scheme_param

from ..core.config import settings
from ..core.security import decode_token
from ..middlewares import principal_ctx_var
from .ui_auth import is_logged_in


class AuthContext:
    def __init__(self, *, subject: str, scheme: str) -> None:
        self.subject = subject
        self.scheme = scheme


def _unauthorized(detail: str = "Unauthorized") -> None:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def _set_principal(request: Request, principal: str) -> None:
    principal_ctx_var.set(principal)
    request.state.principal = principal


async def require_api_or_jwt(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> AuthContext:
    if is_logged_in(request):
        subject = f"ui:{settings.UI_USERNAME}"
        _set_principal(request, subject)
        return AuthContext(subject=subject, scheme="session")

    api_key = settings.API_KEY_VALUE
    provided_key = (x_api_key or "").strip()
    if api_key and provided_key and hmac.compare_digest(api_key, provided_key):
        _set_principal(request, "api-key")
        return AuthContext(subject="api-key", scheme="api_key")

    if not api_key and not authorization:
        _set_principal(request, "anonymous")
        return AuthContext(subject="anonymous", scheme="open")

    if authorization:
        scheme, credentials = get_authorization_scheme_param(authorization)
        if scheme.lower() == "bearer" and credentials:
            try:
                payload = decode_token(credentials, verify_type="access")
            except ValueError as exc:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
            subject = f"jwt:{payload.sub}"
            _set_principal(request, subject)
            request.state.token_payload = payload
            return AuthContext(subject=subject, scheme="jwt")

    if api_key and settings.AUTH_ALLOW_API_KEY:
        _unauthorized("Invalid API key")
    _unauthorized("Authorization required")


async def require_ui_or_token(
    request: Request,
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> AuthContext:
    return await require_api_or_jwt(request=request, authorization=authorization, x_api_key=x_api_key)
