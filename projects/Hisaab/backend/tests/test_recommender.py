"""Water-filling + curve fitting: the mathematical heart of the recommender."""
import math

import numpy as np
import pandas as pd
import pytest

from app.recommender.curves import fit_curve, fit_all
from app.recommender.allocate import water_fill, expected_outcomes
from app.recommender.baselines import roas_proportional, bayes_shrunk_proportional


def _synthetic_weeks(alpha, beta, weeks=40, seed=0, noise=0.05):
    rng = np.random.default_rng(seed)
    spend = rng.uniform(5_000, 400_000, weeks)
    revenue = alpha * np.log1p(spend / beta) + rng.normal(0, noise * alpha, weeks)
    return pd.DataFrame({"platform": "x", "spend": spend, "revenue": revenue})


def test_fit_recovers_known_curve():
    alpha_true, beta_true = 900_000, 120_000
    df = _synthetic_weeks(alpha_true, beta_true, seed=3)
    fit = fit_curve("x", df.spend, df.revenue)
    # weekly aggregates + noise: recovering α within 20% and β within 40% is strong
    assert fit.alpha == pytest.approx(alpha_true, rel=0.20)
    assert fit.beta == pytest.approx(beta_true, rel=0.40)
    assert fit.r2 > 0.90


def test_marginal_roas_decreasing():
    fit = fit_curve("x", *_synthetic_weeks(500_000, 80_000, seed=1)[["spend", "revenue"]].to_numpy().T)
    assert fit.marginal_roas(10_000) > fit.marginal_roas(100_000) > fit.marginal_roas(500_000)


def test_water_fill_sums_to_budget():
    fits = [fit_curve(p, *_synthetic_weeks(a, b, seed=i)[["spend", "revenue"]].to_numpy().T)
            for i, (p, a, b) in enumerate([("google", 1.1e6, 90_000),
                                           ("facebook", 7e5, 110_000),
                                           ("tiktok", 3e5, 150_000)])]
    alloc = water_fill(fits, 1_000_000)
    assert sum(alloc.values()) == pytest.approx(1_000_000, abs=1.0)
    assert alloc["google"] > alloc["facebook"] > alloc["tiktok"], alloc


def test_water_fill_starves_saturated_platform():
    """A platform with a tiny alpha and huge beta earns (almost) nothing at the margin."""
    fits = [fit_curve("good", *_synthetic_weeks(1.2e6, 80_000, seed=1)[["spend", "revenue"]].to_numpy().T),
            fit_curve("dud", *_synthetic_weeks(3e5, 900_000, seed=2)[["spend", "revenue"]].to_numpy().T)]
    alloc = water_fill(fits, 400_000)
    assert alloc["good"] / 400_000 > 0.7


def test_water_fill_empty_budget():
    fits = [fit_curve("x", *_synthetic_weeks(1e6, 1e5, seed=1)[["spend", "revenue"]].to_numpy().T)]
    assert water_fill([], 1000) == {}
    assert all(v == 0 for v in water_fill(fits, 0).values())


def test_baselines_sum_to_budget():
    roas = {"facebook": 3.0, "instagram": 3.1, "google": 4.3, "tiktok": 2.2, "youtube": 2.4}
    a = roas_proportional(roas, 1_000_000)
    assert sum(a.values()) == pytest.approx(1_000_000, abs=1.0)
    assert a["google"] == max(a.values())
    b = bayes_shrunk_proportional({"facebook": 300_000, "tiktok": 5_000},
                                  {"facebook": 100_000, "tiktok": 1_000},
                                  1_000_000, pseudo_spend=20_000)
    assert sum(b.values()) == pytest.approx(1_000_000, abs=1.0)
    # shrinkage tempers a tiny-sample lucky outlier: tiktok's raw ROAS of 5.0 rests on
    # just 1k spend, so its shrunk share must FALL below the naive ROAS-proportional one
    raw = roas_proportional({"facebook": 3.0, "tiktok": 5.0}, 1_000_000)
    assert b["tiktok"] / 1_000_000 < raw["tiktok"] / 1_000_000
