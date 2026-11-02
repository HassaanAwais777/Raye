"""SQLite persistence (stdlib sqlite3, thread-safe via a lock).

Two tables:
  analyses  — job metadata, live progress JSON, final result JSON
  comments  — one row per analyzed comment with full source traceability
"""
import json
import sqlite3
import threading
from typing import Any, Dict, List, Optional

from .config import settings

_lock = threading.Lock()
_conn: Optional[sqlite3.Connection] = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS analyses (
    id TEXT PRIMARY KEY,
    query TEXT NOT NULL,
    params TEXT NOT NULL,
    status TEXT NOT NULL,
    phase TEXT NOT NULL DEFAULT 'queued',
    progress TEXT NOT NULL DEFAULT '{}',
    result TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS comments (
    id TEXT NOT NULL,
    analysis_id TEXT NOT NULL,
    platform TEXT NOT NULL,
    source_id TEXT,
    source_title TEXT,
    source_url TEXT,
    comment_url TEXT,
    author TEXT,
    lang TEXT,
    sentiment TEXT,
    score REAL,
    aspects TEXT,
    text_raw TEXT,
    text_normalized TEXT,
    likes INTEGER DEFAULT 0,
    published TEXT,
    fetched_at TEXT,
    PRIMARY KEY (analysis_id, id)
);
CREATE INDEX IF NOT EXISTS idx_comments_analysis ON comments(analysis_id);
CREATE INDEX IF NOT EXISTS idx_comments_sent ON comments(analysis_id, sentiment);
"""


def get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(settings.db_path, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.executescript(SCHEMA)
        _conn.commit()
    return _conn


def _now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def save_analysis(analysis_id: str, query: str, params: Dict[str, Any], status: str, phase: str,
                  progress: Dict[str, Any]) -> None:
    now = _now()
    with _lock, get_conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO analyses (id, query, params, status, phase, progress, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (analysis_id, query, json.dumps(params), status, phase, json.dumps(progress), now, now),
        )


def update_analysis(analysis_id: str, *, status: Optional[str] = None, phase: Optional[str] = None,
                    progress: Optional[Dict[str, Any]] = None, result: Optional[Dict[str, Any]] = None,
                    error: Optional[str] = None) -> None:
    sets, vals = ["updated_at=?"], [_now()]
    if status is not None:
        sets.append("status=?"); vals.append(status)
    if phase is not None:
        sets.append("phase=?"); vals.append(phase)
    if progress is not None:
        sets.append("progress=?"); vals.append(json.dumps(progress))
    if result is not None:
        sets.append("result=?"); vals.append(json.dumps(result))
    if error is not None:
        sets.append("error=?"); vals.append(error)
    vals.append(analysis_id)
    with _lock, get_conn() as c:
        c.execute(f"UPDATE analyses SET {', '.join(sets)} WHERE id=?", vals)


def get_analysis(analysis_id: str) -> Optional[Dict[str, Any]]:
    with _lock:
        row = get_conn().execute("SELECT * FROM analyses WHERE id=?", (analysis_id,)).fetchone()
    return dict(row) if row else None


def list_analyses(limit: int = 20) -> List[Dict[str, Any]]:
    with _lock:
        rows = get_conn().execute(
            "SELECT id, query, status, phase, progress, created_at FROM analyses ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def insert_comments(analysis_id: str, comments: List[Dict[str, Any]]) -> None:
    rows = [
        (
            analysis_id, c["id"], c["source"]["platform"], c["source"].get("source_id"),
            c["source"].get("title"), c["source"].get("url"), c["source"].get("comment_url"),
            c.get("author"), c.get("lang"), c.get("sentiment"), c.get("score"),
            json.dumps(c.get("aspects", [])), c.get("text_raw"), c.get("text_normalized"),
            c.get("likes", 0), c.get("published"), c.get("fetched_at"),
        )
        for c in comments
    ]
    with _lock, get_conn() as c:
        c.executemany(
            "INSERT OR IGNORE INTO comments (analysis_id, id, platform, source_id, source_title, source_url, "
            "comment_url, author, lang, sentiment, score, aspects, text_raw, text_normalized, likes, published, "
            "fetched_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            rows,
        )


def query_comments(analysis_id: str, *, sentiment: Optional[str] = None, lang: Optional[str] = None,
                   aspect: Optional[str] = None, page: int = 1, page_size: int = 25) -> Dict[str, Any]:
    where, vals = ["analysis_id=?"], [analysis_id]
    if sentiment:
        where.append("sentiment=?"); vals.append(sentiment)
    if lang:
        where.append("lang=?"); vals.append(lang)
    if aspect:
        where.append("aspects LIKE ?"); vals.append(f'%"{aspect}"%')
    cond = " AND ".join(where)
    with _lock:
        conn = get_conn()
        total = conn.execute(f"SELECT COUNT(*) FROM comments WHERE {cond}", vals).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM comments WHERE {cond} ORDER BY likes DESC, score DESC LIMIT ? OFFSET ?",
            vals + [page_size, (page - 1) * page_size],
        ).fetchall()
    items = []
    for r in rows:
        d = dict(r)
        items.append({
            "id": d["id"],
            "text_raw": d["text_raw"],
            "text_normalized": d["text_normalized"],
            "lang": d["lang"],
            "sentiment": d["sentiment"],
            "score": d["score"],
            "aspects": json.loads(d["aspects"] or "[]"),
            "likes": d["likes"],
            "published": d["published"],
            "source": {"platform": d["platform"], "source_id": d["source_id"], "title": d["source_title"],
                       "url": d["source_url"], "comment_url": d["comment_url"]},
        })
    return {"total": total, "page": page, "page_size": page_size, "items": items}


def comment_count(analysis_id: str) -> int:
    with _lock:
        return get_conn().execute(
            "SELECT COUNT(*) FROM comments WHERE analysis_id=?", (analysis_id,)
        ).fetchone()[0]
