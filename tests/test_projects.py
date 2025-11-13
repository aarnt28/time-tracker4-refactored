"""Tests for project containers and staged ticket workflows."""

import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DATA_DIR", str(ROOT / "data"))

from app.db.session import Base
from app.crud.projects import create_project, finalize_project, add_project_ticket
from app.crud.tickets import list_project_tickets, list_tickets, get_ticket

# Ensure models are registered so metadata tables are created
from app.models import project as project_model  # noqa: F401
from app.models import ticket as ticket_model  # noqa: F401


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_project_finalize_posts_tickets(db_session):
    project = create_project(
        db_session,
        {"name": "Office build", "client_key": "client_a", "client": "Client A"},
    )
    staged_ticket = add_project_ticket(
        db_session,
        project,
        {
            "start_iso": "2024-05-01T09:00:00",
            "end_iso": "2024-05-01T11:00:00",
            "client_key": "client_a",
            "client": "Client A",
            "note": "Rack install",
        },
    )

    # Tickets linked to a project stay hidden from the main list until posted
    visible_ticket_ids = [t.id for t in list_tickets(db_session)]
    assert staged_ticket.id not in visible_ticket_ids

    finalize_project(db_session, project)
    refreshed = get_ticket(db_session, staged_ticket.id)
    assert refreshed.project_posted == 1
    assert refreshed.project_id == project.id

    # Once finalised the ticket shows up in the main dashboard feed
    visible_ticket_ids = [t.id for t in list_tickets(db_session)]
    assert staged_ticket.id in visible_ticket_ids

    project_tickets = list_project_tickets(db_session, project.id)
    assert len(project_tickets) == 1
    assert project_tickets[0].project_posted == 1
    assert project.finalized_at is not None
