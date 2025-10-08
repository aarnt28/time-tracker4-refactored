from __future__ import annotations
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..crud.tickets import list_tickets, get_ticket, update_ticket, delete_ticket
from ..crud.hardware import list_hardware, get_hardware, update_hardware, delete_hardware
from ..crud.inventory import get_inventory_summary, list_inventory_events, record_inventory_event
from ..core.config import settings
from ..services.clientsync import load_client_table
from ..models.hardware import Hardware
from ..models.ticket import Ticket
from ..deps.ui_auth import require_ui_session
from ..core.jinja import get_templates  # <<< use centralized templates with filters

templates = get_templates()

router = APIRouter(dependencies=[Depends(require_ui_session)])

def _login_redirect(request: Request):
    return RedirectResponse(url=f"/login?next={request.url.path}", status_code=302)

@router.get("/", response_class=HTMLResponse)
def index_page(request: Request, db: Session = Depends(get_db)):
    try:
        ct = load_client_table()
    except Exception:
        ct = {}

    tickets_total = db.scalar(select(func.count()).select_from(Ticket)) or 0
    tickets_open = db.scalar(
        select(func.count()).select_from(Ticket).where(Ticket.completed == 0)
    ) or 0
    completion = int(round(((tickets_total - tickets_open) / tickets_total) * 100)) if tickets_total else 0
    hardware_total = db.scalar(select(func.count()).select_from(Hardware)) or 0

    recent = list_tickets(db, limit=50)
    spotlight = [t for t in recent if not t.completed][:5]
    recent_tickets = recent[:5]

    stats = {
        "tickets_total": tickets_total,
        "tickets_open": tickets_open,
        "tickets_completion": completion,
        "hardware_total": hardware_total,
        "clients_total": len(ct),
    }

    context = {
        "request": request,
        "client_table": ct,
        "stats": stats,
        "spotlight": spotlight,
        "recent_tickets": recent_tickets,
    }
    return templates.TemplateResponse("index.html", context)

@router.get("/tickets", response_class=HTMLResponse)
def tickets_page(request: Request, db: Session = Depends(get_db)):
    rows = list_tickets(db, limit=200)
    return templates.TemplateResponse("tickets.html", {"request": request, "rows": rows})

@router.get("/clients", response_class=HTMLResponse)
def clients_page(request: Request):
    return templates.TemplateResponse("clients.html", {"request": request})

@router.get("/hardware", response_class=HTMLResponse)
def hardware_page(request: Request, db: Session = Depends(get_db)):
    rows = list_hardware(db, limit=200)
    return templates.TemplateResponse("hardware.html", {"request": request, "rows": rows})


@router.get("/inventory", response_class=HTMLResponse)
def inventory_page(request: Request, db: Session = Depends(get_db)):
    summary = get_inventory_summary(db)
    events = list_inventory_events(db, limit=200)
    hardware_options = list_hardware(db, limit=500)
    context = {
        "request": request,
        "summary": summary,
        "events": events,
        "hardware_options": hardware_options,
    }
    return templates.TemplateResponse("inventory.html", context)

@router.get("/ui/hardware_table", response_class=HTMLResponse)
def hardware_table_partial(request: Request, db: Session = Depends(get_db)):
    rows = list_hardware(db, limit=200)
    return templates.TemplateResponse("_hardware_rows.html", {"request": request, "rows": rows})

@router.get("/ui/ticket_table", response_class=HTMLResponse)
def ticket_table_partial(request: Request, db: Session = Depends(get_db)):
    rows = list_tickets(db, limit=200)
    return templates.TemplateResponse("_rows.html", {"request": request, "rows": rows})

@router.post("/ui/tickets/{entry_id}/toggle-completed", response_class=HTMLResponse)
@router.post("/ui/tickets/{entry_id}/toggle", response_class=HTMLResponse)  # compat
def ui_toggle_ticket(entry_id: int, db: Session = Depends(get_db)):
    r = get_ticket(db, entry_id)
    if not r:
        raise HTTPException(404, "Not found")
    r.completed = 0 if r.completed else 1
    update_ticket(db, r, {"completed": r.completed})
    updated = [r]
    return templates.TemplateResponse("_rows.html", {"request": {}, "rows": updated})

@router.post("/ui/tickets/{entry_id}/delete", response_class=HTMLResponse)
def ui_delete_ticket(entry_id: int, db: Session = Depends(get_db)):
    r = get_ticket(db, entry_id)
    if not r:
        raise HTTPException(404, "Not found")
    delete_ticket(db, r)
    return HTMLResponse("", status_code=204)

@router.post("/ui/hardware/{item_id}/delete", response_class=HTMLResponse)
def ui_delete_hardware(item_id: int, db: Session = Depends(get_db)):
    r = get_hardware(db, item_id)
    if not r:
        raise HTTPException(404, "Not found")
    delete_hardware(db, r)
    return HTMLResponse("", status_code=204)

@router.post("/ui/hardware/{item_id}/set-invoice", response_class=HTMLResponse)
def ui_set_invoice_hardware(item_id: int, invoice_number: str = Form(""), db: Session = Depends(get_db)):
    r = get_hardware(db, item_id)
    if not r:
        raise HTTPException(404, "Not found")
    r.invoice_number = (invoice_number or "").strip() or None
    update_hardware(db, r, {"invoice_number": r.invoice_number})
    return templates.TemplateResponse("_hardware_rows.html", {"request": {}, "rows": [r]})


@router.post("/inventory/adjust", response_class=HTMLResponse)
def inventory_adjust(
    hardware_id: int = Form(...),
    action: str = Form("receive"),
    quantity: int = Form(1),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        qty = int(quantity)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Quantity must be a positive integer") from exc
    if qty <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be a positive integer")

    action_value = (action or "").lower()
    if action_value not in {"receive", "use"}:
        raise HTTPException(status_code=400, detail="Invalid inventory action")

    hardware = get_hardware(db, hardware_id)
    if not hardware:
        raise HTTPException(status_code=404, detail="Hardware not found")

    change = qty if action_value == "receive" else -qty
    record_inventory_event(
        db,
        hardware_id=hardware.id,
        change=change,
        source=f"ui:{action_value}",
        note=note.strip() or None,
    )
    return RedirectResponse(url="/inventory", status_code=303)
