"""Raye — FastAPI application entrypoint.

Run:  uvicorn app.main:app --reload --port 8000
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .config import settings
from .db import get_conn


@asynccontextmanager
async def lifespan(_app: FastAPI):
    get_conn().execute("SELECT 1")  # initialise the SQLite schema eagerly
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description=(
        "Raye — evidence-based product review sentiment analysis. "
        "Crawls real comments from review videos/discussions across platforms, "
        "analyzes them multilingually (English / Urdu / Roman Urdu / code-mixed), "
        "and produces verdicts where every claim is traceable to its source."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def root() -> dict:
    return {"app": settings.app_name, "version": settings.version,
            "docs": "/docs", "health": "/api/health"}
