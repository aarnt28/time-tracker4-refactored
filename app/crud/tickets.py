from __future__ import annotations
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from ..models.ticket import Ticket
from ..models.hardware import Hardware
from .inventory import ensure_ticket_usage_event, delete_ticket_event
from ..services.timecalc import compute_minutes, round_minutes
from ..services.clientsync import resolve_client_name
from ..core.config import settings
from ..core.barcodes import barcode_aliases, normalize_barcode


def list_tickets(db: Session, limit: int = 100, offset: int = 0):
    return db.execute(
        select(Ticket).order_by(desc(Ticket.created_at)).limit(limit).offset(offset)
    ).scalars().all()


def list_active_tickets(db: Session, client_key: str | None = None, limit: int = 100, offset: int = 0):
    stmt = select(Ticket).where(Ticket.end_iso.is_(None))
    if client_key:
        stmt = stmt.where(Ticket.client_key == client_key)
    stmt = stmt.order_by(desc(Ticket.created_at)).limit(limit).offset(offset)
    return db.execute(stmt).scalars().all()

def get_ticket(db: Session, entry_id: int) -> Ticket | None:
    return db.get(Ticket, entry_id)


def _resolve_hardware(db: Session, payload: dict, fallback_id: int | None) -> Hardware | None:
    hw_id = payload.get("hardware_id", fallback_id)
    barcode = payload.get("hardware_barcode")

    for candidate in barcode_aliases(barcode):
        stmt = select(Hardware).where(Hardware.barcode == candidate)
        hw = db.execute(stmt).scalars().first()
        if hw:
            return hw

    if hw_id:
        return db.get(Hardware, hw_id)

    return None


def _apply_time_math(t: Ticket, payload: dict) -> None:
    tz = getattr(settings, "TZ", "America/Chicago")
    start_iso = payload.get("start_iso", t.start_iso)
    end_iso = payload.get("end_iso", t.end_iso)
    base_minutes = compute_minutes(start_iso, end_iso, tz) if start_iso and end_iso else 0
    minutes, rmin, rhours = round_minutes(base_minutes)
    t.elapsed_minutes = base_minutes
    t.minutes = minutes
    t.rounded_minutes = rmin
    t.rounded_hours = rhours


def _apply_hardware_link(db: Session, t: Ticket, payload: dict) -> None:
    """If entry_type is hardware, sync linked hardware details via id or barcode."""
    if payload.get("entry_type", t.entry_type) != "hardware":
        t.hardware_id = None
        t.hardware_description = None
        t.hardware_sales_price = None
        t.hardware_barcode = None
        t.hardware_quantity = None
        return

    hw = _resolve_hardware(db, payload, t.hardware_id)
    desc_override = payload.get("hardware_description")
    if isinstance(desc_override, str):
        desc_override = desc_override.strip() or None
    price_override = payload.get("hardware_sales_price")
    if isinstance(price_override, str):
        price_override = price_override.strip() or None
    barcode_raw = payload.get("hardware_barcode")
    barcode_override = normalize_barcode(barcode_raw) or ((barcode_raw or "").strip() or None)

    if hw:
        t.hardware_id = hw.id
        t.hardware_barcode = hw.barcode
        t.hardware_description = desc_override if desc_override is not None else hw.description
        t.hardware_sales_price = price_override if price_override is not None else hw.sales_price
    else:
        t.hardware_id = None
        t.hardware_barcode = barcode_override
        t.hardware_description = desc_override
        t.hardware_sales_price = price_override

    qty_value = payload.get("hardware_quantity")
    if qty_value is None:
        qty_value = t.hardware_quantity if t.hardware_quantity else 1
    try:
        qty_int = int(qty_value)
    except (TypeError, ValueError) as exc:
        raise ValueError("hardware_quantity must be a positive integer") from exc
    if qty_int <= 0:
        raise ValueError("hardware_quantity must be a positive integer")
    t.hardware_quantity = qty_int


def _apply_client_link(t: Ticket, payload: dict) -> None:
    client_key = payload.get("client_key", t.client_key)
    if not client_key:
        raise ValueError("client_key is required")
    client_name = payload.get("client") or resolve_client_name(client_key)
    if not client_name:
        raise ValueError(f"Unknown client_key '{client_key}'")
    t.client_key = client_key
    t.client = client_name


def create_entry(db: Session, payload: dict) -> Ticket:
    if "client_key" not in payload or not payload["client_key"]:
        raise ValueError("client_key is required")
    t = Ticket(
        client="",  # populated below
        client_key=payload["client_key"],
        start_iso=payload["start_iso"],
        end_iso=payload.get("end_iso"),
        note=payload.get("note"),
        completed=0,
        sent=payload.get("sent", 0) or 0,
        invoice_number=payload.get("invoice_number"),
        created_at=payload.get("created_at") or datetime.utcnow().isoformat(timespec="seconds") + "Z",
        entry_type=payload.get("entry_type", "time"),
        hardware_id=payload.get("hardware_id"),
    )
    _apply_client_link(t, payload)
    _apply_time_math(t, payload)
    _apply_hardware_link(db, t, payload)
    db.add(t)
    db.commit()
    db.refresh(t)
    if t.entry_type == "hardware" and t.hardware_id:
        ensure_ticket_usage_event(
            db,
            ticket_id=t.id,
            hardware_id=t.hardware_id,
            quantity=t.hardware_quantity or 1,
            note=t.note,
        )
    return t


def update_ticket(db: Session, t: Ticket, payload: dict) -> Ticket:
    if "client_key" in payload or "client" in payload:
        _apply_client_link(t, payload)
    for k, v in payload.items():
        if k in {"client", "client_key"}:
            continue
        if not hasattr(t, k):
            continue
        setattr(t, k, v)
    if any(k in payload for k in ("start_iso", "end_iso")):
        _apply_time_math(t, payload)
    if any(k in payload for k in ("entry_type", "hardware_id", "hardware_barcode", "hardware_quantity")):
        _apply_hardware_link(db, t, payload)
    db.commit()
    db.refresh(t)
    if t.entry_type == "hardware" and t.hardware_id:
        ensure_ticket_usage_event(
            db,
            ticket_id=t.id,
            hardware_id=t.hardware_id,
            quantity=t.hardware_quantity or 1,
            note=t.note,
        )
    else:
        delete_ticket_event(db, t.id)
    return t


def delete_ticket(db: Session, ticket: Ticket) -> None:
    delete_ticket_event(db, ticket.id)
    db.delete(ticket)
    db.commit()
