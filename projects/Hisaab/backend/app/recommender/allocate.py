"""Water-filling allocation — spending the NEXT budget optimally.

Problem   maximize  Σᵢ aᵢ·ln(1 + xᵢ/βᵢ)     subject to  Σᵢ xᵢ = B,  xᵢ ≥ 0
Solution  equalize marginal returns:  aᵢ/(βᵢ + xᵢ) = λ  ⇒  xᵢ(λ) = aᵢ/λ − βᵢ

xᵢ(λ) is decreasing in λ, so we bisect on λ until Σ xᵢ(λ) = B. Platforms with
aᵢ/λ ≤ βᵢ at the solution get ZERO — the math itself refuses to fund a saturated,
low-return platform. That is the whole industry argument for marginal thinking.
"""
from __future__ import annotations

from typing import Dict, List

import numpy as np

from .curves import CurveFit


def water_fill(fits: List[CurveFit], budget: float) -> Dict[str, float]:
    """Optimal split of `budget` across platforms given fitted curves."""
    if budget <= 0 or not fits:
        return {f.platform: 0.0 for f in fits}
    active = [f for f in fits if f.alpha > 0]

    def total(lam: float) -> float:
        return sum(max(0.0, f.alpha / lam - f.beta) for f in active)

    lo, hi = 1e-12, max((f.alpha / f.beta if f.beta > 0 else f.alpha for f in active),
                        default=1e-12)
    for _ in range(200):                                   # bisection: total() monotone ↓ in λ
        mid = (lo + hi) / 2
        if total(mid) > budget:
            lo = mid
        else:
            hi = mid
    lam = (lo + hi) / 2
    alloc = {f.platform: round(max(0.0, f.alpha / lam - f.beta), 2) for f in fits}
    # numeric residue → give to the platform with the highest marginal return
    residue = budget - sum(alloc.values())
    if active and residue > 0:
        best = max(active, key=lambda f: f.marginal_roas(alloc[f.platform]))
        alloc[best.platform] = round(alloc[best.platform] + residue, 2)
    return alloc


def expected_outcomes(fits: List[CurveFit], alloc: Dict[str, float]) -> Dict[str, dict]:
    """Incremental revenue / marginal ROAS per platform under an allocation."""
    out = {}
    for f in fits:
        x = alloc.get(f.platform, 0.0)
        inc = max(0.0, f.alpha * float(np.log1p(x / f.beta))) if f.alpha > 0 else 0.0
        out[f.platform] = {
            "allocated": x,
            "expected_incremental_revenue": round(inc, 2),
            "marginal_roas": round(f.marginal_roas(x), 4),
            "curve_alpha": round(f.alpha, 2),
            "curve_beta": round(f.beta, 2),
            "curve_r2": f.r2,
            "weekly_points": f.points,
        }
    return out
