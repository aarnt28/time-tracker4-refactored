from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx

from ..core.config import settings

logger = logging.getLogger(__name__)


class AddressServiceNotConfigured(Exception):
    """Raised when address autocomplete credentials are missing."""


def _ensure_configured() -> None:
    if not settings.GOOGLE_MAPS_API_KEY:
        raise AddressServiceNotConfigured("Address tools are not configured")


def _build_last_line(city: Optional[str], state: Optional[str], postal_code: Optional[str]) -> str:
    parts: List[str] = []
    if city and state:
        parts.append(f"{city}, {state}")
    else:
        if city:
            parts.append(str(city))
        if state:
            parts.append(str(state))
    if postal_code:
        parts.append(str(postal_code))
    return " ".join(part for part in parts if part).strip()


def _component_map(components: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    mapping: Dict[str, Dict[str, Any]] = {}
    for component in components:
        for type_name in component.get("types", []):
            mapping.setdefault(type_name, component)
    return mapping


def _parse_place_details(details: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not details:
        return {}

    components = details.get("address_components") or []
    mapping = _component_map(components)

    street_number = (mapping.get("street_number") or {}).get("long_name")
    route = (mapping.get("route") or {}).get("long_name")
    street_line = " ".join(part for part in [street_number, route] if part)

    secondary_parts: List[str] = []
    for key in ("subpremise", "premise", "floor", "unit", "room"):
        value = (mapping.get(key) or {}).get("long_name")
        if value:
            secondary_parts.append(value)
    secondary = " ".join(secondary_parts).strip()

    city = (mapping.get("locality") or {}).get("long_name")
    if not city:
        city = (mapping.get("postal_town") or {}).get("long_name")
    if not city:
        city = (mapping.get("sublocality") or {}).get("long_name")

    state_component = mapping.get("administrative_area_level_1") or {}
    state = state_component.get("short_name") or state_component.get("long_name")

    postal_code = (mapping.get("postal_code") or {}).get("long_name")

    country_component = mapping.get("country") or {}
    country = country_component.get("short_name") or country_component.get("long_name")

    county = (mapping.get("administrative_area_level_2") or {}).get("long_name")

    geometry = details.get("geometry") or {}
    location = geometry.get("location") or {}
    lat = location.get("lat")
    lon = location.get("lng")

    parsed = {
        "street_line": street_line or None,
        "secondary": secondary or "",
        "city": city or None,
        "state": state or None,
        "postal_code": postal_code or None,
        "country": country or None,
        "county": county or None,
        "lat": float(lat) if isinstance(lat, (int, float)) else None,
        "lon": float(lon) if isinstance(lon, (int, float)) else None,
        "formatted": details.get("formatted_address"),
        "place_types": details.get("types") or [],
    }
    return parsed


def _compose_components_filter(
    city: Optional[str], state: Optional[str], postal_code: Optional[str]
) -> Optional[str]:
    region_code = (settings.GOOGLE_ADDRESS_VALIDATION_REGION_CODE or "").strip()
    if not region_code:
        return None
    # Google Places Autocomplete only accepts country filters in the components
    # query parameter. State, city, or postal code filters trigger INVALID_REQUEST
    # responses, so we restrict the filter to the configured country.
    return f"country:{region_code}"


def _summarize_verdict(verdict: Dict[str, Any]) -> Optional[str]:
    if not verdict:
        return None
    flags: List[str] = []
    if verdict.get("hasUnconfirmedComponents"):
        flags.append("unconfirmed_components")
    if verdict.get("hasInferredComponents"):
        flags.append("inferred_components")
    if verdict.get("hasReplacedComponents"):
        flags.append("replaced_components")
    if verdict.get("addressComplete") is False:
        flags.append("address_incomplete")
    if not flags:
        return None
    return ", ".join(flags)


def _raise_for_status(response: httpx.Response, context: str) -> None:
    if response.status_code in {401, 403}:
        logger.warning("Google Maps authentication failed for %s", context)
    elif response.status_code >= 500:
        logger.error("Google service error %s during %s", response.status_code, context)
    elif response.status_code >= 400:
        logger.error("Google request error %s during %s", response.status_code, context)
    response.raise_for_status()


async def _fetch_place_details(
    client: httpx.AsyncClient, place_id: str
) -> Optional[Dict[str, Any]]:
    params = {
        "place_id": place_id,
        "key": settings.GOOGLE_MAPS_API_KEY,
        "fields": "address_component,geometry,formatted_address,types",
    }
    response = await client.get(settings.GOOGLE_PLACES_DETAILS_URL, params=params)
    _raise_for_status(response, "place details")

    data = response.json()
    status = data.get("status")
    if status and status != "OK":
        if status in {"NOT_FOUND", "ZERO_RESULTS"}:
            logger.info("Google place %s not found (%s)", place_id, status)
            return None
        logger.warning(
            "Google place details error for %s: %s (%s)",
            place_id,
            status,
            data.get("error_message"),
        )
        return None

    return data.get("result") or None


def _build_validation_payload(
    street_line: str,
    city: Optional[str],
    state: Optional[str],
    postal_code: Optional[str],
    secondary: Optional[str],
    place_details: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    parsed = _parse_place_details(place_details)

    address_lines: List[str] = []
    line1 = parsed.get("street_line") or (street_line.strip() if street_line else "")
    if line1:
        address_lines.append(line1)
    if parsed.get("secondary"):
        address_lines.append(parsed["secondary"])
    elif secondary and secondary.strip():
        address_lines.append(secondary.strip())

    payload: Dict[str, Any] = {}
    if address_lines:
        payload["addressLines"] = address_lines

    locality = parsed.get("city") or (city.strip() if city else None)
    if locality:
        payload["locality"] = locality

    admin_area = parsed.get("state") or (state.strip() if state else None)
    if admin_area:
        payload["administrativeArea"] = admin_area

    postal = parsed.get("postal_code") or (postal_code.strip() if postal_code else None)
    if postal:
        payload["postalCode"] = postal

    region = parsed.get("country") or settings.GOOGLE_ADDRESS_VALIDATION_REGION_CODE
    if region:
        payload["regionCode"] = region

    return payload


def _map_suggestion(
    prediction: Dict[str, Any], place_details: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    parsed = _parse_place_details(place_details)
    structured = prediction.get("structured_formatting") or {}
    description = prediction.get("description")

    suggestion = {
        "street_line": parsed.get("street_line")
        or structured.get("main_text")
        or description,
        "secondary": parsed.get("secondary") or structured.get("secondary_text") or "",
        "city": parsed.get("city"),
        "state": parsed.get("state"),
        "postal_code": parsed.get("postal_code"),
        "country": parsed.get("country"),
        "formatted": parsed.get("formatted") or description,
        "place_id": prediction.get("place_id"),
        "result_type": (prediction.get("types") or parsed.get("place_types") or [None])[0],
        "confidence": None,
        "lat": parsed.get("lat"),
        "lon": parsed.get("lon"),
        "county": parsed.get("county"),
    }
    return suggestion


def _map_verified_address(result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not result:
        return None

    address_info = result.get("address") or {}
    postal_address = address_info.get("postalAddress") or {}
    address_lines = postal_address.get("addressLines") or []

    delivery_line_1 = address_lines[0] if address_lines else None
    delivery_line_2 = " ".join(address_lines[1:]) if len(address_lines) > 1 else ""
    if not delivery_line_1:
        delivery_line_1 = address_info.get("formattedAddress")

    city = postal_address.get("locality")
    state = postal_address.get("administrativeArea")
    postal_code = postal_address.get("postalCode")
    country = postal_address.get("regionCode")

    county = None
    for component in address_info.get("addressComponents") or []:
        component_type = component.get("componentType")
        if component_type == "administrative_area_level_2":
            county = (component.get("componentName") or {}).get("text")
            if county:
                break

    geocode = result.get("geocode") or {}
    location = geocode.get("location") or {}
    latitude = location.get("latitude")
    longitude = location.get("longitude")
    place_id = geocode.get("placeId")

    last_line = _build_last_line(city, state, postal_code)
    verdict = result.get("verdict") or {}

    verified = {
        "delivery_line_1": delivery_line_1 or "",
        "delivery_line_2": delivery_line_2 or "",
        "last_line": last_line or "",
        "city": city,
        "state": state,
        "postal_code": postal_code,
        "country": country,
        "county": county,
        "dpv_match_code": None,
        "footnotes": _summarize_verdict(verdict),
        "latitude": float(latitude) if isinstance(latitude, (int, float)) else None,
        "longitude": float(longitude) if isinstance(longitude, (int, float)) else None,
        "place_id": place_id,
        "confidence": None,
    }
    return verified


async def fetch_autocomplete_suggestions(
    search: str,
    *,
    city: Optional[str] = None,
    state: Optional[str] = None,
    postal_code: Optional[str] = None,
    max_results: int = 10,
) -> List[Dict[str, Any]]:
    """Return address suggestions using Google Places autocomplete."""

    _ensure_configured()

    if not search or not search.strip():
        return []

    params: Dict[str, Any] = {
        "input": search.strip(),
        "key": settings.GOOGLE_MAPS_API_KEY,
        "types": "address",
    }

    components_filter = _compose_components_filter(city, state, postal_code)
    if components_filter:
        params["components"] = components_filter

    timeout = httpx.Timeout(6.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.get(settings.GOOGLE_PLACES_AUTOCOMPLETE_URL, params=params)

        _raise_for_status(response, "address autocomplete")

        data = response.json()
        status = data.get("status")
        if status and status not in {"OK", "ZERO_RESULTS"}:
            logger.warning(
                "Google autocomplete error: %s (%s)", status, data.get("error_message")
            )
            return []

        predictions = data.get("predictions") or []
        predictions = predictions[:max_results]

        async def enrich_prediction(prediction: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            place_id = prediction.get("place_id")
            details = None
            if place_id:
                try:
                    details = await _fetch_place_details(client, place_id)
                except httpx.HTTPError as exc:
                    logger.warning("Failed to fetch place details for %s: %s", place_id, exc)
                    details = None
            return _map_suggestion(prediction, details)

        tasks = [enrich_prediction(prediction) for prediction in predictions]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    suggestions: List[Dict[str, Any]] = []
    for result in results:
        if isinstance(result, Exception):
            logger.warning("Google suggestion enrichment failed: %s", result)
            continue
        if result:
            suggestions.append(result)

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
    """Verify a selected address via Google's Address Validation API."""

    _ensure_configured()

    if not street_line or not street_line.strip():
        return None

    timeout = httpx.Timeout(6.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        place_details = None
        if place_id:
            try:
                place_details = await _fetch_place_details(client, place_id)
            except httpx.HTTPError as exc:
                logger.warning("Failed to fetch place %s for verification: %s", place_id, exc)

        payload = {
            "address": _build_validation_payload(
                street_line=street_line,
                city=city,
                state=state,
                postal_code=postal_code,
                secondary=secondary,
                place_details=place_details,
            )
        }

        params = {"key": settings.GOOGLE_MAPS_API_KEY}
        response = await client.post(
            settings.GOOGLE_ADDRESS_VALIDATION_URL, params=params, json=payload
        )

    _raise_for_status(response, "address verification")

    data = response.json()
    result = data.get("result") or {}
    if not result:
        return None

    return _map_verified_address(result)

