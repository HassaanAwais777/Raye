"""FastAPI router for DB persistence (sessions, messages, sentiment results)."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .sessions import (
    add_message, create_session, db_ready, list_sessions, save_sentiment_results,
)

router = APIRouter(prefix="/api/v1/sessions", tags=["persistence"])


class CreateSessionReq(BaseModel):
    objective: str
    country: str = ""
    workspace_name: str = "default"


class AddMessageReq(BaseModel):
    conversation_id: str
    role: str
    content: str
    meta: dict = Field(default_factory=dict)


class SentimentSaveReq(BaseModel):
    comment_texts: list[str]
    results: list[dict]


@router.get("/status")
def status():
    return {"db_ready": db_ready(), "provenance": "LIVE_DATA" if db_ready() else "INSUFFICIENT_DATA"}


@router.post("")
def create(req: CreateSessionReq):
    return create_session(req.objective, req.country, req.workspace_name)


@router.get("")
def list_all(limit: int = 20):
    return list_sessions(limit)


@router.post("/messages")
def add_msg(req: AddMessageReq):
    return add_message(req.conversation_id, req.role, req.content, req.meta)


@router.post("/sentiment")
def save_sent(req: SentimentSaveReq):
    return save_sentiment_results(req.comment_texts, req.results)
