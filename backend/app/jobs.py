"""In-memory job registry (source of truth is mirrored into SQLite)."""
import asyncio
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .db import get_analysis, save_analysis
from .schemas import AnalyzeRequest

MAX_JOBS_IN_MEMORY = 60


@dataclass
class JobState:
    id: str
    request: AnalyzeRequest
    platforms: List[str]
    status: str = "running"
    phase: str = "fetching"
    progress: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    comments: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    task: Optional[asyncio.Task] = None

    def public_progress(self) -> Dict[str, Any]:
        prog = dict(self.progress)
        prog["per_platform"] = prog.get("per_platform", {})
        return prog


JOBS: Dict[str, JobState] = {}


def create_job(request: AnalyzeRequest, platforms: List[str]) -> JobState:
    _prune()
    job = JobState(id=uuid.uuid4().hex[:16], request=request, platforms=platforms)
    JOBS[job.id] = job
    save_analysis(job.id, request.query, request.model_dump(), job.status, job.phase,
                  job.progress)
    return job


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Live view from memory; falls back to SQLite (e.g. after a restart)."""
    job = JOBS.get(job_id)
    if job:
        return {
            "job_id": job.id, "query": job.request.query, "status": job.status,
            "phase": job.phase, "progress": job.public_progress(),
            "result": job.result, "error": job.error,
            "platforms": job.platforms,
        }
    row = get_analysis(job_id)
    if not row:
        return None
    return {
        "job_id": row["id"], "query": row["query"], "status": row["status"],
        "phase": row["phase"], "progress": _json(row["progress"]), "result": _json(row["result"]),
        "error": row["error"], "platforms": (_json(row["params"]) or {}).get("platforms"),
    }


def _json(raw: Any) -> Any:
    import json

    if not raw:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return None


def _prune() -> None:
    if len(JOBS) < MAX_JOBS_IN_MEMORY:
        return
    done = [jid for jid, j in JOBS.items() if j.status in ("done", "failed")]
    done.sort(key=lambda jid: JOBS[jid].created_at)
    for jid in done[: len(done) // 2]:
        JOBS.pop(jid, None)
