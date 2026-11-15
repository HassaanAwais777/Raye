"""Neon PostgreSQL data layer (optional at runtime).

The backend starts and serves all routes even if SQLAlchemy is not installed —
the DB layer only activates when a postgresql:// DATABASE_URL is configured.
Models import is guarded so a missing sqlalchemy never blocks startup.
"""
try:
    from .models import Base  # noqa: F401
except ImportError:
    Base = None  # SQLAlchemy not installed; DB layer inactive
from .session import get_session, init_engine, db_status

__all__ = ["Base", "get_session", "init_engine", "db_status"]
