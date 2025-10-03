from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from ..core.config import settings

logger = logging.getLogger(__name__)


class AddressServiceNotConfigured(Exception):
    """Raised when address autocomplete credentials are missing."""


def _ensure_configured() -> None:
    if not settings.GEOAPIFY_API_KEY:
        raise AddressServiceNotConfigured("Address autocomplete is not configured")


def _compose_street_line(properties: Dict[str, Any]) -> str:
    line1 = (properties.get("address_line1") or "").strip()
    if line1:
        return line1
    parts = [properties.get("housenumber"), properties.get("street")]
    return " ".join(part for part in parts if part).strip()


def _format_postal_code(properties: Dict[str, Any]) -> str:
    postcode = (properties.get("postcode") or "").strip()
    extension = (properties.get("postcode_ext") or "").strip()
    if postcode and extension:
        return f"{postcode}-{extension}"
    return postcode


def _extract_state(properties: Dict[str, Any]) -> str:
    return (properties.get("state_code") or properties.get("state") or "").strip()


async def fetch_autocomplete_suggestions(
    search: str,
    *,
    city: Optional[str] = None,
    state: Optional[str] = None,
    postal_code: Optional[str] = None,
    max_results: int = 10,
) -> List[Dict[str, Any]]:
    """Return address suggestions via Geoapify's autocomplete service."""

    _ensure_configured()

    if not search or not search.strip():
        return []

    search_text = search.strip()

    params: Dict[str, Any] = {
        "text": search_text,
        "apiKey": settings.GEOAPIFY_API_KEY,
        "format": "json",
        "limit": max_results,
        "filter": "countrycode:us",
        "lang": "en",
    }

    context_parts: List[str] = []
    if city:
        context_parts.append(city.strip())
    if state:
        context_parts.append(state.strip())
    if postal_code:
        context_parts.append(postal_code.strip())
    if context_parts:
        params["text"] = ", ".join([search_text, ", ".join(context_parts)])

    timeout = httpx.Timeout(6.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(settings.GEOAPIFY_AUTOCOMPLETE_URL, params=params)

    if response.status_code in {401, 403}:
        logger.warning("Geoapify authentication failed for address autocomplete")
        raise httpx.HTTPStatusError("Unauthorized", request=response.request, response=response)
    if response.status_code >= 500:
        logger.error("Geoapify service error %s", response.status_code)
        raise httpx.HTTPStatusError("Service unavailable", request=response.request, response=response)

    data = response.json()
    suggestions: List[Dict[str, Any]] = []
    for feature in data.get("features", []):
        properties = feature.get("properties") or {}
        suggestion = {
            "street_line": _compose_street_line(properties),
            "secondary": properties.get("address_line2") or "",
            "city": properties.get("city") or properties.get("county"),
            "state": _extract_state(properties),
            "postal_code": properties.get("postcode"),
            "entries": None,
            "source": "Geoapify",
            "place_id": properties.get("place_id"),
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
    place_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Verify a selected address via Geoapify's geocoding service."""

    _ensure_configured()

    timeout = httpx.Timeout(6.0)
    base_params: Dict[str, Any] = {
        "apiKey": settings.GEOAPIFY_API_KEY,
        "format": "json",
        "limit": 1,
    }

    async with httpx.AsyncClient(timeout=timeout) as client:
        if place_id:
            params = dict(base_params)
            params["place_id"] = place_id
            response = await client.get(settings.GEOAPIFY_PLACE_URL, params=params)
        else:
            params = dict(base_params)
            text_parts: List[str] = [street_line]
            if secondary:
                text_parts.append(secondary)
            locality = ", ".join(part for part in [city, state] if part)
            if locality:
                text_parts.append(locality)
            if postal_code:
                text_parts.append(str(postal_code))
            params["text"] = ", ".join(part for part in text_parts if part)
            params["filter"] = "countrycode:us"
            response = await client.get(settings.GEOAPIFY_SEARCH_URL, params=params)

    if response.status_code in {401, 403}:
        logger.warning("Geoapify authentication failed for address verification")
        raise httpx.HTTPStatusError("Unauthorized", request=response.request, response=response)
    if response.status_code >= 500:
        logger.error("Geoapify geocoding error %s", response.status_code)
        raise httpx.HTTPStatusError("Service unavailable", request=response.request, response=response)

    payload = response.json()
    features = None
    if isinstance(payload, dict):
        features = payload.get("features")
    elif isinstance(payload, list):
        features = payload
    if not features:
        return None

    candidate_raw = features[0]
    properties = candidate_raw.get("properties") or {}

    verified = {
        "delivery_line_1": _compose_street_line(properties),
        "delivery_line_2": properties.get("address_line2") or "",
        "last_line": properties.get("formatted"),
        "city": properties.get("city") or properties.get("county"),
        "state": _extract_state(properties),
        "postal_code": _format_postal_code(properties),
        "county": properties.get("county"),
        "confidence": (properties.get("rank") or {}).get("confidence"),
        "place_id": properties.get("place_id"),
        "latitude": properties.get("lat"),
        "longitude": properties.get("lon"),
    }
    return verified
