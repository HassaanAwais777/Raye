"""FastAPI router for the optimizer module (Project B — Hisaab)."""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel, Field

from .engine import optimize

router = APIRouter(prefix="/api/v1/optimizer", tags=["optimizer"])


class OptimizeReq(BaseModel):
    budget: float = Field(..., gt=0)
    currency: str = "USD"
    objective: str = "awareness"
    strategy: str = "balanced"
    formats: list[str] = Field(default_factory=lambda: ["in_stream", "shorts", "in_feed"])
    # Optional real campaign history → switches to MODEL_PREDICTION
    real_curves: Optional[list[dict]] = None


@router.post("/optimize")
def optimize_endpoint(req: OptimizeReq):
    return optimize(
        budget=req.budget,
        formats=req.formats,
        objective=req.objective,
        strategy=req.strategy,
        real_curves=req.real_curves,
    )
