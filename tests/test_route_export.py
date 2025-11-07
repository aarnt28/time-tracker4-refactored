"""Beginner-friendly overview for this module.

WHAT: Handles the logic defined in "tests/test_route_export.py" for the Time Tracker app.
WHEN: Invoked when its functions or classes are imported and called.
WHY: Provides supporting behaviour so the service runs smoothly.
HOW: Read the inline comments and docstrings below for the step-by-step flow.

File: tests/test_route_export.py
"""


import asyncio
import base64
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("GOOGLE_MAPS_API_KEY", "test-key")
os.environ.setdefault("DATA_DIR", str(ROOT / "data"))

from app.schemas.route import LatLng, RouteExportRequest, RouteLeg, RouteStop
from app.services import route_export


def build_sample_payload() -> RouteExportRequest:
    return RouteExportRequest(
        origin_name="Service Origin",
        origin_address="1409 Parkview St, Longview, TX 75601",
        origin_display="1409 Parkview St, Longview, TX 75601",
        stops=[
            RouteStop(order=2, name="Client B", address="456 Elm St, Plano, TX"),
            RouteStop(order=1, name="Client A", address="123 Main St, Dallas, TX"),
        ],
        legs=[
            RouteLeg(
                start_address="Service Origin",
                end_address="123 Main St, Dallas, TX",
                distance_text="130 mi",
                distance_meters=209215.0,
                duration_text="2h 5m",
                duration_seconds=7500.0,
                start_location=LatLng(lat=32.5086, lng=-94.7424),
                end_location=LatLng(lat=32.7767, lng=-96.7970),
            ),
            RouteLeg(
                start_address="123 Main St, Dallas, TX",
                end_address="456 Elm St, Plano, TX",
                distance_text="20 mi",
                distance_meters=32186.0,
                duration_text="30m",
                duration_seconds=1800.0,
                start_location=LatLng(lat=32.7767, lng=-96.7970),
                end_location=LatLng(lat=33.0198, lng=-96.6989),
            ),
        ],
        overview_polyline="abcd",
        total_distance_meters=241401.0,
        total_duration_seconds=9300.0,
    )


def test_render_route_overview_pdf_produces_document():
    payload = build_sample_payload()
    pdf_bytes = route_export.render_route_overview_pdf(payload, map_image=None)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 500


def test_generate_route_overview_pdf_includes_map(monkeypatch):
    payload = build_sample_payload()
    sample_png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR4nGMAAQAABQABDQottAAAAABJRU5ErkJggg=="
    )

    async def fake_fetch_static_map(_payload):
        return sample_png

    monkeypatch.setattr(route_export, "fetch_static_map_image", fake_fetch_static_map)

    pdf_bytes = asyncio.run(route_export.generate_route_overview_pdf(payload))
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 500