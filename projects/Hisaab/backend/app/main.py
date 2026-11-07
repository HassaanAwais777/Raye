"""FastAPI application."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .config import settings
from .api.routes import router

app = FastAPI(
    title="Hisaab API",
    version=settings.version,
    description="Digital advertising budget optimizer — metrics, Big-Data engine "
                "benchmarks (Pandas / MapReduce / Spark / Polars) and a saturation-curve "
                "budget recommendation engine.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.mount("/results", StaticFiles(directory=settings.results_dir), name="results")

# Serve the built dashboard (frontend/dist) from this same process, so the whole
# product runs with ONE command:  uvicorn app.main:app --port 8000  →  http://localhost:8000
# API routes above are matched first; this catch-all only serves the SPA.
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
else:
    @app.get("/")
    def root():
        return {"app": "Hisaab", "docs": "/docs", "api": "/api/health"}
