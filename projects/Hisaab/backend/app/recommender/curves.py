"""Saturation response curves — the L3 modelling core.

Model per platform:  R(s) = a·ln(1 + s/β) + c
  R(s) : revenue from spending s
  a    : revenue scale of the log curve
  β    : saturation half-scale — spend at which the curve has reached ln(2) of its
         logarithmic growth; small β ⇒ saturates early
  c    : baseline revenue at zero spend (attribution noise floor)

Why log? Diminishing returns are the empirical reality of ad platforms (auction
competition, audience fatigue). The marginal return dR/ds = a/(β + s) is strictly
decreasing — exactly the property the water-filling optimizer needs.

Fitting: for a FIXED β the model is linear in (1, ln(1+s/β)) — closed-form OLS.
β is chosen from a log-spaced grid by minimum SSE. No scipy required; auditable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple

import numpy as np


@dataclass
class CurveFit:
    platform: str
    alpha: float
    beta: float
    intercept: float
    r2: float
    points: int                    # weekly observations used
    spend_observed: float          # max weekly spend seen (extrapolation guard)

    def predict(self, spend: float) -> float:
        return self.alpha * np.log1p(max(0.0, spend) / self.beta) + self.intercept

    def marginal_roas(self, spend: float) -> float:
        """dR/ds at spend — 'what the NEXT rupee returns'."""
        return self.alpha / (self.beta + max(0.0, spend))


_BETA_GRID_FRACTION = np.geomspace(0.05, 20.0, 60)   # × median weekly spend (floor half)
_BETA_MAX_TO_MAX_SPEND = 2.0   # β beyond ~2× the largest observed weekly spend is not
                               # identifiable from the data — cap the grid there, or OLS
                               # drifts to the linear corner and the optimizer starves
                               # every platform but the steepest one.


def fit_curve(platform: str, spend: Sequence[float], revenue: Sequence[float]) -> CurveFit:
    s = np.asarray(spend, dtype=np.float64)
    r = np.asarray(revenue, dtype=np.float64)
    if len(s) < 3 or s.sum() <= 0:
        return CurveFit(platform, 0.0, 1.0, 0.0, 0.0, len(s), float(s.max(initial=0)))
    med = float(np.median(s[s > 0])) or 1.0
    beta_grid = _BETA_GRID_FRACTION * med
    beta_grid = beta_grid[beta_grid <= _BETA_MAX_TO_MAX_SPEND * max(float(s.max()), med)]

    best = None
    for beta in beta_grid:
        x = np.log1p(s / beta)
        A = np.stack([np.ones_like(x), x], axis=1)
        coef, *_ = np.linalg.lstsq(A, r, rcond=None)
        resid = r - A @ coef
        sse = float(resid @ resid)
        if best is None or sse < best[0]:
            best = (sse, coef[0], beta, coef[1])
    sse, c, beta, a = best
    sst = float(((r - r.mean()) ** 2).sum())
    r2 = 1.0 - sse / sst if sst > 0 else 0.0
    return CurveFit(platform, float(a), float(beta), float(c), round(r2, 4),
                    len(s), float(s.max()))


def fit_all(weekly) -> List[CurveFit]:
    """weekly: DataFrame with columns [platform, spend, revenue]."""
    fits = []
    for p, g in weekly.groupby("platform"):
        fits.append(fit_curve(str(p), g["spend"].to_numpy(), g["revenue"].to_numpy()))
    fits.sort(key=lambda f: -f.alpha)
    return fits


def bootstrap_curves(weekly, resamples: int = 200, seed: int = 7
                     ) -> dict:
    """Non-parametric bootstrap over weekly points → CI for α, β per platform.

    Returns {platform: {"alpha_ci": [lo, hi], "beta_ci": [lo, hi]}}.
    """
    rng = np.random.default_rng(seed)
    out = {}
    for p, g in weekly.groupby("platform"):
        s = g["spend"].to_numpy()
        r = g["revenue"].to_numpy()
        n = len(s)
        if n < 4:
            out[str(p)] = {"alpha_ci": None, "beta_ci": None, "n": n}
            continue
        alphas, betas = [], []
        for _ in range(resamples):
            idx = rng.integers(0, n, n)
            f = fit_curve("boot", s[idx], r[idx])
            alphas.append(f.alpha)
            betas.append(f.beta)
        out[str(p)] = {
            "alpha_ci": [float(np.percentile(alphas, 5)), float(np.percentile(alphas, 95))],
            "beta_ci": [float(np.percentile(betas, 5)), float(np.percentile(betas, 95))],
            "n": n,
        }
    return out
