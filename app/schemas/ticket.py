from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional

class TicketBase(BaseModel):
    client: str
    client_key: str
    note: Optional[str] = None

class TicketCreate(TicketBase):
    start_iso: str
    end_iso: Optional[str] = None
    invoice_number: Optional[str] = None

class TicketUpdate(BaseModel):
    client: Optional[str] = None
    client_key: Optional[str] = None
    note: Optional[str] = None
    end_iso: Optional[str] = None
    invoice_number: Optional[str] = None
    completed: Optional[int] = None

class TicketOut(BaseModel):
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
    invoice_number: Optional[str]
    created_at: str
    minutes: int

    class Config:
        from_attributes = True
