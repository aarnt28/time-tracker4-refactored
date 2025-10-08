from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, model_validator


class InventoryAdjustment(BaseModel):
    hardware_id: Optional[int] = None
    barcode: Optional[str] = None
    quantity: int = Field(gt=0)
    note: Optional[str] = None

    @model_validator(mode="after")
    def validate_target(self) -> "InventoryAdjustment":
        if not self.hardware_id and not (self.barcode and self.barcode.strip()):
            raise ValueError("hardware_id or barcode is required")
        return self


class InventoryEventOut(BaseModel):
    id: int
    hardware_id: int
    change: int
    source: str
    note: Optional[str]
    created_at: str
    ticket_id: Optional[int]
    hardware_barcode: Optional[str] = None
    hardware_description: Optional[str] = None

    class Config:
        from_attributes = True


class InventorySummaryItem(BaseModel):
    hardware_id: int
    barcode: str
    description: str
    quantity: int
    last_activity: Optional[str]
