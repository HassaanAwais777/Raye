"""Persistence repository — saves research sessions, chat messages, and
sentiment results to Neon PostgreSQL when the DB is connected.

Every function is guarded: if the DB is not connected (no postgresql:// URL or
sqlalchemy missing), it returns None / empty and never raises. This keeps the
backend fully functional without persistence; persistence activates the moment
DATABASE_URL is set and migrations are applied.
"""
from __future__ import annotations

from typing import Any

from ..db.session import get_session, init_engine
from ..db import models


def db_ready() -> bool:
    return init_engine() is not None


def _status() -> dict[str, Any]:
    return {"persisted": False, "db_ready": db_ready()}


# ---------------------------------------------------------------------------
# Sessions & messages
# ---------------------------------------------------------------------------


def create_session(objective: str, country: str = "", workspace_name: str = "default") -> dict[str, Any]:
    """Create a research session + (lazily) its workspace. Returns the session id."""
    if not db_ready():
        return {"persisted": False, "db_ready": False, "session_id": None}
    session = get_session()
    if session is None:
        return {"persisted": False, "db_ready": False, "session_id": None}
    with session.begin():
        ws = session.query(models.Workspace).filter_by(name=workspace_name).first()
        if not ws:
            ws = models.Workspace(name=workspace_name)
            session.add(ws)
            session.flush()
        rs = models.ResearchSession(workspace_id=ws.id, objective=objective, country=country)
        session.add(rs)
        session.flush()
        sid = rs.id
        convo = models.ChatConversation(session_id=sid, title=objective[:80])
        session.add(convo)
        session.flush()
        cid = convo.id
    return {"persisted": True, "db_ready": True, "session_id": sid, "conversation_id": cid}


def add_message(conversation_id: str, role: str, content: str, meta: dict | None = None) -> dict[str, Any]:
    if not db_ready() or not conversation_id:
        return {"persisted": False, "db_ready": db_ready()}
    session = get_session()
    if session is None:
        return {"persisted": False, "db_ready": False}
    with session.begin():
        session.add(models.ChatMessage(
            conversation_id=conversation_id, role=role, content=content, meta=meta or {},
        ))
    return {"persisted": True, "db_ready": True}


def save_sentiment_results(comment_texts: list[str], results: list[dict]) -> dict[str, Any]:
    """Persist sentiment results. Comments are stored with a synthetic id when
    they don't come from YouTube (USER_INPUT provenance path)."""
    if not db_ready() or not results:
        return {"persisted": False, "db_ready": db_ready(), "n": 0}
    session = get_session()
    if session is None:
        return {"persisted": False, "db_ready": False, "n": 0}
    n = 0
    with session.begin():
        for text, r in zip(comment_texts, results):
            # Synthetic comment id for pasted (non-YouTube) comments
            vid = "pasted"
            import hashlib
            cid = "p-" + hashlib.sha1(text.encode()).hexdigest()[:16]
            existing = session.get(models.Comment, cid)
            if not existing:
                v = session.get(models.Video, vid)
                if not v:
                    v = models.Video(id=vid, channel_id="pasted", title="Pasted comments")
                    session.add(v)
                    session.flush()
                session.add(models.Comment(id=cid, video_id=vid, text=text))
                session.flush()
            session.add(models.SentimentResult(
                comment_id=cid,
                sentiment=r.get("sentiment", "uncertain"),
                score=float(r.get("score", 0)),
                confidence=float(r.get("confidence", 0)),
                language=r.get("language", "en"),
                aspects=r.get("aspects", []),
                provenance="MODEL_PREDICTION",
            ))
            n += 1
    return {"persisted": True, "db_ready": True, "n": n}


def list_sessions(limit: int = 20) -> dict[str, Any]:
    if not db_ready():
        return {"sessions": [], "db_ready": False}
    session = get_session()
    if session is None:
        return {"sessions": [], "db_ready": False}
    rows = session.query(models.ResearchSession).order_by(
        models.ResearchSession.created_at.desc()
    ).limit(limit).all()
    return {
        "sessions": [
            {
                "id": r.id, "objective": r.objective, "country": r.country,
                "status": r.status, "created_at": str(r.created_at),
            }
            for r in rows
        ],
        "db_ready": True,
    }
