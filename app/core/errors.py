from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette import status
from starlette.exceptions import HTTPException as StarletteHTTPException


class ErrorEnvelope(JSONResponse):
    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        details: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        payload: dict[str, Any] = {"code": code, "message": message}
        if details is not None:
            payload["details"] = details
        super().__init__(payload, status_code=status_code, headers=headers)


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        accept = (request.headers.get("accept") or "").lower()
        path = request.url.path
        if "text/html" in accept and not path.startswith("/api") and not path.startswith("/login"):
            return RedirectResponse(url=f"/login?next={request.url}", status_code=302)
    detail = exc.detail
    message = detail if isinstance(detail, str) else status.HTTP_STATUS_CODES.get(exc.status_code, "Error")
    details = detail if isinstance(detail, dict) else None
    return ErrorEnvelope(status_code=exc.status_code, code="http_error", message=message, details=details)


async def validation_exception_handler(request: Request, exc):  # type: ignore[override]
    from fastapi.exceptions import RequestValidationError

    if isinstance(exc, RequestValidationError):
        return ErrorEnvelope(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="validation_error",
            message="Validation failed",
            details={"errors": exc.errors()},
        )
    raise exc


async def rate_limit_handler(request: Request, exc):
    retry_after = getattr(exc, "retry_after", None)
    headers = {"Retry-After": str(retry_after)} if retry_after else None
    return ErrorEnvelope(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        code="rate_limit_exceeded",
        message="Too many requests",
        headers=headers,
    )
