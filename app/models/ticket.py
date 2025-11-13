"""Beginner-friendly overview for this module.

WHAT: Handles the logic defined in "app/models/ticket.py" for the Time Tracker app.
WHEN: Invoked when its functions or classes are imported and called.
WHY: Provides supporting behaviour so the service runs smoothly.
HOW: Read the inline comments and docstrings below for the step-by-step flow.

File: app/models/ticket.py
"""


from __future__ import annotations
import json
from sqlalchemy import Column, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship
from ..db.session import Base


class Ticket(Base):
    __tablename__ = "tickets"
    __allow_unmapped__ = True

    id = Column(Integer, primary_key=True, index=True)
    client = Column(Text, nullable=False)
    client_key = Column(Text, nullable=False, index=True)
    start_iso = Column(Text, nullable=False)
    end_iso = Column(Text, nullable=True)
    elapsed_minutes = Column(Integer, nullable=False)
    rounded_minutes = Column(Integer, nullable=False)
    rounded_hours = Column(Text, nullable=False)
    note = Column(Text, nullable=True)
    completed = Column(Integer, nullable=False)
    sent = Column(Integer, nullable=False, default=0)
    invoice_number = Column(Text, nullable=True)
    created_at = Column(Text, nullable=False)
    minutes = Column(Integer, nullable=False, default=0)
    entry_type = Column(Text, nullable=False, default="time")

    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)
    project_posted = Column(Integer, nullable=False, default=0)

    # Link & snapshot when entry_type == 'hardware'
    hardware_id = Column(Integer, nullable=True, index=True)
    hardware_description = Column(Text, nullable=True)
    hardware_sales_price = Column(Text, nullable=True)
    hardware_quantity = Column(Integer, nullable=True, default=1)

    # Deployment flat rate metadata
    flat_rate_amount = Column(Text, nullable=True)
    flat_rate_quantity = Column(Integer, nullable=True, default=1)
    invoiced_total = Column(Text, nullable=True)
    calculated_value = Column(Text, nullable=True)
    attachments_blob = Column("attachments", Text, nullable=True)

    project = relationship("Project", back_populates="tickets")

    @property
    def hardware_barcode(self) -> str | None:
        return getattr(self, "_hardware_barcode", None)

    @hardware_barcode.setter
    def hardware_barcode(self, value: str | None) -> None:
        if value:
            self._hardware_barcode = value
        elif hasattr(self, "_hardware_barcode"):
            delattr(self, "_hardware_barcode")

    def _attachment_records(self) -> list[dict[str, object]]:
        raw = self.attachments_blob
        if not raw:
            return []
        try:
            decoded = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            return []
        if not isinstance(decoded, list):
            return []
        records: list[dict[str, object]] = []
        for item in decoded:
            if isinstance(item, dict):
                records.append(dict(item))
        return records

    def _store_attachment_records(self, records: list[dict[str, object]]) -> None:
        if not records:
            self.attachments_blob = None
            return
        self.attachments_blob = json.dumps(records)

    @property
    def attachments(self) -> list[dict[str, object]]:
        visible: list[dict[str, object]] = []
        for record in self._attachment_records():
            filtered = {
                k: v for k, v in record.items() if k != "storage_filename"
            }
            if "id" in filtered and filtered["id"] is not None:
                filtered["id"] = str(filtered["id"])
            visible.append(filtered)
        return visible

    @attachments.setter
    def attachments(self, value: list[dict[str, object]] | None) -> None:
        if not value:
            self.attachments_blob = None
            return
        if not isinstance(value, list):
            raise ValueError("attachments must be a list of objects")
        cleaned: list[dict[str, object]] = []
        for item in value:
            if isinstance(item, dict):
                cleaned.append(dict(item))
        self._store_attachment_records(cleaned)

    def get_attachment_record(self, attachment_id: str) -> dict[str, object] | None:
        for record in self._attachment_records():
            if str(record.get("id")) == str(attachment_id):
                return record
        return None
