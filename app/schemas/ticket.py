"""Beginner-friendly overview for this module.

WHAT: Handles the logic defined in "app/schemas/ticket.py" for the Time Tracker app.
WHEN: Invoked when its functions or classes are imported and called.
WHY: Provides supporting behaviour so the service runs smoothly.
HOW: Read the inline comments and docstrings below for the step-by-step flow.

File: app/schemas/ticket.py
"""


from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional

from ..core.ticket_types import ENTRY_TYPE_CHOICES

ENTRY_TYPE_PATTERN = f"^({'|'.join(ENTRY_TYPE_CHOICES)})$"


class EntryBase(BaseModel):
    client: Optional[str] = None
    client_key: str
    note: Optional[str] = None
    entry_type: str = Field(default="time", pattern=ENTRY_TYPE_PATTERN)
    hardware_id: Optional[int] = None  # when entry_type == 'hardware'
    hardware_barcode: Optional[str] = None
    hardware_quantity: Optional[int] = Field(default=None, ge=1)
    hardware_description: Optional[str] = None
    hardware_sales_price: Optional[str] = None
    flat_rate_amount: Optional[str] = None
    flat_rate_quantity: Optional[int] = Field(default=None, ge=1)
    project_id: Optional[int] = None


class EntryCreate(EntryBase):
    start_iso: str
    end_iso: Optional[str] = None
    invoice_number: Optional[str] = None
    sent: Optional[int] = 0
    invoiced_total: Optional[str] = None
    project_posted: Optional[bool] = None


class EntryUpdate(BaseModel):
    client: Optional[str] = None
    client_key: Optional[str] = None
    start_iso: Optional[str] = None
    end_iso: Optional[str] = None
    note: Optional[str] = None
    completed: Optional[int] = None
    sent: Optional[int] = None
    invoice_number: Optional[str] = None
    invoiced_total: Optional[str] = None
    entry_type: Optional[str] = Field(default=None, pattern=ENTRY_TYPE_PATTERN)
    hardware_id: Optional[int] = None
    hardware_barcode: Optional[str] = None
    hardware_quantity: Optional[int] = Field(default=None, ge=1)
    hardware_description: Optional[str] = None
    hardware_sales_price: Optional[str] = None
    flat_rate_amount: Optional[str] = None
    flat_rate_quantity: Optional[int] = Field(default=None, ge=1)
    project_id: Optional[int] = None
    project_posted: Optional[bool] = None


class TicketAttachment(BaseModel):
    id: str
    filename: str
    content_type: Optional[str] = None
    size: Optional[int] = None
    uploaded_at: str
    url: Optional[str] = None

    class Config:
        extra = "ignore"


class EntryOut(BaseModel):
    id: int
    client: str
    client_key: str
    start_iso: str
    end_iso: Optional[str]
    elapsed_minutes: int
    rounded_minutes: int
    rounded_hours: str
    note: Optional[str]
    completed: int
    sent: int
    invoice_number: Optional[str]
    invoiced_total: Optional[str]
    created_at: str
    minutes: int
    entry_type: str
    hardware_id: Optional[int] = None
    hardware_barcode: Optional[str] = None
    hardware_description: Optional[str] = None
    hardware_sales_price: Optional[str] = None
    hardware_quantity: Optional[int] = None
    flat_rate_amount: Optional[str] = None
    flat_rate_quantity: Optional[int] = None
    calculated_value: Optional[str] = None
    attachments: list[TicketAttachment] = Field(default_factory=list)
    project_id: Optional[int] = None
    project_posted: int

    class Config:
        from_attributes = True
