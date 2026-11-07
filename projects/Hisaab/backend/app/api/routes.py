"""REST API routes."""
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException

from ..config import settings
from ..db import list_datasets, latest_benchmark, list_recommendations
from ..generator import get_locale
from ..generator.locales import LOCALES
from ..schemas import GenerateRequest, BenchmarkRequest, RecommendRequest
from ..service import create_dataset, dataset_overview, recommend_budget, sentiment_summary
from ..benchmark.harness import run_matrix
from ..benchmark.costs import cost_table
from ..engines import engine_catalog

router = APIRouter(prefix="/api")


@router.get("/health")
def health():
    return {"status": "ok", "version": settings.version, "app": settings.app_name}


@router.get("/locales")
def locales():
    return [{"id": code, "label": lp.label, "currency": lp.currency, "symbol": lp.symbol,
             "cities": [c[0] for c in lp.cities][:5] + ["…"], "seasons": [s[0] for s in lp.seasons]}
            for code, lp in LOCALES.items()]


@router.get("/engines")
def engines():
    return engine_catalog()


@router.post("/datasets")
def post_dataset(req: GenerateRequest):
    try:
        return create_dataset(req.rows, req.locale, req.seed, req.with_csv)
    except ValueError as e:
        raise HTTPException(409, str(e))


@router.get("/datasets")
def get_datasets():
    return list_datasets()


@router.get("/datasets/{ds_id}/overview")
def get_overview(ds_id: str, by: str = "platform"):
    try:
        return dataset_overview(ds_id, by)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/benchmark")
def post_benchmark(req: BenchmarkRequest):
    try:
        payload = run_matrix(req.scales, req.engines, req.locale, req.repeat, req.mr_procs)
        return payload
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/benchmark/latest")
def get_benchmark():
    payload = latest_benchmark()
    if not payload:
        raise HTTPException(404, "no benchmark run yet — POST /api/benchmark first")
    rows_label = str(max(payload["scales"]))
    payload = dict(payload)
    payload["cost_model"] = cost_table(payload["results"], rows_label)
    return payload


@router.post("/recommend")
def post_recommend(req: RecommendRequest):
    try:
        return recommend_budget(req.dataset, req.budget, req.with_ci, req.sentiment_aware)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/sentiment/summary")
def get_sentiment_summary():
    """Raye → Hisaab voice-of-customer snapshot (brand health, factors, product board)."""
    try:
        return sentiment_summary()
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))


@router.get("/recommend/history")
def get_recommendations():
    return list_recommendations()
