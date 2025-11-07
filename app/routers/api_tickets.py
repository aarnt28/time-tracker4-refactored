"""Beginner-friendly overview for this module.

WHAT: Handles the logic defined in "app/routers/api_tickets.py" for the Time Tracker app.
WHEN: Invoked when its functions or classes are imported and called.
WHY: Provides supporting behaviour so the service runs smoothly.
HOW: Read the inline comments and docstrings below for the step-by-step flow.

File: app/routers/api_tickets.py
"""


from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ..db.session import get_db
from ..schemas.ticket import EntryCreate, EntryUpdate, EntryOut, TicketAttachment
from ..crud.tickets import (
    list_tickets,
    list_active_tickets,
    get_ticket,
    create_entry,
    update_ticket,
    delete_ticket,
    add_ticket_attachment,
    list_ticket_attachments,
    get_ticket_attachment,
)
from ..deps.auth import require_ui_or_token

ALLOWED_ATTACHMENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/gif",
    "image/webp",
}


router = APIRouter(prefix="/api/v1/tickets", tags=["tickets"])


def _attachment_to_schema(ticket_id: int, record: dict[str, object]) -> TicketAttachment:
    payload = dict(record)
    attachment_id = payload.get("id")
    if attachment_id is not None:
        payload["id"] = str(attachment_id)
        payload["url"] = f"/api/v1/tickets/{ticket_id}/attachments/{attachment_id}"
    else:
        payload["id"] = ""
        payload["url"] = f"/api/v1/tickets/{ticket_id}/attachments/{attachment_id}"
    return TicketAttachment.model_validate(payload)


def _serialize_ticket(ticket) -> EntryOut:
    payload = EntryOut.model_validate(ticket, from_attributes=True)
    attachment_records = list_ticket_attachments(ticket)
    payload.attachments = [
        _attachment_to_schema(ticket.id, record) for record in attachment_records
    ]
    return payload

@router.get("/active", response_model=list[EntryOut], dependencies=[Depends(require_ui_or_token)])
def api_list_active(client_key: str | None = Query(default=None), db: Session = Depends(get_db)):
    records = list_active_tickets(db, client_key=client_key)
    return [_serialize_ticket(record) for record in records]


@router.get("", response_model=list[EntryOut], dependencies=[Depends(require_ui_or_token)])
def api_list(db: Session = Depends(get_db)):
    records = list_tickets(db)
    return [_serialize_ticket(record) for record in records]


@router.get("/{entry_id}", response_model=EntryOut, dependencies=[Depends(require_ui_or_token)])
def api_get(entry_id: int, db: Session = Depends(get_db)):
    r = get_ticket(db, entry_id)
    if not r:
        raise HTTPException(404, "Not found")
    return _serialize_ticket(r)


@router.post("", response_model=EntryOut, status_code=201, dependencies=[Depends(require_ui_or_token)])
def api_create(payload: EntryCreate, db: Session = Depends(get_db)):
    try:
        ticket = create_entry(db, payload.model_dump(exclude_unset=True))
        return _serialize_ticket(ticket)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/{entry_id}", response_model=EntryOut, dependencies=[Depends(require_ui_or_token)])
def api_update(entry_id: int, payload: EntryUpdate, db: Session = Depends(get_db)):
    r = get_ticket(db, entry_id)
    if not r:
        raise HTTPException(404, "Not found")
    try:
        data = {k: v for k, v in payload.model_dump().items() if v is not None}
        updated = update_ticket(db, r, data)
        return _serialize_ticket(updated)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{entry_id}/attachments", response_model=list[TicketAttachment], dependencies=[Depends(require_ui_or_token)])
def api_list_attachments(entry_id: int, db: Session = Depends(get_db)):
    ticket = get_ticket(db, entry_id)
    if not ticket:
        raise HTTPException(404, "Not found")
    records = list_ticket_attachments(ticket)
    return [_attachment_to_schema(ticket.id, record) for record in records]


@router.post(
    "/{entry_id}/attachments",
    response_model=TicketAttachment,
    status_code=201,
    dependencies=[Depends(require_ui_or_token)],
)
async def api_add_attachment(
    entry_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    ticket = get_ticket(db, entry_id)
    if not ticket:
        raise HTTPException(404, "Not found")
    filename = (file.filename or "").strip()
    if not filename:
        await file.close()
        raise HTTPException(status_code=400, detail="A file upload is required")
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_ATTACHMENT_TYPES:
        await file.close()
        raise HTTPException(
            status_code=415,
            detail="Only image attachments (PNG, JPG, GIF, WEBP) are supported",
        )
    try:
        attachment = add_ticket_attachment(db, ticket, filename, content_type, file.file)
    finally:
        await file.close()
    return _attachment_to_schema(ticket.id, attachment)


@router.get(
    "/{entry_id}/attachments/{attachment_id}",
    response_class=FileResponse,
    dependencies=[Depends(require_ui_or_token)],
)
def api_get_attachment(entry_id: int, attachment_id: str, db: Session = Depends(get_db)):
    ticket = get_ticket(db, entry_id)
    if not ticket:
        raise HTTPException(404, "Not found")
    resource = get_ticket_attachment(ticket, attachment_id)
    if not resource:
        raise HTTPException(404, "Attachment not found")
    record, path = resource
    if not path.exists():
        raise HTTPException(404, "Attachment not found")
    media_type = record.get("content_type") or "application/octet-stream"
    filename = record.get("filename") or path.name
    return FileResponse(path, media_type=media_type, filename=filename)


@router.delete("/{entry_id}", dependencies=[Depends(require_ui_or_token)])
def api_delete(entry_id: int, db: Session = Depends(get_db)):
    r = get_ticket(db, entry_id)
    if not r:
        raise HTTPException(404, "Not found")
    delete_ticket(db, r)
    return {"status": "deleted"}
