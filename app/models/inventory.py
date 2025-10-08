from __future__ import annotations

from sqlalchemy import Column, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import relationship

from ..db.session import Base


class InventoryEvent(Base):
    """A change in inventory for a hardware item.

    Positive ``change`` values represent stock being added while negatives
    represent usage/consumption.
    """

    __tablename__ = "inventory_events"

    id = Column(Integer, primary_key=True, index=True)
    hardware_id = Column(Integer, ForeignKey("hardware.id"), nullable=False, index=True)
    change = Column(Integer, nullable=False)
    source = Column(Text, nullable=False, default="manual")
    note = Column(Text, nullable=True)
    created_at = Column(Text, nullable=False)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=True, index=True)
    counterparty_name = Column(Text, nullable=True)
    counterparty_type = Column(Text, nullable=True)
    actual_cost = Column(Float, nullable=True)
    unit_cost = Column(Float, nullable=True)

    hardware = relationship("Hardware", lazy="joined")

    @property
    def hardware_barcode(self) -> str | None:
        return self.hardware.barcode if self.hardware else None

    @property
    def hardware_description(self) -> str | None:
        return self.hardware.description if self.hardware else None
