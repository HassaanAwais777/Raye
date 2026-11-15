"""FastAPI router for the findings engine."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .engine import generate

router = APIRouter(prefix="/api/v1/findings", tags=["findings"])


class FindingsReq(BaseModel):
    texts: list[str] = Field(..., min_length=1)
    aspect_catalog: str = "general"
    cluster_method: str = "kmeans"


@router.post("/generate")
def generate_endpoint(req: FindingsReq):
    """Generate evidence-based finding cards from a set of comments."""
    return generate(req.texts, req.aspect_catalog, req.cluster_method)
