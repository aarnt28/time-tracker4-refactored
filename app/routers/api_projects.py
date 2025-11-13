from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..crud.projects import (
    add_project_ticket,
    create_project,
    delete_project,
    finalize_project,
    get_project,
    list_projects,
    update_project,
)
from ..crud.tickets import (
    get_ticket,
    list_project_tickets,
    list_ticket_attachments,
    update_ticket,
    delete_ticket,
)
from ..db.session import get_db
from ..deps.auth import require_ui_or_token
from ..schemas.project import ProjectCreate, ProjectDetail, ProjectOut, ProjectUpdate
from ..schemas.ticket import EntryCreate, EntryOut, EntryUpdate, TicketAttachment

router = APIRouter(prefix="/api/v1/projects", tags=["projects"], dependencies=[Depends(require_ui_or_token)])


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


def _ticket_to_schema(ticket) -> EntryOut:
    payload = EntryOut.model_validate(ticket, from_attributes=True)
    attachment_records = list_ticket_attachments(ticket)
    payload.attachments = [
        _attachment_to_schema(ticket.id, record) for record in attachment_records
    ]
    return payload


def _project_to_schema(project, *, include_tickets: bool = False) -> ProjectOut | ProjectDetail:
    tickets = list(project.tickets or [])
    open_count = sum(1 for t in tickets if not t.project_posted)
    posted_count = sum(1 for t in tickets if t.project_posted)
    base = ProjectOut.model_validate(
        project,
        from_attributes=True,
    ).model_copy(
        update={
            "open_ticket_count": open_count,
            "posted_ticket_count": posted_count,
            "ticket_count": len(tickets),
        }
    )
    if not include_tickets:
        return base
    detail = ProjectDetail(**base.model_dump())
    detail.tickets = [_ticket_to_schema(ticket) for ticket in tickets]
    return detail


@router.get("", response_model=list[ProjectOut])
def api_list_projects(db: Session = Depends(get_db)):
    projects = list_projects(db)
    return [_project_to_schema(project) for project in projects]


@router.post("", response_model=ProjectOut, status_code=201)
def api_create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    try:
        project = create_project(db, payload.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    project = get_project(db, project.id) or project
    return _project_to_schema(project)


@router.get("/{project_id}", response_model=ProjectDetail)
def api_get_project(project_id: int, db: Session = Depends(get_db)):
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(404, "Not found")
    return _project_to_schema(project, include_tickets=True)


@router.patch("/{project_id}", response_model=ProjectOut)
def api_update_project(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db)):
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(404, "Not found")
    try:
        updated = update_project(db, project, payload.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    refreshed = get_project(db, updated.id) or updated
    return _project_to_schema(refreshed)


@router.delete("/{project_id}")
def api_delete_project(project_id: int, db: Session = Depends(get_db)):
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(404, "Not found")
    delete_project(db, project)
    return {"status": "deleted"}


@router.post("/{project_id}/finalize", response_model=ProjectOut)
def api_finalize_project(project_id: int, db: Session = Depends(get_db)):
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(404, "Not found")
    finalized = finalize_project(db, project)
    refreshed = get_project(db, finalized.id) or finalized
    return _project_to_schema(refreshed)


@router.get("/{project_id}/tickets", response_model=list[EntryOut])
def api_list_project_tickets(project_id: int, db: Session = Depends(get_db)):
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(404, "Not found")
    tickets = list_project_tickets(db, project.id)
    return [_ticket_to_schema(ticket) for ticket in tickets]


@router.post("/{project_id}/tickets", response_model=EntryOut, status_code=201)
def api_add_project_ticket(project_id: int, payload: EntryCreate, db: Session = Depends(get_db)):
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(404, "Not found")
    try:
        ticket = add_project_ticket(db, project, payload.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _ticket_to_schema(ticket)


@router.patch("/{project_id}/tickets/{ticket_id}", response_model=EntryOut)
def api_update_project_ticket(project_id: int, ticket_id: int, payload: EntryUpdate, db: Session = Depends(get_db)):
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(404, "Not found")
    ticket = get_ticket(db, ticket_id)
    if not ticket or ticket.project_id != project.id:
        raise HTTPException(404, "Not found")
    data = payload.model_dump(exclude_unset=True)
    data["project_id"] = project.id
    try:
        updated = update_ticket(db, ticket, data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _ticket_to_schema(updated)


@router.delete("/{project_id}/tickets/{ticket_id}")
def api_delete_project_ticket(project_id: int, ticket_id: int, db: Session = Depends(get_db)):
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(404, "Not found")
    ticket = get_ticket(db, ticket_id)
    if not ticket or ticket.project_id != project.id:
        raise HTTPException(404, "Not found")
    delete_ticket(db, ticket)
    return {"status": "deleted"}
