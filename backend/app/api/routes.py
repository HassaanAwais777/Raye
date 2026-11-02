"""Raye REST API endpoints."""
import asyncio
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ..config import settings
from ..db import list_analyses, query_comments
from ..jobs import create_job, get_job
from ..scraping.orchestrator import Orchestrator
from ..scraping.registry import platform_meta, resolve_platforms
from ..schemas import AnalyzeRequest

router = APIRouter(prefix="/api")


@router.get("/health")
async def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "version": settings.version}


@router.get("/platforms")
async def platforms() -> dict:
    return {"platforms": platform_meta()}


@router.post("/analyses")
async def start_analysis(req: AnalyzeRequest) -> dict:
    if req.max_comments > settings.max_total_comments:
        raise HTTPException(400, f"max_comments exceeds server ceiling {settings.max_total_comments}")
    try:
        plats = resolve_platforms(req.platforms)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    job = create_job(req, plats)
    job.task = asyncio.create_task(Orchestrator(job).run())
    return {"job_id": job.id, "status": job.status, "platforms": plats}


@router.get("/analyses")
async def history(limit: int = Query(20, ge=1, le=50)) -> dict:
    rows = list_analyses(limit)
    for r in rows:
        import json

        try:
            r["progress"] = json.loads(r.pop("progress", "{}") or "{}")
        except ValueError:
            r["progress"] = {}
    return {"items": rows}


@router.get("/analyses/{job_id}")
async def job_status(job_id: str) -> dict:
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "analysis not found")
    return job


@router.get("/analyses/{job_id}/comments")
async def job_comments(
    job_id: str,
    sentiment: Optional[str] = Query(None, pattern="^(positive|negative|mixed|neutral)$"),
    lang: Optional[str] = None,
    aspect: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
) -> dict:
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "analysis not found")
    return query_comments(job_id, sentiment=sentiment, lang=lang, aspect=aspect,
                          page=page, page_size=page_size)
