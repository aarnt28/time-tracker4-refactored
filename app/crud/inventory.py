from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from ..models.inventory import InventoryEvent
from ..models.hardware import Hardware


def list_inventory_events(db: Session, limit: int = 100, offset: int = 0) -> list[InventoryEvent]:
    stmt = (
        select(InventoryEvent)
        .order_by(desc(InventoryEvent.created_at), desc(InventoryEvent.id))
        .limit(limit)
        .offset(offset)
    )
    return db.execute(stmt).scalars().all()


def get_inventory_summary(db: Session) -> list[dict[str, object]]:
    stmt = (
        select(
            InventoryEvent.hardware_id,
            Hardware.barcode,
            Hardware.description,
            func.coalesce(func.sum(InventoryEvent.change), 0).label("quantity"),
            func.max(InventoryEvent.created_at).label("last_activity"),
        )
        .join(Hardware, Hardware.id == InventoryEvent.hardware_id)
        .group_by(InventoryEvent.hardware_id, Hardware.barcode, Hardware.description)
        .order_by(Hardware.description)
    )
    rows = db.execute(stmt).all()
    return [
        {
            "hardware_id": row.hardware_id,
            "barcode": row.barcode,
            "description": row.description,
            "quantity": int(row.quantity or 0),
            "last_activity": row.last_activity,
        }
        for row in rows
    ]


def record_inventory_event(
    db: Session,
    *,
    hardware_id: int,
    change: int,
    source: str = "manual",
    note: str | None = None,
    ticket_id: int | None = None,
    counterparty_name: str | None = None,
    counterparty_type: str | None = None,
    actual_cost: float | None = None,
) -> InventoryEvent:
    if not change:
        raise ValueError("change must be non-zero")
    name = (counterparty_name or "").strip() or None
    ctype = (counterparty_type or "").strip() or None
    cost_total = float(actual_cost) if actual_cost is not None else None
    unit_cost = None
    if cost_total is not None:
        quantity = abs(change)
        if quantity:
            unit_cost = cost_total / quantity
    event = InventoryEvent(
        hardware_id=hardware_id,
        change=change,
        source=source,
        note=note,
        ticket_id=ticket_id,
        created_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
        counterparty_name=name,
        counterparty_type=ctype,
        actual_cost=cost_total,
        unit_cost=unit_cost,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def get_event_by_ticket(db: Session, ticket_id: int) -> InventoryEvent | None:
    stmt = select(InventoryEvent).where(InventoryEvent.ticket_id == ticket_id)
    return db.execute(stmt).scalars().first()


def delete_event(db: Session, event: InventoryEvent) -> None:
    db.delete(event)
    db.commit()


def delete_ticket_event(db: Session, ticket_id: int) -> None:
    existing = get_event_by_ticket(db, ticket_id)
    if existing:
        delete_event(db, existing)


def ensure_ticket_usage_event(
    db: Session,
    *,
    ticket_id: int,
    hardware_id: int,
    quantity: int = 1,
    note: str | None = None,
) -> InventoryEvent:
    """Create or update the inventory event associated with a hardware ticket.

    ``quantity`` represents how many units were consumed by the ticket. The
    stored change is always negative to reflect usage.
    """

    change = -abs(quantity)
    existing = get_event_by_ticket(db, ticket_id)
    if existing:
        existing.hardware_id = hardware_id
        existing.change = change
        existing.source = "ticket"
        existing.note = note
        existing.counterparty_name = None
        existing.counterparty_type = None
        existing.actual_cost = None
        existing.unit_cost = None
        db.commit()
        db.refresh(existing)
        return existing

    return record_inventory_event(
        db,
        hardware_id=hardware_id,
        change=change,
        source="ticket",
        note=note,
        ticket_id=ticket_id,
        counterparty_name=None,
        counterparty_type=None,
        actual_cost=None,
    )
