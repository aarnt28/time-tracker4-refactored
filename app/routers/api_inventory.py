from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..crud.inventory import get_inventory_summary, list_inventory_events, record_inventory_event
from ..db.session import get_db
from ..deps.auth import require_ui_or_token
from ..models.hardware import Hardware
from ..schemas.inventory import (
    InventoryAdjustment,
    InventoryEventOut,
    InventorySummaryItem,
)

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"], dependencies=[Depends(require_ui_or_token)])


def _lookup_hardware(db: Session, hardware_id: int | None, barcode: str | None) -> Hardware:
    if hardware_id:
        hw = db.get(Hardware, hardware_id)
        if hw:
            return hw
    if barcode:
        stmt = select(Hardware).where(Hardware.barcode == barcode.strip())
        hw = db.execute(stmt).scalars().first()
        if hw:
            return hw
    raise HTTPException(status_code=404, detail="Hardware item not found")


@router.get("/summary", response_model=list[InventorySummaryItem])
def api_inventory_summary(db: Session = Depends(get_db)):
    return get_inventory_summary(db)


@router.get("/events", response_model=list[InventoryEventOut])
def api_inventory_events(limit: int = 100, offset: int = 0, db: Session = Depends(get_db)):
    return list_inventory_events(db, limit=limit, offset=offset)


@router.post("/receive", response_model=InventoryEventOut, status_code=201)
def api_receive_inventory(payload: InventoryAdjustment, db: Session = Depends(get_db)):
    hw = _lookup_hardware(db, payload.hardware_id, payload.barcode)
    return record_inventory_event(
        db,
        hardware_id=hw.id,
        change=payload.quantity,
        source="api:receive",
        note=payload.note,
    )


@router.post("/use", response_model=InventoryEventOut, status_code=201)
def api_use_inventory(payload: InventoryAdjustment, db: Session = Depends(get_db)):
    hw = _lookup_hardware(db, payload.hardware_id, payload.barcode)
    return record_inventory_event(
        db,
        hardware_id=hw.id,
        change=-payload.quantity,
        source="api:use",
        note=payload.note,
    )
