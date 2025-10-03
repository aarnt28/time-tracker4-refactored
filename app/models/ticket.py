from __future__ import annotations
from sqlalchemy import Column, Integer, Text
from ..db.session import Base

class Ticket(Base):
    __tablename__ = "entries"
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
    invoice_number = Column(Text, nullable=True)
    created_at = Column(Text, nullable=False)
    minutes = Column(Integer, nullable=False, default=0)
