"""Beginner-friendly overview for this module.

WHAT: Handles the logic defined in "app/models/hardware.py" for the Time Tracker app.
WHEN: Invoked when its functions or classes are imported and called.
WHY: Provides supporting behaviour so the service runs smoothly.
HOW: Read the inline comments and docstrings below for the step-by-step flow.

File: app/models/hardware.py
"""


from __future__ import annotations
from sqlalchemy import Column, Integer, Text
from ..db.session import Base


class Hardware(Base):
    __tablename__ = "hardware"

    id = Column(Integer, primary_key=True, index=True)
    barcode = Column(Text, nullable=False, index=True, unique=True)
    description = Column(Text, nullable=False)
    acquisition_cost = Column(Text, nullable=True)
    sales_price = Column(Text, nullable=True)
    created_at = Column(Text, nullable=False)