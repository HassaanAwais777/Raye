"""Metric formulas — the shared vocabulary of the whole project.

Every engine returns RAW SUMS (impressions, clicks, spend, conversions, revenue, rows);
derived ratios are computed here and only here, so engine-agreement tests compare
integers/sums, and every dashboard number traces to one auditable formula.
"""
from typing import Dict, Union

Number = Union[int, float]


def safe_div(a: Number, b: Number) -> float:
    """Division that refuses to explode: 0 when the denominator is 0."""
    return float(a) / float(b) if b else 0.0


def ctr(clicks: Number, impressions: Number) -> float:
    """Click-through rate = clicks / impressions."""
    return safe_div(clicks, impressions)


def cpc(spend: Number, clicks: Number) -> float:
    """Cost per click = spend / clicks."""
    return safe_div(spend, clicks)


def cpa(spend: Number, conversions: Number) -> float:
    """Cost per acquisition = spend / conversions."""
    return safe_div(spend, conversions)


def cvr(conversions: Number, clicks: Number) -> float:
    """Conversion rate = conversions / clicks."""
    return safe_div(conversions, clicks)


def roas(revenue: Number, spend: Number) -> float:
    """Return on ad spend = revenue / spend (e.g. 3.2 → Rs. 3.20 back per Rs. 1)."""
    return safe_div(revenue, spend)


def derive(sums: Dict[str, float]) -> Dict[str, float]:
    """Attach all derived metrics to a dict of raw sums."""
    s = dict(sums)
    s["ctr"] = round(ctr(s.get("clicks", 0), s.get("impressions", 0)), 6)
    s["cpc"] = round(cpc(s.get("spend", 0), s.get("clicks", 0)), 4)
    s["cpa"] = round(cpa(s.get("spend", 0), s.get("conversions", 0)), 2)
    s["cvr"] = round(cvr(s.get("conversions", 0), s.get("clicks", 0)), 6)
    s["roas"] = round(roas(s.get("revenue", 0), s.get("spend", 0)), 4)
    return s
