"""Application factory and top-level wiring for the Time Tracker app.

This module is the glue that brings together configuration, database setup,
HTML templates, API routers, and error handling. The goal is to give even a
brand-new developer a bird's-eye view of *what* pieces exist, *when* they are
initialised, *why* they are required, and *how* they interact to deliver the
web experience.
"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from .core.config import settings
from .db.session import Base, engine
from .db.migrate import run_migrations

# Importing the SQLAlchemy models registers them with the metadata. Without
# this step ``Base.metadata.create_all`` would not know about our tables.
from .models import hardware as _hardware  # noqa: F401
from .models import ticket as _ticket  # noqa: F401
from .models import inventory as _inventory  # noqa: F401
from .models import project as _project  # noqa: F401

# ---------- App init ----------
# The FastAPI instance is the beating heart of the project. Once created it
# will serve every HTTP request we receive.
app = FastAPI(title="Time Tracker")

# Static & templates
BASE_DIR = Path(__file__).resolve().parent
# ``mount`` glues the /static URL path to our local folder so browsers can load
# CSS/JS files. Think of it like pointing a shop sign to the correct storage
# cupboard.
app.mount("/static", StaticFiles(directory=str(settings.STATIC_DIR)), name="static")
# Jinja2Templates wraps the template directory and will later be used by router
# handlers when rendering HTML pages.
TEMPLATES = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))

# ---------- Jinja filters (restored) ----------
# When showing datetimes we want consistent formatting. LOCAL_TZ gives us the
# user's preferred timezone (from configuration) if one is available.
LOCAL_TZ = ZoneInfo(settings.TZ) if settings.TZ else None


def _to_dt(value: Any) -> datetime | None:
    """Normalize incoming values into timezone-aware ``datetime`` objects.

    *What:* Converts strings or naive datetimes into aware datetimes.
    *When:* Called before formatting a timestamp for display.
    *Why:* Working with consistent timezone-aware objects prevents confusing
    offsets in the UI.
    *How:* Try ``fromisoformat`` and attach/convert timezones when needed.
    """

    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value:
        # Try fromisoformat first; fall back to lenient parse if you add it later
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
    """Turn any supported timestamp into a friendly date-time string."""

    dt = _to_dt(value)
    return dt.strftime(fmt) if dt else ""


def fmt_date(value: Any, fmt: str = "%Y-%m-%d") -> str:
    """Format only the date portion so HTML tables look tidy."""

    dt = _to_dt(value)
    return dt.strftime(fmt) if dt else ""


def fmt_time(value: Any, fmt: str = "%I:%M %p") -> str:
    """Format only the time portion for quick-at-a-glance reading."""

    dt = _to_dt(value)
    return dt.strftime(fmt) if dt else ""


# Register filters
# ``env.filters`` is Jinja's plugin spot. By registering here we make these
# helpers available inside every HTML template without additional imports.
TEMPLATES.env.filters["fmt_dt"] = fmt_dt
TEMPLATES.env.filters["fmt_date"] = fmt_date
TEMPLATES.env.filters["fmt_time"] = fmt_time

# ---------- DB init/migrations (unchanged) ----------
# ``create_all`` ensures tables exist for brand-new databases, while
# ``run_migrations`` upgrades existing installations. Running these on import
# makes the app self-starting during development and tests.
Base.metadata.create_all(bind=engine)
run_migrations(engine)

# ---------- Session middleware (UI login persistence) ----------
# Sessions remember who is logged in between page loads. This middleware stores
# the login token inside a secure cookie so the browser can keep the session
# alive.
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.APP_SECRET,
    session_cookie=settings.SESSION_COOKIE_NAME,
    max_age=settings.SESSION_MAX_AGE,
    same_site="lax",
    https_only=False,  # set True once the app is always accessed via HTTPS at the edge
)

# ---------- Routers ----------
# The following blocks plug in different groups of URL routes. Each router is a
# collection of views that handle specific tasks (login, API endpoints, etc.).

# UI login routes (no session required)
from .routers import auth_ui as auth_ui_router  # type: ignore

app.include_router(auth_ui_router.router)

# UI pages/actions (session required via router dependency)
from .routers import ui as ui_router  # type: ignore

app.include_router(ui_router.router)

# APIs (headless; X-API-Key required via dependency inside each API router)
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

from .routers import api_projects as api_projects_router  # type: ignore

app.include_router(api_projects_router.router, prefix="")

# ---------- Exception handling ----------
# This catch-all handler ensures the browser-friendly login redirect happens
# whenever someone hits a protected page without being authenticated.


# Redirect HTML 401s to /login while keeping JSON 401s for API/headless clients.
@app.exception_handler(StarletteHTTPException)
async def handle_http_exceptions(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 401:
        accept = (request.headers.get("accept") or "").lower()
        path = request.url.path
        is_html = "text/html" in accept
        is_api = path.startswith("/api")
        is_login = path.startswith("/login")
        if is_html and not is_api and not is_login:
            return RedirectResponse(url=f"/login?next={request.url}", status_code=302)
        return JSONResponse({"detail": exc.detail or "Unauthorized"}, status_code=401)
    return JSONResponse({"detail": exc.detail or "Error"}, status_code=exc.status_code)


__all__ = ["app"]
