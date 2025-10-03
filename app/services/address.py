from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from ..core.config import settings

logger = logging.getLogger(__name__)

class AddressServiceNotConfigured(Exception):
    """Raised when address autocomplete credentials are missing."""


def _ensure_configured() -> None:
    if not settings.SMARTY_AUTH_ID or not settings.SMARTY_AUTH_TOKEN:
        raise AddressServiceNotConfigured("Address autocomplete is not configured")


def _format_zip(components: Dict[str, Any]) -> str:
    zipcode = (components.get("zipcode") or "").strip()
    plus4 = (components.get("plus4_code") or "").strip()
    if zipcode and plus4:
        return f"{zipcode}-{plus4}"
    return zipcode


async def fetch_autocomplete_suggestions(
    search: str,
    *,
    city: Optional[str] = None,
    state: Optional[str] = None,
    postal_code: Optional[str] = None,
    max_results: int = 10,
) -> List[Dict[str, Any]]:
    """Return USPS-verified address suggestions via SmartyStreets Autocomplete Pro."""

    _ensure_configured()

    if not search or not search.strip():
        return []

    params: Dict[str, Any] = {
        "search": search.strip(),
        "auth-id": settings.SMARTY_AUTH_ID,
        "auth-token": settings.SMARTY_AUTH_TOKEN,
        "source": "all",
        "max_results": max_results,
    }

    if city:
        params["include_only_cities"] = city
    if state:
        params["include_only_states"] = state
    if postal_code:
        params["include_only_zip_codes"] = postal_code

    timeout = httpx.Timeout(6.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(settings.SMARTY_AUTOCOMPLETE_URL, params=params)

    if response.status_code == 401:
        logger.warning("SmartyStreets authentication failed for address autocomplete")
        raise httpx.HTTPStatusError("Unauthorized", request=response.request, response=response)
    if response.status_code >= 500:
        logger.error("SmartyStreets service error %s", response.status_code)
        raise httpx.HTTPStatusError("Service unavailable", request=response.request, response=response)

    data = response.json()
    suggestions: List[Dict[str, Any]] = []
    for item in data.get("suggestions", []):
        suggestion = {
            "street_line": item.get("street_line") or item.get("primary_line"),
            "secondary": item.get("secondary") or "",
            "city": item.get("city"),
            "state": item.get("state"),
            "postal_code": item.get("zipcode"),
            "entries": item.get("entries"),
            "source": item.get("source"),
        }
        suggestions.append(suggestion)

    return suggestions


async def verify_postal_address(
    *,
    street_line: str,
    city: Optional[str] = None,
    state: Optional[str] = None,
    postal_code: Optional[str] = None,
    secondary: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Verify a selected address via SmartyStreets US Street API."""

    _ensure_configured()

    payload: List[Dict[str, Any]] = [
        {
            "street": street_line,
            "city": city,
            "state": state,
            "zipcode": postal_code,
            "secondary": secondary or None,
            "candidates": 1,
        }
    ]

    timeout = httpx.Timeout(6.0)
    params = {
        "auth-id": settings.SMARTY_AUTH_ID,
        "auth-token": settings.SMARTY_AUTH_TOKEN,
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            settings.SMARTY_STREET_URL,
            params=params,
            json=payload,
        )

    if response.status_code == 401:
        logger.warning("SmartyStreets authentication failed for address verification")
        raise httpx.HTTPStatusError("Unauthorized", request=response.request, response=response)
    if response.status_code >= 500:
        logger.error("SmartyStreets street API error %s", response.status_code)
        raise httpx.HTTPStatusError("Service unavailable", request=response.request, response=response)

    candidates = response.json()
    if not candidates:
        return None

    candidate = candidates[0]
    components = candidate.get("components") or {}

    verified = {
        "delivery_line_1": candidate.get("delivery_line_1"),
        "delivery_line_2": candidate.get("delivery_line_2") or "",
        "last_line": candidate.get("last_line"),
        "city": components.get("city_name"),
        "state": components.get("state_abbreviation"),
        "postal_code": _format_zip(components),
        "county": candidate.get("metadata", {}).get("county_name"),
        "dpv_match_code": candidate.get("analysis", {}).get("dpv_match_code"),
        "footnotes": candidate.get("analysis", {}).get("footnotes"),
    }
    return verified
