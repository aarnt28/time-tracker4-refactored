"""Beginner-friendly overview for this module.

WHAT: Handles the logic defined in "app/routers/address.py" for the Time Tracker app.
WHEN: Invoked when its functions or classes are imported and called.
WHY: Provides supporting behaviour so the service runs smoothly.
HOW: Read the inline comments and docstrings below for the step-by-step flow.

File: app/routers/address.py
"""


from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status

from ..deps.auth import require_ui_or_token
from ..services.address import (
    AddressServiceNotConfigured,
    fetch_autocomplete_suggestions,
    verify_postal_address,
)

router = APIRouter(
    prefix="/api/v1/address",
    tags=["address"],
    dependencies=[Depends(require_ui_or_token)],
)


@router.get("/suggest")
async def suggest_address(
    q: str = Query(..., min_length=2, alias="query"),
    city: str | None = Query(default=None),
    state: str | None = Query(default=None),
    postal_code: str | None = Query(default=None, alias="zip"),
    limit: int = Query(default=8, ge=1, le=20),
):
    try:
        suggestions = await fetch_autocomplete_suggestions(
            q,
            city=city,
            state=state,
            postal_code=postal_code,
            max_results=limit,
        )
    except AddressServiceNotConfigured:
        # When the autocomplete integration is not configured we silently fall
        # back to manual entry.  Returning an empty list keeps the UI happy
        # without surfacing a 503 to the browser logs.
        return {"suggestions": []}
    return {"suggestions": suggestions}


@router.get("/verify")
async def verify_address(
    street_line: str = Query(..., alias="street"),
    city: str | None = Query(default=None),
    state: str | None = Query(default=None),
    postal_code: str | None = Query(default=None, alias="zip"),
    secondary: str | None = Query(default=None),
    place_id: str | None = Query(default=None),
):
    try:
        candidate = await verify_postal_address(
            street_line=street_line,
            city=city,
            state=state,
            postal_code=postal_code,
            secondary=secondary,
            place_id=place_id,
        )
    except AddressServiceNotConfigured:
        # Fall back to manual entry when verification is unavailable.
        return {"candidate": None}
    if not candidate:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Address not verified")
    return {"candidate": candidate}