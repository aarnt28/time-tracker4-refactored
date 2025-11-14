"""Pydantic schemas that describe project payloads for the API."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from .ticket import EntryOut


class ProjectBase(BaseModel):
    name: str
    client_key: str
    client: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    client_key: Optional[str] = None
    client: Optional[str] = None
    status: Optional[str] = None
    note: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    finalized_at: Optional[str] = None


class ProjectOut(ProjectBase):
    id: int
    created_at: str
    updated_at: str
    finalized_at: Optional[str] = None
    open_ticket_count: int = 0
    posted_ticket_count: int = 0
    ticket_count: int = 0

    class Config:
        from_attributes = True


class ProjectDetail(ProjectOut):
    tickets: list[EntryOut] = Field(default_factory=list)
