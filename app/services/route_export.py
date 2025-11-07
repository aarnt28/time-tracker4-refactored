"""Beginner-friendly overview for this module.

WHAT: Handles the logic defined in "app/services/route_export.py" for the Time Tracker app.
WHEN: Invoked when its functions or classes are imported and called.
WHY: Provides supporting behaviour so the service runs smoothly.
HOW: Read the inline comments and docstrings below for the step-by-step flow.

File: app/services/route_export.py
"""


from __future__ import annotations

import logging
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Tuple

import httpx
from fpdf import FPDF
from fpdf.enums import XPos, YPos

from ..core.config import settings
from ..schemas.route import LatLng, RouteExportRequest

LOGGER = logging.getLogger(__name__)

STATIC_MAP_URL = "https://maps.googleapis.com/maps/api/staticmap"
ROUTE_PDF_FONT_FAMILY = "DejaVu"
ROUTE_PDF_FONT_FILES = {
    "": "DejaVuSans.ttf",
    "B": "DejaVuSans-Bold.ttf",
    "I": "DejaVuSans-Oblique.ttf",
}


def _font_path(filename: str) -> Path:
    return (
        Path(__file__)
        .resolve()
        .parent
        .parent
        .joinpath("static", "fonts", filename)
    )


def _register_route_fonts(pdf: FPDF) -> None:
    for style, filename in ROUTE_PDF_FONT_FILES.items():
        font_key = f"{ROUTE_PDF_FONT_FAMILY.lower()}{style.upper()}"
        if font_key in pdf.fonts:
            continue
        font_file = _font_path(filename)
        if not font_file.exists():
            LOGGER.error("Route export font missing: %s", font_file)
            raise FileNotFoundError(font_file)
        pdf.add_font(ROUTE_PDF_FONT_FAMILY, style=style, fname=str(font_file), uni=True)


def _format_distance(meters: Optional[float], fallback: Optional[str] = None) -> str:
    if meters is None or meters <= 0:
        return fallback or "N/A"
    miles = meters / 1609.344
    if miles >= 10:
        return f"{miles:.0f} mi"
    if miles >= 1:
        return f"{miles:.1f} mi"
    yards = meters * 1.09361
    if yards >= 100:
        return f"{yards:.0f} yd"
    return f"{meters:.0f} m"


def _format_duration(seconds: Optional[float], fallback: Optional[str] = None) -> str:
    if seconds is None or seconds <= 0:
        return fallback or "N/A"
    seconds = int(round(seconds))
    hours, remainder = divmod(seconds, 3600)
    minutes, remaining_seconds = divmod(remainder, 60)
    pieces: List[str] = []
    if hours:
        pieces.append(f"{hours}h")
    if minutes:
        pieces.append(f"{minutes}m")
    if not pieces and remaining_seconds:
        pieces.append(f"{remaining_seconds}s")
    return " ".join(pieces) or "N/A"


def _safe_latlng(value: Optional[LatLng]) -> Optional[Tuple[float, float]]:
    if not value:
        return None
    lat = float(value.lat)
    lng = float(value.lng)
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return None
    return (lat, lng)


def _build_marker_label(index: int) -> str:
    # Static Maps markers accept a single alphanumeric character.
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    if 0 <= index < len(alphabet):
        return alphabet[index]
    return ""


async def fetch_static_map_image(payload: RouteExportRequest) -> Optional[bytes]:
    """Fetch a static map rendering for the supplied route."""

    api_key = (settings.GOOGLE_MAPS_API_KEY or "").strip()
    if not api_key:
        return None

    params: List[Tuple[str, str]] = [
        ("size", "640x400"),
        ("scale", "2"),
        ("maptype", "roadmap"),
        ("format", "png"),
        ("key", api_key),
    ]

    if payload.overview_polyline:
        params.append(("path", f"weight:5|color:0x0091EAFF|enc:{payload.overview_polyline}"))

    markers: List[Tuple[str, str]] = []
    first_leg = payload.legs[0] if payload.legs else None
    first_point = _safe_latlng(first_leg.start_location if first_leg else None)
    if first_point:
        markers.append(("markers", f"label:S|color:0x2E7D32|{first_point[0]:.6f},{first_point[1]:.6f}"))

    for index, leg in enumerate(payload.legs, start=0):
        point = _safe_latlng(leg.end_location)
        if not point:
            continue
        label = _build_marker_label(index)
        markers.append(("markers", f"label:{label}|color:0xC62828|{point[0]:.6f},{point[1]:.6f}"))

    params.extend(markers)

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(STATIC_MAP_URL, params=params)
        if response.status_code == httpx.codes.OK and response.content:
            return bytes(response.content)
        LOGGER.warning(
            "Static map request failed with status %s", response.status_code
        )
    except Exception as exc:  # pragma: no cover - log unexpected transport errors
        LOGGER.warning("Static map request failed: %s", exc)
    return None


def render_route_overview_pdf(
    payload: RouteExportRequest, map_image: Optional[bytes] = None
) -> bytes:
    """Render a PDF summarising the supplied route."""

    pdf = FPDF(unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    _register_route_fonts(pdf)

    effective_width = pdf.w - pdf.l_margin - pdf.r_margin

    pdf.set_font(ROUTE_PDF_FONT_FAMILY, "B", 16)
    pdf.cell(effective_width, 10, "Route Overview", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    generated_at = datetime.now(timezone.utc).astimezone()
    pdf.set_font(ROUTE_PDF_FONT_FAMILY, size=10)
    pdf.cell(
        effective_width,
        5,
        f"Generated: {generated_at.strftime('%Y-%m-%d %H:%M %Z')}",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.ln(2)

    origin_display = payload.origin_display or payload.origin_name
    pdf.set_font(ROUTE_PDF_FONT_FAMILY, "", 11)
    pdf.multi_cell(effective_width, 5.5, f"Origin: {origin_display}")

    total_distance = _format_distance(payload.total_distance_meters)
    total_duration = _format_duration(payload.total_duration_seconds)
    pdf.multi_cell(effective_width, 5.5, f"Total distance: {total_distance}")
    pdf.multi_cell(effective_width, 5.5, f"Total drive time: {total_duration}")
    pdf.ln(4)

    image_buffer = BytesIO(map_image) if map_image else None
    if image_buffer:
        pdf.set_font(ROUTE_PDF_FONT_FAMILY, "B", 12)
        pdf.cell(effective_width, 6, "Route map", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(1)
        image_buffer.seek(0)
        pdf.image(image_buffer, w=effective_width)
        pdf.ln(4)
    else:
        pdf.set_font(ROUTE_PDF_FONT_FAMILY, "I", 10)
        pdf.multi_cell(
            effective_width,
            5,
            "Map preview unavailable. Ensure the Static Maps API is enabled and rebuild the route.",
        )
        pdf.ln(4)

    if payload.stops:
        pdf.set_font(ROUTE_PDF_FONT_FAMILY, "B", 12)
        pdf.cell(effective_width, 6, "Stops", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font(ROUTE_PDF_FONT_FAMILY, "", 11)
        for stop in payload.stops:
            label = f"{stop.order}. {stop.name or stop.address}"
            pdf.multi_cell(effective_width, 5, label)
            if stop.address:
                pdf.set_font(ROUTE_PDF_FONT_FAMILY, size=10)
                pdf.multi_cell(effective_width, 4.5, f"   {stop.address}")
                pdf.set_font(ROUTE_PDF_FONT_FAMILY, "", 11)
        pdf.ln(2)

    pdf.set_font(ROUTE_PDF_FONT_FAMILY, "B", 12)
    pdf.cell(effective_width, 6, "Leg breakdown", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font(ROUTE_PDF_FONT_FAMILY, "", 11)
    for index, leg in enumerate(payload.legs, start=1):
        header = f"Leg {index}: {leg.start_address or 'N/A'} -> {leg.end_address or 'N/A'}"
        pdf.multi_cell(effective_width, 5, header)
        distance_text = _format_distance(leg.distance_meters, leg.distance_text)
        duration_text = _format_duration(leg.duration_seconds, leg.duration_text)
        pdf.set_font(ROUTE_PDF_FONT_FAMILY, size=10)
        pdf.multi_cell(
            effective_width,
            4.5,
            f"   Distance: {distance_text} | Duration: {duration_text}",
        )
        pdf.set_font(ROUTE_PDF_FONT_FAMILY, "", 11)
        pdf.ln(1)

    output = pdf.output(dest="S")
    if isinstance(output, str):
        return output.encode("latin1")
    return bytes(output)


async def generate_route_overview_pdf(payload: RouteExportRequest) -> bytes:
    """High-level helper that downloads the map and renders the PDF."""

    map_image = await fetch_static_map_image(payload)
    return render_route_overview_pdf(payload, map_image=map_image)