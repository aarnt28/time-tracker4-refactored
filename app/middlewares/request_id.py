from __future__ import annotations

import logging
import time
from contextvars import ContextVar
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

request_id_ctx_var: ContextVar[str | None] = ContextVar("request_id", default=None)
principal_ctx_var: ContextVar[str | None] = ContextVar("principal_id", default=None)
logger = logging.getLogger("app.request")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Ensure every request has a correlation id and emit structured logs."""

    def __init__(self, app, header_name: str = "X-Request-ID") -> None:  # type: ignore[override]
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get(self.header_name) or str(uuid4())
        token = request_id_ctx_var.set(request_id)
        principal_token = principal_ctx_var.set(None)
        request.state.request_id = request_id
        start = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_ctx_var.reset(token)
            principal_ctx_var.reset(principal_token)
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers[self.header_name] = request_id
        response.headers.setdefault("X-Response-Time", f"{duration_ms:.2f}ms")
        principal = principal_ctx_var.get()
        extra = {
            "extra_data": {
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": round(duration_ms, 2),
            }
        }
        if principal:
            extra["extra_data"]["principal"] = principal
        logger.info("request.completed", extra=extra)
        return response
