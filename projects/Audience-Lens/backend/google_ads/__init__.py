"""Google Ads API integration (optional — GAQL, YouTube video campaigns)."""
from .client import status, fetch_metrics, SUPPORTED_METRICS

__all__ = ["status", "fetch_metrics", "SUPPORTED_METRICS"]
