"""SQLAlchemy model for project containers that group related tickets."""

from __future__ import annotations

from sqlalchemy import Column, Integer, Text
from sqlalchemy.orm import relationship

from ..db.session import Base


class Project(Base):
    """High level project that groups multiple tickets for a single client."""

    __tablename__ = "projects"
    __allow_unmapped__ = True

    id = Column(Integer, primary_key=True, index=True)
    name = Column(Text, nullable=False)
    client = Column(Text, nullable=False)
    client_key = Column(Text, nullable=False, index=True)
    status = Column(Text, nullable=True)
    note = Column(Text, nullable=True)
    start_date = Column(Text, nullable=True)
    end_date = Column(Text, nullable=True)
    created_at = Column(Text, nullable=False)
    updated_at = Column(Text, nullable=False)
    finalized_at = Column(Text, nullable=True)

    tickets = relationship("Ticket", back_populates="project")


__all__ = ["Project"]
