"""Unified FastAPI application — mounts all three projects + YouTube + DB.

Run unified:  uvicorn backend.main:app --port 8000
Each project is also independently runnable via its CLI (see README).
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db.session import db_status, init_engine
from .nlp.router import router as nlp_router
from .optimizer.router import router as optimizer_router
from .audience.router import router as audience_router
from .youtube.router import router as youtube_router
from .findings.router import router as findings_router
from .google_ads.router import router as google_ads_router
from .reports.router import router as reports_router
from .repository.router import router as repository_router

app = FastAPI(
    title="AudienceLens Backend",
    description="YouTube Audience & Campaign Intelligence — unified API for the "
                "Raye NLP (Project A), Hisaab optimizer (Project B), and Project 3 "
                "audience/clustering modules, plus YouTube Data API v3 collection.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(nlp_router)
app.include_router(optimizer_router)
app.include_router(audience_router)
app.include_router(youtube_router)
app.include_router(findings_router)
app.include_router(google_ads_router)
app.include_router(reports_router)
app.include_router(repository_router)


@app.get("/api/v1/health", tags=["system"])
def health():
    init_engine()
    return {
        "status": "ok",
        "version": "0.2.0",
        "modules": {
            "nlp": "Project A — multilingual sentiment + ABSA",
            "optimizer": "Project B — water-fill budget optimization",
            "audience": "Project 3 — clustering + anomaly detection",
            "youtube": "YouTube Data API v3 collection",
            "findings": "Evidence-based findings engine (capstone)",
            "google_ads": "Google Ads GAQL (YouTube video campaigns)",
            "reports": "Report generation + PDF/DOCX export",
            "repository": "Neon persistence (sessions, messages, results)",
        },
        "integrations": {
            "youtube_connected": settings.youtube_connected,
            "google_ads_connected": settings.google_ads_connected,
            "database": db_status(),
        },
        "provenance_policy": [
            "LIVE_DATA", "MODEL_PREDICTION", "ESTIMATED_SCENARIO",
            "INFERENCE", "USER_INPUT", "INSUFFICIENT_DATA",
        ],
    }


@app.get("/", tags=["system"])
def root():
    return {"name": "AudienceLens Backend", "docs": "/docs", "health": "/api/v1/health"}
