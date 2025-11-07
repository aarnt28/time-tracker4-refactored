"""Beginner-friendly overview for this module.

WHAT: Handles the logic defined in "app/schemas/route.py" for the Time Tracker app.
WHEN: Invoked when its functions or classes are imported and called.
WHY: Provides supporting behaviour so the service runs smoothly.
HOW: Read the inline comments and docstrings below for the step-by-step flow.

File: app/schemas/route.py
"""


from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class LatLng(BaseModel):
    """Latitude/longitude pair used for plotting markers on maps."""

    lat: float = Field(..., description="Latitude in decimal degrees")
    lng: float = Field(..., description="Longitude in decimal degrees")

    @field_validator("lat")
    def _validate_lat(cls, value: float) -> float:
        if not -90 <= value <= 90:
            raise ValueError("lat must be between -90 and 90 degrees")
        return value

    @field_validator("lng")
    def _validate_lng(cls, value: float) -> float:
        if not -180 <= value <= 180:
            raise ValueError("lng must be between -180 and 180 degrees")
        return value


class RouteStop(BaseModel):
    """Stop metadata exposed in the PDF export."""

    order: int = Field(..., ge=1, description="1-indexed order of the stop")
    name: str = Field(..., description="Display label for the stop")
    address: str = Field(..., description="Full mailing address for the stop")

    @field_validator("name", "address")
    def _strip_strings(cls, value: str) -> str:
        return value.strip()


class RouteLeg(BaseModel):
    """Driving segment returned from Google Maps."""

    start_address: str = Field(..., description="Leg origin address")
    end_address: str = Field(..., description="Leg destination address")
    distance_text: Optional[str] = Field(None, description="Formatted distance")
    distance_meters: Optional[float] = Field(
        None, ge=0, description="Distance in meters"
    )
    duration_text: Optional[str] = Field(None, description="Formatted travel time")
    duration_seconds: Optional[float] = Field(
        None, ge=0, description="Duration in seconds"
    )
    start_location: Optional[LatLng] = Field(
        None, description="Coordinates for the leg origin"
    )
    end_location: Optional[LatLng] = Field(
        None, description="Coordinates for the leg destination"
    )

    @field_validator("start_address", "end_address", "distance_text", "duration_text")
    def _clean_text(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value.strip()


class RouteExportRequest(BaseModel):
    """Payload posted by the UI when exporting a route overview."""

    origin_name: str = Field(..., description="Human-friendly label for the origin")
    origin_address: str = Field(..., description="Service origin street address")
    origin_display: Optional[str] = Field(
        None, description="Origin text shown in the UI"
    )
    stops: List[RouteStop] = Field(default_factory=list)
    legs: List[RouteLeg] = Field(default_factory=list)
    overview_polyline: Optional[str] = Field(
        None, description="Encoded polyline returned by Google Maps"
    )
    total_distance_meters: Optional[float] = Field(
        None, ge=0, description="Aggregate distance in meters"
    )
    total_duration_seconds: Optional[float] = Field(
        None, ge=0, description="Aggregate duration in seconds"
    )

    @field_validator("origin_name", "origin_address", "origin_display", mode="before")
    def _strip_origin_fields(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return str(value).strip()

    @field_validator("stops", mode="after")
    def _validate_stops(cls, value: List[RouteStop]) -> List[RouteStop]:
        return sorted(value, key=lambda stop: stop.order)

    @field_validator("legs", mode="after")
    def _validate_legs(cls, value: List[RouteLeg]) -> List[RouteLeg]:
        if not value:
            raise ValueError("At least one leg is required to export a route")
        return value