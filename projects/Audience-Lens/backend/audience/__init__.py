"""Project 3 — Audience clustering & anomaly detection.

Standalone CLI:
  python -m backend.audience.cli --texts comments.txt --method kmeans
  python -m backend.audience.cli --anomaly --series "v1,v2,v3,v4,v5,v6,v7,v8"
"""
from .engine import cluster, detect, build_features

__all__ = ["cluster", "detect", "build_features"]
