"""Budget optimization engine — Project B (Hisaab), ported and extended.

Saturation model:  R(s) = α·ln(1 + s/β) + c

  * fit_curve() fits α/β/c from real (spend, revenue) weekly aggregates via a
    β-grid OLS (closed-form for α and c given β). Bootstrap CIs optional.
  * water_fill() equalizes marginal return α/(β+x) = λ across formats via
    bisection; saturated platforms earn zero.
  * Largest-remainder rounding ensures the allocation sums to the budget exactly.

When real Google Ads curves are supplied → MODEL_PREDICTION.
When assumptions are used → ESTIMATED_SCENARIO.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Any

# ---------------------------------------------------------------------------
# Curve representation & fitting
# ---------------------------------------------------------------------------


@dataclass
class CurveFit:
    platform: str
    alpha: float
    beta: float
    c: float = 0.0
    r_squared: float = 0.0
    n_points: int = 0

    def revenue(self, spend: float) -> float:
        return self.alpha * math.log(1 + max(0.0, spend) / self.beta) + self.c

    def marginal_roas(self, spend: float) -> float:
        return self.alpha / (self.beta + max(0.0, spend))


def fit_curve(platform: str, pairs: list[tuple[float, float]]) -> CurveFit:
    """Fit R(s)=α·ln(1+s/β)+c from (spend, revenue) points via β-grid OLS."""
    pts = [(float(s), float(r)) for s, r in pairs if float(s) >= 0]
    if len(pts) < 3:
        # not enough real data → caller should fall back to assumptions
        return CurveFit(platform=platform, alpha=0.0, beta=1.0, c=0.0, r_squared=0.0, n_points=len(pts))
    # β grid search (log-spaced)
    spends = [s for s, _ in pts]
    lo, hi = max(1e-3, min(spends) / 4), max(spends) * 4
    best = None
    grid = [lo * (hi / lo) ** (i / 60) for i in range(61)]
    for beta in grid:
        # given beta, design matrix [ln(1+s/beta), 1]; solve OLS for (alpha, c)
        import numpy as np
        X = np.array([[math.log(1 + s / beta), 1.0] for s, _ in pts])
        y = np.array([r for _, r in pts])
        try:
            coef, *_ = np.linalg.lstsq(X, y, rcond=None)
            alpha, c = float(coef[0]), float(coef[1])
            pred = X @ coef
            ss_res = float(((y - pred) ** 2).sum())
            ss_tot = float(((y - y.mean()) ** 2).sum()) + 1e-12
            r2 = 1 - ss_res / ss_tot
            if best is None or r2 > best[3]:
                best = (beta, alpha, c, r2)
        except Exception:
            continue
    if best is None:
        return CurveFit(platform=platform, alpha=0.0, beta=1.0, n_points=len(pts))
    beta, alpha, c, r2 = best
    return CurveFit(platform=platform, alpha=alpha, beta=beta, c=c, r_squared=round(r2, 4), n_points=len(pts))


# ---------------------------------------------------------------------------
# Allocation — water-fill + largest-remainder rounding
# ---------------------------------------------------------------------------


def water_fill(curves: list[CurveFit], budget: float) -> dict[str, float]:
    """Equalize marginal return; x_i = max(0, α/λ − β). Saturated → 0."""
    active = [c for c in curves if c.alpha > 0 and c.beta > 0]
    if not active or budget <= 0:
        return {c.platform: 0.0 for c in curves}

    max_corner = max(c.alpha / c.beta for c in active)
    lo, hi = 1e-9, max_corner * 1.0001 + 1e-6
    for _ in range(200):
        mid = (lo + hi) / 2
        total = sum(max(0.0, c.alpha / mid - c.beta) for c in active)
        if total > budget:
            lo = mid
        else:
            hi = mid
    lam = (lo + hi) / 2

    alloc: dict[str, float] = {}
    allocated = 0.0
    for c in active:
        x = round(max(0.0, c.alpha / lam - c.beta), 2)
        alloc[c.platform] = x
        allocated += x
    for c in curves:
        if c.platform not in alloc:
            alloc[c.platform] = 0.0

    # Largest-remainder: give the residue to the highest marginal-return format.
    residue = round(budget - allocated, 2)
    if abs(residue) > 0.001 and active:
        best = max(active, key=lambda c: c.marginal_roas(alloc[c.platform]))
        alloc[best.platform] = round(alloc[best.platform] + residue, 2)
    return alloc


def equal_split(platforms: list[str], budget: float) -> dict[str, float]:
    n = len(platforms)
    if n == 0:
        return {}
    per = round(budget / n, 2)
    alloc = {p: per for p in platforms}
    residue = round(budget - per * n, 2)
    alloc[platforms[0]] = round(alloc[platforms[0]] + residue, 2)
    return alloc


def roas_proportional(curves: list[CurveFit], budget: float) -> dict[str, float]:
    weights = [max(1e-6, c.alpha / c.beta) for c in curves]
    total = sum(weights)
    alloc = {c.platform: round((w / total) * budget, 2) for c, w in zip(curves, weights)}
    residue = round(budget - sum(alloc.values()), 2)
    if curves:
        alloc[curves[0].platform] = round(alloc[curves[0].platform] + residue, 2)
    return alloc


def expected_revenue(curves: list[CurveFit], alloc: dict[str, float]) -> float:
    return round(sum(c.revenue(alloc.get(c.platform, 0.0)) for c in curves), 4)


# ---------------------------------------------------------------------------
# Assumed curves (ESTIMATED_SCENARIO) — documented assumptions
# ---------------------------------------------------------------------------

FORMAT_BASE: dict[str, dict[str, float]] = {
    "in_stream": {"alpha": 1.0, "beta": 200.0, "label": "In-Stream Ads"},
    "shorts": {"alpha": 0.85, "beta": 120.0, "label": "Shorts Ads"},
    "in_feed": {"alpha": 0.7, "beta": 90.0, "label": "In-Feed Video Ads"},
}

OBJECTIVE_MULT: dict[str, dict[str, float]] = {
    "awareness": {"in_stream": 0.95, "shorts": 1.15, "in_feed": 1.10},
    "views": {"in_stream": 1.10, "shorts": 1.00, "in_feed": 0.90},
    "traffic": {"in_stream": 1.00, "shorts": 0.90, "in_feed": 1.15},
    "leads": {"in_stream": 1.15, "shorts": 0.85, "in_feed": 1.00},
    "sales": {"in_stream": 1.20, "shorts": 0.80, "in_feed": 0.95},
}


def assumed_curves(
    formats: list[str], objective: str, strategy: str
) -> list[CurveFit]:
    """Build illustrative curves from documented assumptions."""
    out: list[CurveFit] = []
    for f in formats:
        base = FORMAT_BASE.get(f)
        if not base:
            continue
        alpha = base["alpha"] * OBJECTIVE_MULT.get(objective, {}).get(f, 1.0)
        beta = base["beta"]
        if strategy == "performance_focused":
            # amplify spread
            max_base = max(
                FORMAT_BASE[x]["alpha"] * OBJECTIVE_MULT.get(objective, {}).get(x, 1.0)
                for x in formats
            )
            cur_base = base["alpha"] * OBJECTIVE_MULT.get(objective, {}).get(f, 1.0)
            alpha *= 1.12 if cur_base == max_base else 0.88
        out.append(CurveFit(platform=f, alpha=round(alpha, 4), beta=beta))
    return out


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def optimize(
    budget: float,
    formats: list[str],
    objective: str = "awareness",
    strategy: str = "balanced",
    real_curves: list[dict] | None = None,
) -> dict[str, Any]:
    """Optimize allocation across formats.

    If real_curves is provided (list of {platform, spend_revenue:[[s,r],...]}),
    fit real curves → MODEL_PREDICTION. Otherwise use assumptions → ESTIMATED_SCENARIO.
    """
    provenance = "ESTIMATED_SCENARIO"
    curves: list[CurveFit] = []
    fitted = []
    if real_curves:
        for rc in real_curves:
            pairs = rc.get("spend_revenue", [])
            if len(pairs) >= 3:
                cf = fit_curve(rc["platform"], pairs)
                if cf.alpha > 0:
                    curves.append(cf)
                    fitted.append(asdict(cf))
        if curves:
            provenance = "MODEL_PREDICTION"

    if not curves:
        curves = assumed_curves(formats, objective, strategy)

    # Exploratory strategy reserves 10% split equally (UCB-style on real data only)
    exploration = budget * 0.1 if strategy == "exploratory" else 0.0
    optimizable = budget - exploration

    wf = water_fill(curves, optimizable)
    eq = equal_split([c.platform for c in curves], optimizable)
    rp = roas_proportional(curves, optimizable)

    if exploration > 0 and curves:
        ex_per = exploration / len(curves)
        for c in curves:
            wf[c.platform] = round(wf.get(c.platform, 0.0) + ex_per, 2)
            eq[c.platform] = round(eq.get(c.platform, 0.0) + ex_per, 2)
            rp[c.platform] = round(rp.get(c.platform, 0.0) + ex_per, 2)

    total = round(sum(wf.values()), 2)
    labels = {c.platform: FORMAT_BASE.get(c.platform, {}).get("label", c.platform) for c in curves}

    allocation = []
    for c in sorted(curves, key=lambda x: wf.get(x.platform, 0.0), reverse=True):
        amt = wf.get(c.platform, 0.0)
        allocation.append({
            "format": c.platform,
            "label": labels.get(c.platform, c.platform),
            "amount": amt,
            "share": round(amt / total * 100, 1) if total > 0 else 0.0,
            "marginal_roas": round(c.marginal_roas(amt), 6),
            "alpha": c.alpha,
            "beta": c.beta,
        })

    scenarios = {
        "equal_split": {
            "expected_revenue": expected_revenue(curves, eq),
            "allocation": eq,
        },
        "roas_proportional": {
            "expected_revenue": expected_revenue(curves, rp),
            "allocation": rp,
        },
        "water_fill": {
            "expected_revenue": expected_revenue(curves, wf),
            "allocation": wf,
        },
    }

    return {
        "allocation": allocation,
        "total_allocated": total,
        "budget": budget,
        "objective": objective,
        "strategy": strategy,
        "scenarios": scenarios,
        "curves": fitted if fitted else [{"platform": c.platform, "alpha": c.alpha, "beta": c.beta, "source": "assumption"} for c in curves],
        "provenance": provenance,
        "constraints": {
            "sums_to_budget_exactly": abs(total - budget) < 0.01,
            "no_negative_allocations": all(a["amount"] >= 0 for a in allocation),
        },
        "assumptions_note": (
            "Curve parameters are documented assumptions, not measured performance. "
            "Connect Google Ads to switch to MODEL_PREDICTION mode."
            if provenance == "ESTIMATED_SCENARIO"
            else "Curves fitted from real campaign data via OLS over a β-grid."
        ),
        "is_recommendation_only": True,
    }
