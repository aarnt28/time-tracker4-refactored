# app/crud/hardware.py
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session
from sqlalchemy import select, desc

from ..models.hardware import Hardware


def list_hardware(db: Session, limit: int = 100, offset: int = 0):
    """
    Return hardware items ordered by created_at (desc) with pagination.
    """
    stmt = (
        select(Hardware)
        .order_by(desc(Hardware.created_at))
        .limit(limit)
        .offset(offset)
    )
    return db.execute(stmt).scalars().all()


def get_hardware(db: Session, item_id: int) -> Hardware | None:
    """
    Fetch a single hardware record by primary key.
    """
    return db.get(Hardware, item_id)


def create_hardware(db: Session, payload: dict) -> Hardware:
    """
    Create and persist a hardware record from a payload dict.
    """
    data = payload.copy()
    barcode = (data.get("barcode") or "").strip()
    if not barcode:
        raise ValueError("barcode is required for hardware items")
    data["barcode"] = barcode

    if "description" in data and isinstance(data["description"], str):
        data["description"] = data["description"].strip()

    for key in ("acquisition_cost", "sales_price"):
        if key in data:
            val = (data[key] or "")
            data[key] = val.strip() or None

    data.setdefault(
        "created_at",
        datetime.utcnow().isoformat(timespec="seconds") + "Z",
    )

    obj = Hardware(**data)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_hardware(db: Session, item: Hardware, payload: dict) -> Hardware:
    """
    Update an existing hardware record in-place from a payload dict.
    Unknown keys are ignored so older clients with stale fields do not break.
    """
    for k, v in payload.items():
        if not hasattr(item, k):
            continue
        if isinstance(v, str):
            v = v.strip()
            if k in ("acquisition_cost", "sales_price") and v == "":
                v = None
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


def delete_hardware(db: Session, item: Hardware) -> None:
    """
    Delete the given hardware record.
    """
    db.delete(item)
    db.commit()