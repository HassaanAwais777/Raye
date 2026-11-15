"""Database session — Neon PostgreSQL, optional at runtime.

Creates an engine only when DATABASE_URL is set. Otherwise returns None and the
backend continues to process requests statelessly (NLP/optimizer/audience work
without persistence; results carry provenance labels either way).
"""
from __future__ import annotations

from typing import Optional

# SQLAlchemy is optional at runtime — the backend starts and serves all routes
# even if it is not installed. Imports are guarded so a missing package never
# blocks startup; the DB layer simply stays inactive.
try:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session, sessionmaker
    _HAS_SQLALCHEMY = True
except ImportError:
    create_engine = None  # type: ignore
    Session = None  # type: ignore
    sessionmaker = None  # type: ignore
    _HAS_SQLALCHEMY = False

from ..config import settings

_engine = None
_SessionLocal = None


def init_engine():
    global _engine, _SessionLocal
    if not _HAS_SQLALCHEMY:
        return None
    # Neon PostgreSQL only — reject non-postgres URLs (e.g. the Next.js
    # scaffold's file: URL) and run statelessly instead.
    if not settings.db_enabled or not settings.database_url.startswith("postgresql"):
        return None
    if _engine is None:
        try:
            _engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
            _SessionLocal = sessionmaker(bind=_engine, class_=Session, expire_on_commit=False)
        except Exception:
            _engine = None
            return None
    return _engine


def get_session() -> Optional[Session]:
    if init_engine() is None:
        return None
    return _SessionLocal()


def db_status() -> dict:
    return {
        "enabled": settings.db_enabled and _HAS_SQLALCHEMY,
        "connected": _engine is not None,
        "sqlalchemy_installed": _HAS_SQLALCHEMY,
        "url_configured": bool(settings.database_url),
        "direct_url_configured": bool(settings.direct_url),
    }
