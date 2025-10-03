from __future__ import annotations
from sqlalchemy.orm import Session
from sqlalchemy import select, desc
from ..models.ticket import Ticket
from ..services.timecalc import compute_minutes, round_minutes
from ..core.config import settings

def list_entries(db: Session, limit: int = 100, offset: int = 0):
    return db.execute(select(Ticket).order_by(desc(Ticket.created_at)).limit(limit).offset(offset)).scalars().all()

def get_ticket(db: Session, ticket_id: int) -> Ticket | None:
    return db.get(Ticket, ticket_id)

def create_ticket(db: Session, payload: dict) -> Ticket:
    start_iso = payload.get("start_iso")
    end_iso = payload.get("end_iso")
    base_minutes = compute_minutes(start_iso, end_iso, settings.TZ) if end_iso else 0
    minutes, rmin, rhours = round_minutes(base_minutes)
    obj = Ticket(
        client=payload["client"],
        client_key=payload["client_key"],
        start_iso=start_iso,
        end_iso=end_iso,
        elapsed_minutes=base_minutes,
        rounded_minutes=rmin,
        rounded_hours=rhours,
        note=payload.get("note"),
        completed=payload.get("completed", 0),
        invoice_number=payload.get("invoice_number"),
        created_at=payload.get("created_at") or start_iso,
        minutes=minutes,
    )
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

def update_ticket(db: Session, ticket: Ticket, payload: dict) -> Ticket:
    for k, v in payload.items():
        setattr(ticket, k, v)
    # recompute times if end_iso or start changed
    base_minutes = 0
    if ticket.end_iso and ticket.start_iso:
        base_minutes = compute_minutes(ticket.start_iso, ticket.end_iso, settings.TZ)
    minutes, rmin, rhours = round_minutes(base_minutes)
    ticket.elapsed_minutes = base_minutes
    ticket.rounded_minutes = rmin
    ticket.rounded_hours = rhours
    ticket.minutes = minutes
    db.commit(); db.refresh(ticket)
    return ticket

def delete_ticket(db: Session, ticket: Ticket) -> None:
    db.delete(ticket); db.commit()
