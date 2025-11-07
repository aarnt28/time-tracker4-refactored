"""SQLAlchemy session helpers with beginner-friendly guidance."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from ..core.config import settings

# For SQLite, ensure ``check_same_thread=False`` so the connection can be shared
# by FastAPI worker threads. Other database engines ignore this argument.
CONNECT_ARGS = {"check_same_thread": False} if settings.DB_URL.startswith("sqlite") else {}

# The engine manages the actual database connection pool. Creating it once per
# process keeps things fast and memory efficient.
engine = create_engine(settings.DB_URL, connect_args=CONNECT_ARGS)
# ``SessionLocal`` is a factory function that builds new sessions per request.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# ``Base`` is the parent class for every SQLAlchemy model defined in app/models.
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a session and guarantees cleanup."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
