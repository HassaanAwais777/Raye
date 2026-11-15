"""FastAPI router for YouTube Data API v3 collection."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from .client import (
    YouTubeError,
    get_channel,
    get_comments,
    get_playlist_videos,
    get_videos,
    quota_state,
    research,
    search_videos,
)
from ..config import settings

router = APIRouter(prefix="/api/v1/youtube", tags=["youtube"])


class ConfigureReq(BaseModel):
    api_key: str


@router.get("/status")
def status():
    return {
        "connected": settings.youtube_connected,
        "quota": quota_state(),
        "provenance": "LIVE_DATA" if settings.youtube_connected else "INSUFFICIENT_DATA",
        "detail": "YouTube Data API v3 ready." if settings.youtube_connected else "No API key configured. Set YOUTUBE_API_KEY or POST /configure.",
    }


@router.post("/configure")
def configure(req: ConfigureReq):
    """Set the YouTube API key in-memory for this backend session.

    The key is never persisted or logged — it lives only in the running process
    and is cleared on restart. Use the YOUTUBE_API_KEY env var for production.
    """
    settings.youtube_api_key = req.api_key.strip()
    return {
        "connected": settings.youtube_connected,
        "quota": quota_state(),
        "provenance": "USER_INPUT",
        "detail": "Key accepted for this session. Restart clears it." if settings.youtube_connected else "Empty key ignored.",
    }


@router.get("/search")
async def search(
    q: str = Query(..., min_length=1),
    country: str = Query(""),
    language: str = Query(""),
    limit: int = Query(25, ge=1, le=50),
    published_after: str = Query(""),
    published_before: str = Query(""),
):
    try:
        return await search_videos(q, country, language, published_after, published_before, limit=limit)
    except YouTubeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/videos")
async def videos(ids: str = Query(..., min_length=1)):
    try:
        return await get_videos([i.strip() for i in ids.split(",") if i.strip()])
    except YouTubeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/comments")
async def comments(video_id: str = Query(...), limit: int = Query(100, ge=1, le=200)):
    try:
        return await get_comments(video_id, limit=limit)
    except YouTubeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/channel")
async def channel(handle_or_id: str = Query(...)):
    try:
        return await get_channel(handle_or_id)
    except YouTubeError as e:
        raise HTTPException(status_code=503, detail=str(e))


@router.get("/playlist")
async def playlist(playlist_id: str = Query(...), limit: int = Query(50, ge=1, le=50)):
    try:
        return await get_playlist_videos(playlist_id, limit=limit)
    except YouTubeError as e:
        raise HTTPException(status_code=503, detail=str(e))


class ResearchReq(BaseModel):
    query: str
    country: str = ""
    max_videos: int = 5
    comments_per_video: int = 40
    aspect_catalog: str = "general"


@router.post("/research")
async def research_endpoint(req: ResearchReq):
    """Integrated pipeline: search videos → fetch comments → run NLP batch.

    Composes YouTube collection with the Project A sentiment pipeline in one call.
    Returns videos, comments, and the full sentiment distribution.
    """
    try:
        return await research(
            req.query,
            country=req.country,
            max_videos=req.max_videos,
            comments_per_video=req.comments_per_video,
            aspect_catalog=req.aspect_catalog,
        )
    except YouTubeError as e:
        raise HTTPException(status_code=503, detail=str(e))
