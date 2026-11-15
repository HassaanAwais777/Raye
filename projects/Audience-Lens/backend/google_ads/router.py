"""Google Ads API router — YouTube video campaign metrics via GAQL."""
from __future__ import annotations

from fastapi import APIRouter

from .client import SUPPORTED_METRICS, fetch_metrics, status

router = APIRouter(prefix="/api/v1/google-ads", tags=["google-ads"])


@router.get("/status")
def status_endpoint():
    return status()


@router.get("/metrics")
def metrics_endpoint():
    return fetch_metrics()


@router.get("/supported-metrics")
def supported():
    return {"metrics": SUPPORTED_METRICS}
