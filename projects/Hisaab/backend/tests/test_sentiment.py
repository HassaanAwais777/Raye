"""Sentiment bridge: aggregation math, factor properties, Raye-export validation,
and the end-to-end sentiment-aware recommendation."""
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.sentiment.bridge import BrandHealth, SentimentSnapshot, load_snapshot, aggregate_from_csv
from app.sentiment.adjust import (EVIDENCE, PlatformSentiment, platform_factors,
                                  product_board, apply_to_fits, DEFAULT_CAP)
from app.recommender.curves import fit_curve
from app.recommender.allocate import water_fill

RAYE_DIR = Path(__file__).resolve().parents[1] / "data" / "raye"
AGGS = RAYE_DIR / "raye_sentiment_aggregates.json"
FULL = RAYE_DIR / "raye_sentiment_full.csv"

needs_aggs = pytest.mark.skipif(not AGGS.exists(), reason="raye aggregates not exported yet")


# ---------------------------------------------------------------- fixtures ----
def _snapshot(platform_health: dict, global_health: dict = None) -> SentimentSnapshot:
    """Hand-built snapshot for property tests (no dependency on exported data)."""
    gh = global_health or {"key": "global", "n": 1000, "net": 0.2, "net_weighted": 0.2,
                           "by_sentiment": {}, "likes": 0}
    plats = {k: BrandHealth(key=k, **v) for k, v in platform_health.items()}
    return SentimentSnapshot(global_=BrandHealth(**gh), platforms=plats,
                             products=[], languages=BrandHealth(key="lang", n=0, net=0.0,
                                                                net_weighted=0.0),
                             provenance={"source_project": "test"}, source="fixture")


# ------------------------------------------------------------ aggregation ----
def test_brand_health_likes_weighting(tmp_path):
    """net_weighted must weight comments by likes+1: liked comments dominate."""
    df = pd.DataFrame({
        "platform": ["youtube"] * 3, "product_slug": ["p"] * 3, "lang": ["en"] * 3,
        "sentiment": ["positive", "negative", "neutral"],
        "score": [0.9, -0.9, 0.0],
        "confidence": [1.0, 1.0, 1.0],
        "likes": [100, 0, 0],
        "posted_at": [0, 0, 0],
    })
    p = tmp_path / "exp.csv"
    df.to_csv(p, index=False)
    snap = aggregate_from_csv(p)
    # weights: 101, 1, 1 → weighted mean = (0.9*101 − 0.9) / 103
    expected = (0.9 * 101 - 0.9) / 103
    assert snap.global_.net_weighted == pytest.approx(expected, abs=1e-4)
    assert snap.global_.n == 3


# ---------------------------------------------------------- factor maths -----
def test_factors_within_cap_and_unmeasured_neutral():
    snap = _snapshot({
        "youtube": {"n": 177_234, "net": 0.2, "net_weighted": 0.9, "by_sentiment": {}, "likes": 0},
        "reddit": {"n": 33_277, "net": 0.2, "net_weighted": -0.5, "by_sentiment": {}, "likes": 0},
    })
    factors = platform_factors(snap, ["youtube", "google", "facebook", "tiktok"])
    for f in factors.values():
        assert 1 - DEFAULT_CAP <= f.factor <= 1 + DEFAULT_CAP
    # measured surfaces drive their ad-platform mapping
    assert factors["youtube"].factor > 1.0          # very positive voice
    assert factors["google"].factor < 1.0           # reddit proxy, negative voice
    # unmeasured surfaces → global fallback, zero deviation, factor exactly 1.0
    assert factors["facebook"].factor == 1.0
    assert factors["facebook"].evidence == "-"
    assert factors["tiktok"].factor == 1.0


def test_factor_monotone_in_sentiment():
    """Holding everything else fixed, better voice ⇒ higher factor."""
    plat = {"s": {"n": 100_000, "net": 0.0, "net_weighted": 0.0, "by_sentiment": {}, "likes": 0}}
    factors = []
    for voice in (-0.6, -0.2, 0.0, 0.2, 0.6):
        plat["s"]["net_weighted"] = voice
        snap = _snapshot(plat, {"key": "global", "n": 100_000, "net": 0.0,
                                "net_weighted": 0.0, "by_sentiment": {}, "likes": 0})
        # map "s" onto the youtube slot to exercise a direct-measurement path
        EVIDENCE["__test"] = {"evidence": "s", "proxy_weight": 1.0}
        try:
            factors.append(platform_factors(snap, ["__test"])["__test"].factor)
        finally:
            EVIDENCE.pop("__test")
    assert factors == sorted(factors)
    assert factors[0] < 1.0 < factors[-1]


def test_shrinkage_pulls_small_samples_to_global():
    """A 100-comment surface cannot move its factor much — confidence shrinkage."""
    snap_lo = _snapshot({
        "youtube": {"n": 100, "net": 0.0, "net_weighted": 0.9, "by_sentiment": {}, "likes": 0}})
    snap_hi = _snapshot({
        "youtube": {"n": 500_000, "net": 0.0, "net_weighted": 0.9, "by_sentiment": {}, "likes": 0}})
    f_lo = platform_factors(snap_lo, ["youtube"])["youtube"].factor
    f_hi = platform_factors(snap_hi, ["youtube"])["youtube"].factor
    assert abs(f_lo - 1.0) < abs(f_hi - 1.0)        # small n → smaller nudge


def test_apply_to_fits_scales_alpha_only():
    fit = fit_curve("youtube", *np.array([[10_000, 30_000, 90_000, 200_000],
                                          [40_000, 95_000, 210_000, 330_000.]]))
    fac = {"youtube": PlatformSentiment("youtube", "youtube", 1000, 0.5, 0.05, 1.10)}
    adjusted = apply_to_fits([fit], fac)[0]
    assert adjusted.alpha == pytest.approx(fit.alpha * 1.10)
    assert adjusted.beta == fit.beta and adjusted.r2 == fit.r2


# ------------------------------------------------- end-to-end water-filling ---
def test_sentiment_shifts_budget_toward_healthier_platform():
    """Equal performance curves + different sentiment ⇒ budget flows to the healthy one."""
    s = np.array([[10_000, 30_000, 90_000, 200_000, 400_000],
                  [10_000, 30_000, 90_000, 200_000, 400_000.]]).T
    r = s * 2.5                                        # identical linear-ish responses
    fits = [fit_curve("youtube", s[:, 0], s[:, 1] * 2.5),
            fit_curve("facebook", s[:, 0], s[:, 1] * 2.5)]
    snap = _snapshot({
        "youtube": {"n": 400_000, "net": 0.0, "net_weighted": 0.6, "by_sentiment": {}, "likes": 0}},
        {"key": "global", "n": 400_000, "net": 0.0, "net_weighted": 0.0,
         "by_sentiment": {}, "likes": 0})
    factors = platform_factors(snap, ["youtube", "facebook"])
    fits_s = apply_to_fits(fits, factors)
    base = water_fill(fits, 1_000_000)
    overlay = water_fill(fits_s, 1_000_000)
    assert base["youtube"] == pytest.approx(base["facebook"], rel=0.01)   # symmetric start
    assert overlay["youtube"] > overlay["facebook"]                        # sentiment breaks the tie
    assert sum(overlay.values()) == pytest.approx(1_000_000, abs=1.0)


# ------------------------------------------------- real Raye export checks ---
@needs_aggs
def test_raye_aggregates_are_consistent():
    d = json.loads(AGGS.read_text(encoding="utf-8"))
    assert d["global"]["n"] == sum(p["n"] for p in d["platforms"].values())
    assert d["global"]["n"] == sum(p["n"] for p in d["products"])
    assert d["provenance"]["comments_total"] == d["global"]["n"]


@needs_aggs
def test_raye_snapshot_matches_full_export():
    """The committed JSON must equal aggregates recomputed from the 210k-row CSV."""
    if not FULL.exists():
        pytest.skip("full export not present (optional artefact)")
    from_json = load_snapshot(AGGS)
    from_csv = aggregate_from_csv(FULL)
    assert from_json.global_.n == from_csv.global_.n
    for p, st in from_csv.platforms.items():
        assert from_json.platforms[p].net_weighted == pytest.approx(st.net_weighted, abs=1e-3)
    for pr in from_csv.products:
        match = next(x for x in from_json.products if x.key == pr.key)
        assert match.net_weighted == pytest.approx(pr.net_weighted, abs=1e-3)


@needs_aggs
def test_raye_real_factors_are_mild():
    """Raye's corpus has a uniform platform voice: real factors must stay within ±3%.

    This is the honesty guarantee — the overlay nudges, it does not hijack.
    """
    snap = load_snapshot(AGGS)
    factors = platform_factors(snap, ["facebook", "instagram", "google", "tiktok", "youtube"])
    for f in factors.values():
        assert abs(f.factor - 1.0) <= 0.03, f
    # the product board is where the corpus differentiates: spread must exceed 0.3
    board = product_board(snap)
    board = [r for r in board if r["n_comments"] >= 1000]
    assert max(r["net_shrunk"] for r in board) - min(r["net_shrunk"] for r in board) > 0.3
    # and the known laggards must be flagged as risk
    flags = {r["slug"]: r["flag"] for r in board}
    assert flags.get("tecno-spark-10") == "risk"


# --------------------------------------------------- service integration ----
@needs_aggs
def test_recommend_with_sentiment_overlay(dataset_service):
    ds_id = dataset_service
    from app.service import recommend_budget
    out = recommend_budget(ds_id, 1_000_000, with_ci=False, sentiment_aware=True)
    assert "sentiment" in out
    s = out["sentiment"]
    assert s["comments_total"] == 210_511
    alloc = {a["platform"]: a["allocated"] for a in s["allocation"]}
    assert sum(alloc.values()) == pytest.approx(1_000_000, abs=1.0)
    # overlay revenue reported under original curves, delta computed
    assert s["revenue_delta_vs_l3"] == pytest.approx(
        s["expected_incremental_revenue"] - out["expected_incremental_revenue"], abs=0.51)
    # performance-only block unchanged
    assert out["expected_incremental_revenue"] > 0
    # method note mentions the overlay
    assert "Sentiment overlay" in out["method"]


@pytest.fixture(scope="module")
def dataset_service(tmp_path_factory):
    from app.config import settings
    from app.service import create_dataset
    tmp = tmp_path_factory.mktemp("hisaab-sent")
    settings.data_dir = tmp
    settings.db_path = tmp / "test.db"
    settings.bootstrap_resamples = 40
    return create_dataset(60_000, "pk", seed=42, with_csv=False)["id"]
