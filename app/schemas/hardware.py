"""Beginner-friendly overview for this module.

WHAT: Handles the logic defined in "app/schemas/hardware.py" for the Time Tracker app.
WHEN: Invoked when its functions or classes are imported and called.
WHY: Provides supporting behaviour so the service runs smoothly.
HOW: Read the inline comments and docstrings below for the step-by-step flow.

File: app/schemas/hardware.py
"""


from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional


class HardwareBase(BaseModel):
    barcode: str
    description: str
    acquisition_cost: Optional[str] = None
    sales_price: Optional[str] = None


class HardwareCreate(HardwareBase):
    pass


class HardwareUpdate(BaseModel):
    barcode: Optional[str] = None
    description: Optional[str] = None
    acquisition_cost: Optional[str] = None
    sales_price: Optional[str] = None


class HardwareOut(BaseModel):
    id: int
    barcode: str
    description: str
    acquisition_cost: Optional[str]
    sales_price: Optional[str]
    created_at: str
    common_vendors: list[str] = Field(default_factory=list)
    average_unit_cost: Optional[float] = None

    class Config:
        from_attributes = True