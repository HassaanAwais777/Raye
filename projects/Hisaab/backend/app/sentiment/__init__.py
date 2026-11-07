"""Sentiment bridge — the Raye → Hisaab integration.

Raye (companion project, github.com/HassaanAwais777/Raye) analysed 210,511
product comments from YouTube and Reddit in EN / Urdu / Roman-Urdu and labelled
each with a sentiment score in [-1, 1]. This package turns that export into a
*brand-health signal* the budget recommender can consume:

  bridge.py  — load the exported aggregates (JSON fast path) or recompute them
               from a raw export CSV
  adjust.py  — convert brand health into per-platform multipliers for the
               water-filling optimizer + an empirical-Bayes product risk board
"""
from .bridge import BrandHealth, ProductHealth, SentimentSnapshot, load_snapshot
from .adjust import (PlatformSentiment, platform_factors, product_board,
                     apply_to_fits, EVIDENCE)

__all__ = [
    "BrandHealth", "ProductHealth", "SentimentSnapshot", "load_snapshot",
    "PlatformSentiment", "platform_factors", "product_board", "apply_to_fits",
    "EVIDENCE",
]
