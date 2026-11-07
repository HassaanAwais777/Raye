"""Turning brand health into budget pressure — the L3 sentiment overlay.

The recommender's water-filling equalizes marginal returns aᵢ/(βᵢ + xᵢ) = λ.
Raye's brand health enters as a *multiplier on aᵢ*: a platform whose audience
talks more positively about the brand gets a proportionally steeper response
curve, so the optimizer — unchanged — shifts budget toward it. One mechanism,
two evidences.

Evidence mapping (honest by design — measured ≠ inferred):
  youtube  ← youtube comments  (direct: the ads run on the measured surface)
  google   ← reddit comments   (proxy: discussion/research channels, 0.5 weight)
  facebook / instagram / tiktok ← unmeasured in Raye's corpus → fall back to the
             GLOBAL brand index with zero deviation (factor 1.0). We do NOT
             invent sentiment for platforms we did not measure.

Shrinkage (empirical Bayes, same pattern as the L2 baseline):
  c = n / (n + prior_n)            confidence in the measurement
  D = c · proxy_weight · (S_e − S̄) shrunk deviation from the global voice
  factor = clip(1 + sensitivity · D, 1 − cap, 1 + cap)

With Raye's real corpus the platform-level deviations are small (±0.3%:
the corpus has a uniform platform voice), so factors land within ±2% — the
machinery responds to signal strength, it does not manufacture drama. The
PRODUCT board is where Raye's corpus differentiates sharply (±0.45 spread),
and it feeds creative/qualification decisions, not platform splits.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Dict, List, Sequence

from .bridge import SentimentSnapshot, ProductHealth
from ..recommender.curves import CurveFit

# ad platform → which Raye surface measures its audience voice, and how much a
# proxy surface is trusted vs a direct one
EVIDENCE: Dict[str, dict] = {
    "youtube": {"evidence": "youtube", "proxy_weight": 1.0},
    "google": {"evidence": "reddit", "proxy_weight": 0.5},
    "facebook": {"evidence": None},
    "instagram": {"evidence": None},
    "tiktok": {"evidence": None},
}

DEFAULT_PRIOR_N = 25_000      # comments needed before a measurement is half-trusted
DEFAULT_SENSITIVITY = 1.5     # full ±1.0 deviation swing → ±1.5× factor, pre-cap
DEFAULT_CAP = 0.12            # sentiment can move a platform by at most ±12%


@dataclass
class PlatformSentiment:
    platform: str
    evidence: str                 # Raye surface used ("-" = global fallback)
    n_comments: int
    net_weighted: float           # measured (or fallback) brand health
    deviation: float              # shrunk deviation from the global voice
    factor: float                 # multiplier applied to the curve's alpha


def platform_factors(snapshot: SentimentSnapshot,
                     platforms: Sequence[str],
                     prior_n: int = DEFAULT_PRIOR_N,
                     sensitivity: float = DEFAULT_SENSITIVITY,
                     cap: float = DEFAULT_CAP) -> Dict[str, PlatformSentiment]:
    """Per-platform sentiment multipliers for the water-filling optimizer."""
    s_bar = snapshot.global_.net_weighted
    out: Dict[str, PlatformSentiment] = {}
    for p in platforms:
        cfg = EVIDENCE.get(p, {"evidence": None})
        ev_key = cfg.get("evidence")
        ev = snapshot.platforms.get(ev_key) if ev_key else None
        if ev is not None and ev.n > 0:
            c = ev.n / (ev.n + prior_n)
            proxy_w = float(cfg.get("proxy_weight", 0.5))
            deviation = c * proxy_w * (ev.net_weighted - s_bar)
            out[p] = PlatformSentiment(
                platform=p, evidence=ev_key, n_comments=ev.n,
                net_weighted=ev.net_weighted, deviation=deviation,
                factor=_clip(1.0 + sensitivity * deviation, cap))
        else:
            # unmeasured surface: global fallback, zero deviation, factor 1.0
            fb = ev.net_weighted if ev else s_bar
            out[p] = PlatformSentiment(
                platform=p, evidence="-", n_comments=ev.n if ev else 0,
                net_weighted=fb, deviation=0.0, factor=1.0)
    return out


def _clip(x: float, cap: float) -> float:
    lo, hi = 1.0 - cap, 1.0 + cap
    return max(lo, min(hi, x))


def product_board(snapshot: SentimentSnapshot, prior_n: int = 2_000,
                  risk_below: float = 0.0) -> List[dict]:
    """Empirical-Bayes product reputation board.

    shrunk_i = (n_i·S_i + prior_n·S̄) / (n_i + prior_n)
    Products with few comments stay near the brand average; the corpus's real
    laggards (e.g. 38% negative share) survive shrinkage and get flagged.
    """
    s_bar = snapshot.global_.net_weighted
    rows = []
    for pr in snapshot.products:
        shrunk = (pr.n * pr.net_weighted + prior_n * s_bar) / (pr.n + prior_n) if pr.n else s_bar
        pos_share = pr.by_sentiment.get("positive", 0) / pr.n if pr.n else 0.0
        neg_share = pr.by_sentiment.get("negative", 0) / pr.n if pr.n else 0.0
        rows.append({
            "slug": pr.key, "name": pr.name, "category": pr.category,
            "n_comments": pr.n, "net_weighted": pr.net_weighted,
            "net_shrunk": round(shrunk, 4),
            "positive_share": round(pos_share, 4), "negative_share": round(neg_share, 4),
            "flag": ("risk" if shrunk < risk_below else
                     "tailwind" if shrunk > 0.25 else "neutral"),
        })
    rows.sort(key=lambda r: -r["net_shrunk"])
    return rows


def apply_to_fits(fits: List[CurveFit],
                  factors: Dict[str, PlatformSentiment]) -> List[CurveFit]:
    """Scale each curve's alpha by its sentiment factor (β untouched, R² untouched)."""
    return [replace(f, alpha=f.alpha * factors[f.platform].factor) if f.platform in factors
            else f for f in fits]
