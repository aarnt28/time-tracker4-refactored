"""Helper utilities for teaching Jinja2 how to format our data.

Templates are the presentation layer. This module explains *what* formatting
helpers exist, *when* they are used (whenever an HTML page renders), *why* we
need them (to keep the UI tidy and consistent), and *how* to hook them into the
Jinja environment.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi.templating import Jinja2Templates

from .config import settings

# We keep this module tiny and focused: build a templates environment and register filters.

_LOCAL_TZ = ZoneInfo(settings.TZ) if settings.TZ else None


def _to_dt(value: Any) -> datetime | None:
    """Convert strings/numbers into timezone-aware datetimes for safe formatting."""

    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str) and value:
        try:
            dt = datetime.fromisoformat(value)
        except Exception:
            return None
    else:
        return None

    if dt.tzinfo is None and _LOCAL_TZ:
        dt = dt.replace(tzinfo=_LOCAL_TZ)
    if _LOCAL_TZ:
        dt = dt.astimezone(_LOCAL_TZ)
    return dt


def _fmt_dt(value: Any, fmt: str = "%Y-%m-%d %I:%M %p") -> str:
    """Format a timestamp with both date and time so tables remain legible."""

    dt = _to_dt(value)
    return dt.strftime(fmt) if dt else ""


def _fmt_dt_compact(value: Any) -> str:
    """Condensed date/time format for places where space is tight (e.g. badges)."""

    dt = _to_dt(value)
    if not dt:
        return ""
    return f"{dt.month}/{dt.day} {dt.strftime('%H:%M')}"


def _fmt_date(value: Any, fmt: str = "%Y-%m-%d") -> str:
    """Return only the date portion, useful for headings and filters."""

    dt = _to_dt(value)
    return dt.strftime(fmt) if dt else ""


def _fmt_time(value: Any, fmt: str = "%I:%M %p") -> str:
    """Return only the time, matching the rest of the dashboard styling."""

    dt = _to_dt(value)
    return dt.strftime(fmt) if dt else ""


def _fmt_currency(value: Any) -> str:
    """Add a dollar sign and commas to any numeric value so costs look professional."""

    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    return f"${number:,.2f}"


def get_templates() -> Jinja2Templates:
    """Create a ``Jinja2Templates`` instance with our standard filters registered."""

    templates = Jinja2Templates(directory=str(settings.TEMPLATES_DIR))
    env = templates.env
    # These assignments teach Jinja new “verbs” it can use from HTML using the
    # ``{{ value|filter_name }}`` syntax.
    env.filters["fmt_dt"] = _fmt_dt
    env.filters["fmt_dt_compact"] = _fmt_dt_compact
    env.filters["fmt_date"] = _fmt_date
    env.filters["fmt_time"] = _fmt_time
    env.filters["fmt_currency"] = _fmt_currency
    return templates

