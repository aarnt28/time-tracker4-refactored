
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from .core.config import settings
from .core.errors import ErrorEnvelope, http_exception_handler, rate_limit_handler, validation_exception_handler
from .core.logging import configure_logging
from .db.migrate import run_migrations
from .db.session import Base, engine
from .middlewares import RequestIdMiddleware, SecurityHeadersMiddleware

# Ensure models are registered with SQLAlchemy metadata before create_all.
from .models import hardware as _hardware  # noqa: F401
from .models import inventory as _inventory  # noqa: F401
from .models import ticket as _ticket  # noqa: F401

configure_logging()

app = FastAPI(
    title="Time Tracker API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(RequestIdMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

if settings.ALLOWED_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["ETag", "Last-Modified", "Retry-After", "X-Request-ID"],
    )

limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT])
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request, exc):  # type: ignore[override]
    return ErrorEnvelope(status_code=500, code="internal_error", message="Internal server error")


BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")
TEMPLATES = Jinja2Templates(directory=str(settings.templates_dir))

LOCAL_TZ = ZoneInfo(settings.TZ) if settings.TZ else None


def _to_dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value:
        try:
            dt = datetime.fromisoformat(value)
        except Exception:
            return None
    else:
        return None
    if dt.tzinfo is None and LOCAL_TZ:
        dt = dt.replace(tzinfo=LOCAL_TZ)
    if LOCAL_TZ:
        dt = dt.astimezone(LOCAL_TZ)
    return dt


def fmt_dt(value: Any, fmt: str = "%Y-%m-%d %I:%M %p") -> str:
    dt = _to_dt(value)
    return dt.strftime(fmt) if dt else ""


def fmt_date(value: Any, fmt: str = "%Y-%m-%d") -> str:
    dt = _to_dt(value)
    return dt.strftime(fmt) if dt else ""


def fmt_time(value: Any, fmt: str = "%I:%M %p") -> str:
    dt = _to_dt(value)
    return dt.strftime(fmt) if dt else ""


TEMPLATES.env.filters["fmt_dt"] = fmt_dt
TEMPLATES.env.filters["fmt_date"] = fmt_date
TEMPLATES.env.filters["fmt_time"] = fmt_time

Base.metadata.create_all(bind=engine)
run_migrations(engine)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.APP_SECRET,
    session_cookie=settings.SESSION_COOKIE_NAME,
    max_age=settings.SESSION_MAX_AGE,
    same_site="lax",
    https_only=False,
)

instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app, include_in_schema=False, endpoint="/metrics")

from .routers import auth_ui as auth_ui_router  # type: ignore
app.include_router(auth_ui_router.router)

from .routers import api_auth as api_auth_router  # type: ignore
app.include_router(api_auth_router.router)

from .routers import ui as ui_router  # type: ignore
app.include_router(ui_router.router)

from .routers import api_tickets as api_tickets_router  # type: ignore
app.include_router(api_tickets_router.router, prefix="")

from .routers import clients as clients_router  # type: ignore
app.include_router(clients_router.router, prefix="")

from .routers import api_hardware as api_hardware_router  # type: ignore
app.include_router(api_hardware_router.router, prefix="")

from .routers import api_inventory as api_inventory_router  # type: ignore
app.include_router(api_inventory_router.router, prefix="")

from .routers import address as address_router  # type: ignore
app.include_router(address_router.router, prefix="")


@app.get("/healthz", include_in_schema=False)
async def healthz():
    return {"status": "ok"}


@app.get("/readyz", include_in_schema=False)
async def readyz():
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    return {"status": "ready"}


__all__ = ["app", "limiter"]
