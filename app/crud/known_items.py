"""Helpers for the ``known_items`` materialized view (kept intentionally small)."""

from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ..models.known_items import known_items


# The historic application referenced this module for ad-hoc lookups against the
# ``known_items`` database view. The current codebase relies on other flows, so
# we leave the imports and context here for posterity and future expansion.
