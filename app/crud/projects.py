"""CRUD helpers for project containers and their staged tickets."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session, selectinload

from ..models.project import Project
from ..models.ticket import Ticket
from ..services.clientsync import resolve_client_name
from .tickets import (
    create_entry,
    delete_ticket,
    list_project_tickets,
    update_ticket,
)


def _utcnow() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def list_projects(db: Session, limit: int = 200, offset: int = 0):
    stmt = (
        select(Project)
        .options(selectinload(Project.tickets))
        .order_by(desc(Project.created_at))
        .limit(limit)
        .offset(offset)
    )
    return db.execute(stmt).scalars().all()


def get_project(db: Session, project_id: int) -> Project | None:
    stmt = select(Project).options(selectinload(Project.tickets)).where(Project.id == project_id)
    return db.execute(stmt).scalars().first()


def create_project(db: Session, payload: dict) -> Project:
    name = (payload.get("name") or "").strip()
    if not name:
        raise ValueError("name is required")
    client_key = (payload.get("client_key") or "").strip()
    if not client_key:
        raise ValueError("client_key is required")
    client = (payload.get("client") or "").strip() or resolve_client_name(client_key)
    if not client:
        raise ValueError("client could not be resolved from client_key")
    now = _utcnow()
    project = Project(
        name=name,
        client_key=client_key,
        client=client,
        status=(payload.get("status") or None),
        note=(payload.get("note") or None),
        start_date=(payload.get("start_date") or None),
        end_date=(payload.get("end_date") or None),
        created_at=now,
        updated_at=now,
        finalized_at=(payload.get("finalized_at") or None),
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def update_project(db: Session, project: Project, payload: dict) -> Project:
    if "name" in payload:
        name = (payload.get("name") or "").strip()
        if not name:
            raise ValueError("name is required")
        project.name = name
    if "client_key" in payload or "client" in payload:
        client_key = (payload.get("client_key") or project.client_key or "").strip()
        if not client_key:
            raise ValueError("client_key is required")
        client = (payload.get("client") or "").strip() or resolve_client_name(client_key)
        if not client:
            raise ValueError("client could not be resolved from client_key")
        project.client_key = client_key
        project.client = client
    for field in ("status", "note", "start_date", "end_date", "finalized_at"):
        if field in payload:
            value = payload.get(field)
            project.__setattr__(field, value or None)
    project.updated_at = _utcnow()
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project: Project) -> None:
    # Remove project-only tickets (not yet posted). Posted tickets stay in history.
    staged = db.execute(
        select(Ticket).where(Ticket.project_id == project.id, Ticket.project_posted == 0)
    ).scalars().all()
    for ticket in staged:
        delete_ticket(db, ticket)
    posted = db.execute(
        select(Ticket).where(Ticket.project_id == project.id, Ticket.project_posted == 1)
    ).scalars().all()
    for ticket in posted:
        ticket.project_id = None
    db.delete(project)
    db.commit()


def finalize_project(db: Session, project: Project) -> Project:
    tickets = list_project_tickets(db, project.id, include_posted=False)
    for ticket in tickets:
        update_ticket(db, ticket, {"project_posted": 1})
    project.status = project.status or "finalized"
    project.finalized_at = _utcnow()
    project.updated_at = project.finalized_at
    db.commit()
    db.refresh(project)
    return project


def add_project_ticket(db: Session, project: Project, payload: dict):
    data = dict(payload)
    data["project_id"] = project.id
    data["project_posted"] = 0
    data["client_key"] = project.client_key
    data["client"] = project.client
    return create_entry(db, data)
*** End File
