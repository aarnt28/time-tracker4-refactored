"""Beginner-friendly overview for this module.

WHAT: Handles the logic defined in "tests/test_tickets.py" for the Time Tracker app.
WHEN: Invoked when its functions or classes are imported and called.
WHY: Provides supporting behaviour so the service runs smoothly.
HOW: Read the inline comments and docstrings below for the step-by-step flow.

File: tests/test_tickets.py
"""


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
from app.crud.tickets import (
    CONTRACT_CLIENT_NOTE_PREFIX,
    create_entry,
    list_active_tickets,
)

# Ensure models are registered so metadata tables are created
from app.models import ticket as ticket_model  # noqa: F401
from app.models import project as project_model  # noqa: F401


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


def test_list_active_tickets_excludes_hardware_entries(db_session):
    open_time_ticket = create_entry(
        db_session,
        {
            "client_key": "client_a",
            "client": "Client A",
            "start_iso": "2024-01-01T09:00:00",
        },
    )

    # Hardware entries remain open but should not be returned by the active listing
    create_entry(
        db_session,
        {
            "client_key": "client_b",
            "client": "Client B",
            "entry_type": "hardware",
            "hardware_description": "Wireless Access Point",
            "hardware_quantity": 1,
            "hardware_sales_price": "250",
            "start_iso": "2024-01-02T09:00:00",
        },
    )

    # Deployment flat rate entries should also be excluded from the active listing
    create_entry(
        db_session,
        {
            "client_key": "client_d",
            "client": "Client D",
            "entry_type": "deployment_flat_rate",
            "flat_rate_amount": "600",
            "flat_rate_quantity": 2,
            "start_iso": "2024-01-04T09:00:00",
        },
    )

    closed_time_ticket = create_entry(
        db_session,
        {
            "client_key": "client_c",
            "client": "Client C",
            "start_iso": "2024-01-03T10:00:00",
            "end_iso": "2024-01-03T12:00:00",
        },
    )
    closed_time_ticket.end_iso = "2024-01-03T12:00:00"
    db_session.commit()

    active = list_active_tickets(db_session)

    assert [ticket.id for ticket in active] == [open_time_ticket.id]


def test_create_deployment_flat_rate_ticket(db_session):
    ticket = create_entry(
        db_session,
        {
            "client_key": "client_flat",
            "client": "Client Flat",
            "entry_type": "deployment_flat_rate",
            "flat_rate_amount": "750",
            "flat_rate_quantity": 3,
            "start_iso": "2024-03-05T09:00:00",
        },
    )

    assert ticket.entry_type == "deployment_flat_rate"
    assert ticket.flat_rate_amount == "750.00"
    assert ticket.flat_rate_quantity == 3
    assert ticket.calculated_value == "2250.00"


def test_contract_client_note_prefix_added(db_session):
    ticket = create_entry(
        db_session,
        {
            "client_key": "brightway",
            "client": "Brightway Dental (Elite)",
            "start_iso": "2024-02-01T09:00:00",
            "note": "Original note",
        },
    )

    assert ticket.note == f"{CONTRACT_CLIENT_NOTE_PREFIX}\nOriginal note"


def test_contract_client_note_prefix_not_duplicated(db_session):
    existing_note = f"{CONTRACT_CLIENT_NOTE_PREFIX}\nFollow up"
    ticket = create_entry(
        db_session,
        {
            "client_key": "asana",
            "client": "Asana Dental (Elite)",
            "start_iso": "2024-02-02T09:00:00",
            "note": existing_note,
        },
    )

    assert ticket.note == existing_note