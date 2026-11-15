"""FastAPI router for the audience module (Project 3)."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .engine import cluster, detect

router = APIRouter(prefix="/api/v1/audience", tags=["audience"])


class ClusterReq(BaseModel):
    texts: list[str] = Field(..., min_length=1)
    method: str = "kmeans"  # kmeans | dbscan | hierarchical
    k: int | None = None


class AnomalyItem(BaseModel):
    label: str
    features: list[float]


class AnomalyReq(BaseModel):
    series: list[AnomalyItem]


@router.post("/cluster")
def cluster_endpoint(req: ClusterReq):
    return cluster(req.texts, method=req.method, k=req.k)


@router.post("/anomaly")
def anomaly_endpoint(req: AnomalyReq):
    return detect([{"label": it.label, "features": it.features} for it in req.series])
