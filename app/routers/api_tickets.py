from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..schemas.ticket import TicketCreate, TicketUpdate, TicketOut
from ..crud.tickets import list_entries, get_ticket, create_ticket, update_ticket, delete_ticket
from ..core.config import settings

router = APIRouter(prefix="/api/v1/entries", tags=["entries"])

def require_token(x_api_key: str = Header(default="")):
    if settings.API_TOKEN and x_api_key != settings.API_TOKEN:
        raise HTTPException(401, "Invalid token")
    return True

@router.get("", response_model=list[TicketOut], dependencies=[Depends(require_token)])
def api_list(limit: int = 100, offset: int = 0, db: Session = Depends(get_db)):
    return list_entries(db, limit=limit, offset=offset)

@router.get("/{ticket_id}", response_model=TicketOut, dependencies=[Depends(require_token)])
def api_get(ticket_id: int, db: Session = Depends(get_db)):
    r = get_ticket(db, ticket_id)
    if not r: raise HTTPException(404, "Not found")
    return r

@router.post("", response_model=TicketOut, dependencies=[Depends(require_token)])
def api_create(payload: TicketCreate, db: Session = Depends(get_db)):
    return create_ticket(db, payload.model_dump())

@router.patch("/{ticket_id}", response_model=TicketOut, dependencies=[Depends(require_token)])
def api_update(ticket_id: int, payload: TicketUpdate, db: Session = Depends(get_db)):
    r = get_ticket(db, ticket_id)
    if not r: raise HTTPException(404, "Not found")
    return update_ticket(db, r, {k:v for k,v in payload.model_dump().items() if v is not None})

@router.delete("/{ticket_id}", dependencies=[Depends(require_token)])
def api_delete(ticket_id: int, db: Session = Depends(get_db)):
    r = get_ticket(db, ticket_id)
    if not r: raise HTTPException(404, "Not found")
    delete_ticket(db, r)
    return {"status": "deleted"}
