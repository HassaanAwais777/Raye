"""FastAPI router for the NLP module (Project A)."""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from .pipeline import ASPECT_CATALOGS, analyze_text, analyze_batch

router = APIRouter(prefix="/api/v1/nlp", tags=["nlp"])


class AnalyzeReq(BaseModel):
    text: str = Field(..., min_length=1)
    aspect_catalog: str = "general"


class BatchReq(BaseModel):
    texts: list[str] = Field(..., min_length=1)
    aspect_catalog: str = "general"


@router.get("/aspects/{catalog}")
def list_aspects(catalog: str):
    """List the aspects in a given catalog."""
    if catalog not in ASPECT_CATALOGS:
        return {"available": list(ASPECT_CATALOGS.keys()), "aspects": []}
    return {
        "catalog": catalog,
        "aspects": [
            {"name": a["name"], "label": a["label"], "keywords": a["keywords"]}
            for a in ASPECT_CATALOGS[catalog]
        ],
        "available": list(ASPECT_CATALOGS.keys()),
    }


@router.post("/analyze")
def analyze(req: AnalyzeReq):
    """Analyze a single comment."""
    return analyze_text(req.text, req.aspect_catalog)


@router.post("/analyze-batch")
def analyze_many(req: BatchReq):
    """Analyze a batch of comments; returns distribution + topics."""
    return analyze_batch(req.texts, req.aspect_catalog)
