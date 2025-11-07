"""Beginner-friendly overview for this module.

WHAT: Handles the logic defined in "app/models/known_items.py" for the Time Tracker app.
WHEN: Invoked when its functions or classes are imported and called.
WHY: Provides supporting behaviour so the service runs smoothly.
HOW: Read the inline comments and docstrings below for the step-by-step flow.

File: app/models/known_items.py
"""


from __future__ import annotations
from sqlalchemy import Column, Integer, Text
from ..db.session import Base

class known_item(Base):
    __tablename__ = "tickets"
    id = Column(Integer, primary_key=True, index=True)
    barcode = Column(Integer, nullable=False, index=True)
    description = Column(Text, nullable=False, index=True)
    category = Column(Text, nullable=False)
    added_date = Column(Text, nullable=False, index=True)
    