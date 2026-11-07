"""Baseline allocators (L1, L2) — what the L3 engine is compared against.

Including weaker baselines is a deliberate teaching device: the dashboard shows all
three side by side, scored by the SAME fitted curves, so the improvement of marginal
optimisation over naive ROAS-proportional splitting is measurable, not hand-waved.
"""
from __future__ import annotations

from typing import Dict


def roas_proportional(roas_by_platform: Dict[str, float], budget: float) -> Dict[str, float]:
    """L1: split budget ∝ average ROAS. Ignores saturation entirely."""
    positive = {p: max(0.0, r) for p, r in roas_by_platform.items()}
    total = sum(positive.values())
    if total <= 0:
        return {p: 0.0 for p in roas_by_platform}
    return {p: round(budget * r / total, 2) for p, r in positive.items()}


def eb_shrunk_roas(rev_by_platform: Dict[str, float], spend_by_platform: Dict[str, float],
                   pseudo_spend: float) -> Dict[str, float]:
    """L2 helper: empirical-Bayes shrinkage of raw ROAS toward the blended mean.

    r_shrunk_i = (revᵢ + k·μ) / (spendᵢ + k),  μ = global revenue/spend, k = pseudo-spend.
    Platforms with little spend get pulled toward the global average — a principled
    guard against crowning a platform on 3 lucky weeks.
    """
    total_spend = sum(spend_by_platform.values())
    mu = (sum(rev_by_platform.values()) / total_spend) if total_spend > 0 else 0.0
    return {p: (rev_by_platform.get(p, 0.0) + pseudo_spend * mu)
            / (spend_by_platform.get(p, 0.0) + pseudo_spend)
            for p in spend_by_platform}


def bayes_shrunk_proportional(rev_by_platform: Dict[str, float],
                              spend_by_platform: Dict[str, float],
                              budget: float, pseudo_spend: float) -> Dict[str, float]:
    """L2: split budget ∝ shrunk ROAS."""
    shrunk = eb_shrunk_roas(rev_by_platform, spend_by_platform, pseudo_spend)
    return roas_proportional(shrunk, budget)
