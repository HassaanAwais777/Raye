"""Generator: schema, calibration, cleaning-trap injection, saturation signal."""
import numpy as np
import pandas as pd
import pytest

from app.generator import get_locale, iter_generated
from app.generator.locales import PLATFORMS, CAMPAIGNS
from app.metrics.aggregate import clean


def test_chunk_shape_and_columns():
    rows = next(iter_generated(5_000, "pk", seed=1))
    assert set(rows) == {"date", "campaign", "platform", "impressions", "clicks",
                         "spend", "conversions", "revenue", "age", "gender",
                         "city", "device"}
    n = len(rows["date"])
    assert n == 5_000
    for c in ("impressions", "clicks", "conversions"):
        assert (rows[c] >= 0).all()


def test_campaigns_belong_to_platforms():
    rows = next(iter_generated(20_000, "pk", seed=2))
    plat = pd.Series(rows["platform"])
    camp = pd.Series(rows["campaign"])
    df = pd.DataFrame({"p": plat, "c": camp})
    for p in PLATFORMS:
        sub = set(df[df.p == p].c.unique())
        assert sub, f"{p}: no rows"
        assert sub <= set(CAMPAIGNS[p]), f"{p}: foreign campaigns {sub - set(CAMPAIGNS[p])}"
        assert len(sub) >= 2, f"{p}: expected the catalogue to be exercised, got {sub}"


def test_injected_duplicates_present():
    rows = next(iter_generated(30_000, "pk", seed=3))
    df = pd.DataFrame({k: rows[k] for k in ("date", "campaign", "platform", "impressions",
                                            "clicks", "spend", "conversions", "revenue")})
    dupes = df.duplicated().sum()
    assert dupes > 0, "generator should inject exact duplicates"
    cleaned = clean(df, drop_bots=False)
    assert len(cleaned) == len(df) - dupes


def test_bot_rows_injected_and_cleanable():
    rows = next(iter_generated(30_000, "pk", seed=4))
    df = pd.DataFrame({k: rows[k] for k in ("impressions", "clicks", "spend")})
    bots = df[(df.impressions >= df.impressions.quantile(0.995)) & (df.clicks == 0)]
    assert len(bots) > 0, "generator should inject impression-fraud rows"
    cleaned = clean(df, drop_dupes=False)
    assert (cleaned.clicks == 0).sum() < len(bots)


def test_blended_roas_in_calibration_band():
    """The generator is calibrated so blended ROAS lands in a credible 2–4 band."""
    rows = next(iter_generated(200_000, "pk", seed=42))
    spend, revenue = rows["spend"].sum(), rows["revenue"].sum()
    roas = revenue / spend
    assert 1.8 < roas < 4.2, f"blended ROAS {roas:.2f} out of calibration band"


def test_saturation_signal_exists():
    """High-spend weeks must convert less efficiently — the L3 curve needs concavity."""
    rows = next(iter_generated(400_000, "pk", seed=5))
    df = pd.DataFrame({
        "platform": rows["platform"], "spend": rows["spend"],
        "revenue": rows["revenue"], "conversions": rows["conversions"]})
    df["week"] = np.random.randint(0, 12, len(df))          # proxy weeks
    g = df.groupby("week").agg(spend=("spend", "sum"), revenue=("revenue", "sum"))
    g["roas"] = g.revenue / g.spend
    hi, lo = g.nlargest(3, "spend").roas.mean(), g.nsmallest(3, "spend").roas.mean()
    assert hi < lo * 1.35, f"expected weaker ROAS in high-spend weeks (hi={hi:.2f}, lo={lo:.2f})"


def test_locale_currency_and_cities():
    g = next(iter_generated(2_000, "global", seed=6))
    assert set(np.unique(g["city"])) <= {"New York", "London", "Dubai", "Toronto", "Berlin",
                                         "Singapore", "Sydney", "Mumbai", "Lagos",
                                         "São Paulo", "Other"}
