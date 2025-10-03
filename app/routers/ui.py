from __future__ import annotations
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..db.session import get_db
from ..crud.tickets import list_entries, get_ticket, update_ticket, delete_ticket
from ..crud.hardware import list_hardware, get_hardware, update_hardware, delete_hardware
from ..core.config import settings
from ..services.timecalc import parse_iso

router = APIRouter()
templates = Jinja2Templates(directory=str(settings.BASE_DIR / "app" / "templates"))

# ---- Register legacy Jinja filters expected by your templates ----
def _register_jinja_filters() -> None:
    def fmt_dt(s: str | None) -> str:
        """Format ISO timestamp into 'M/D/YY H:MM AM/PM' in local TZ.
        Works on Linux and Windows (strftime width flags differ)."""
        if not s:
            return "—"
        try:
            dt = parse_iso(s, settings.TZ)
            try:
                return dt.strftime("%-m/%-d/%y %I:%M %p")   # POSIX
            except ValueError:
                return dt.strftime("%#m/%#d/%y %#I:%M %p")  # Windows
        except Exception:
            return "—"

    def timeonly(s: str | None) -> str:
        """Format ISO timestamp into 'H:MM AM/PM' in local TZ."""
        if not s:
            return "—"
        try:
            dt = parse_iso(s, settings.TZ)
            try:
                return dt.strftime("%I:%M %p")             # POSIX
            except ValueError:
                return dt.strftime("%#I:%M %p")            # Windows
        except Exception:
            return "—"

    # simple numeric formatter used in _row.html
    def hours2d(s: str | float | int | None) -> str:
        try:
            return f"{float(s) if s is not None else 0.0:.2f}"
        except Exception:
            return "0.00"

    templates.env.filters["fmt_dt"] = fmt_dt
    templates.env.filters["timeonly"] = timeonly
    templates.env.filters["hours2d"] = hours2d

_register_jinja_filters()
# ------------------------------------------------------------------

@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    rows = list_entries(db, limit=100)
    return templates.TemplateResponse("index.html", {"request": request, "rows": rows})

@router.get("/hardware", response_class=HTMLResponse)
def hardware_page(request: Request, db: Session = Depends(get_db)):
    rows = list_hardware(db, limit=200)
    return templates.TemplateResponse("hardware.html", {"request": request, "rows": rows})

# ---- Minimal UI actions to match your forms/partials ----
@router.post("/ui/entries/{ticket_id}/toggle", response_class=HTMLResponse)
def ui_toggle(ticket_id: int, db: Session = Depends(get_db)):
    r = get_ticket(db, ticket_id)
    if not r:
        raise HTTPException(404, "Not found")
    r.completed = 0 if r.completed else 1
    update_ticket(db, r, {"completed": r.completed})
    # Partial for a single updated row
    return templates.TemplateResponse("_rows.html", {"request": {}, "rows": [r]})

@router.post("/ui/entries/{ticket_id}/delete", response_class=HTMLResponse)
def ui_delete(ticket_id: int, db: Session = Depends(get_db)):
    r = get_ticket(db, ticket_id)
    if not r:
        raise HTTPException(404, "Not found")
    delete_ticket(db, r)
    return HTMLResponse("", status_code=204)

@router.post("/ui/hardware/{item_id}/toggle", response_class=HTMLResponse)
def ui_hw_toggle(item_id: int, db: Session = Depends(get_db)):
    r = get_hardware(db, item_id)
    if not r:
        raise HTTPException(404, "Not found")
    r.completed = 0 if r.completed else 1
    update_hardware(db, r, {"completed": r.completed})
    return templates.TemplateResponse("_hardware_rows.html", {"request": {}, "rows": [r]})

@router.post("/ui/hardware/{item_id}/delete", response_class=HTMLResponse)
def ui_hw_delete(item_id: int, db: Session = Depends(get_db)):
    r = get_hardware(db, item_id)
    if not r:
        raise HTTPException(404, "Not found")
    delete_hardware(db, r)
    return HTMLResponse("", status_code=204)

@router.post("/ui/hardware/{item_id}/set-invoice", response_class=HTMLResponse)
def ui_hw_set_invoice(item_id: int, invoice_number: str = Form(""), db: Session = Depends(get_db)):
    r = get_hardware(db, item_id)
    if not r:
        raise HTTPException(404, "Not found")
    r.invoice_number = (invoice_number or "").strip() or None
    update_hardware(db, r, {"invoice_number": r.invoice_number})
    return templates.TemplateResponse("_hardware_rows.html", {"request": {}, "rows": [r]})
