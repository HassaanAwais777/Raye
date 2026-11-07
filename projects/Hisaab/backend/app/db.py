"""SQLite persistence: datasets, benchmarks, recommendations (stdlib only)."""
import json
import sqlite3
import time
from typing import Dict, List, Optional

from .config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS datasets (
    id TEXT PRIMARY KEY, rows INTEGER, locale TEXT, seed INTEGER,
    parquet_path TEXT, csv_path TEXT, csv_rows INTEGER,
    currency TEXT, generation_seconds REAL, created_at TEXT
);
CREATE TABLE IF NOT EXISTS benchmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, payload TEXT
);
CREATE TABLE IF NOT EXISTS recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT, payload TEXT
);
"""


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(settings.db_path))
    c.row_factory = sqlite3.Row
    c.executescript(_SCHEMA)
    return c


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def save_dataset(rec: Dict) -> None:
    with _conn() as c:
        c.execute("INSERT OR REPLACE INTO datasets VALUES (?,?,?,?,?,?,?,?,?,?)",
                  (rec["id"], rec["rows"], rec["locale"], rec["seed"], rec["parquet_path"],
                   rec.get("csv_path", ""), rec.get("csv_rows", 0), rec["currency"],
                   rec.get("generation_seconds", 0), _now()))


def get_dataset(ds_id: str) -> Optional[Dict]:
    with _conn() as c:
        row = c.execute("SELECT * FROM datasets WHERE id = ?", (ds_id,)).fetchone()
    return dict(row) if row else None


def list_datasets(limit: int = 50) -> List[Dict]:
    with _conn() as c:
        rows = c.execute("SELECT * FROM datasets ORDER BY created_at DESC LIMIT ?",
                         (limit,)).fetchall()
    return [dict(r) for r in rows]


def save_benchmark(payload: Dict) -> None:
    with _conn() as c:
        c.execute("INSERT INTO benchmarks (created_at, payload) VALUES (?,?)",
                  (_now(), json.dumps(payload)))


def save_recommendation(payload: Dict) -> None:
    with _conn() as c:
        c.execute("INSERT INTO recommendations (created_at, payload) VALUES (?,?)",
                  (_now(), json.dumps(payload)))


def latest_benchmark() -> Optional[Dict]:
    with _conn() as c:
        row = c.execute("SELECT payload FROM benchmarks ORDER BY id DESC LIMIT 1").fetchone()
    return json.loads(row["payload"]) if row else None


def list_recommendations(limit: int = 20) -> List[Dict]:
    with _conn() as c:
        rows = c.execute("SELECT id, created_at, payload FROM recommendations "
                         "ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [{"id": r["id"], "created_at": r["created_at"],
             **{k: v for k, v in json.loads(r["payload"]).items() if k != "dataset"}}
            for r in rows]
