"""Metric formula correctness — the numbers every stakeholder quotes."""
import pytest

from app.metrics.formulas import ctr, cpc, cpa, cvr, roas, safe_div, derive


def test_safe_div_handles_zero():
    assert safe_div(10, 0) == 0.0
    assert safe_div(10, 2) == 5.0


def test_ctr():
    assert ctr(50, 10_000) == pytest.approx(0.005)


def test_cpc_cpa_cvr_roas():
    assert cpc(220, 10) == pytest.approx(22.0)
    assert cpa(300, 4) == pytest.approx(75.0)
    assert cvr(4, 200) == pytest.approx(0.02)
    assert roas(8000, 2000) == pytest.approx(4.0)


def test_derive_attaches_all_ratios():
    out = derive({"impressions": 1000, "clicks": 20, "spend": 400,
                  "conversions": 2, "revenue": 1200, "rows": 1})
    assert out["ctr"] == pytest.approx(0.02)
    assert out["cpc"] == pytest.approx(20.0)
    assert out["cpa"] == pytest.approx(200.0)
    assert out["cvr"] == pytest.approx(0.1)
    assert out["roas"] == pytest.approx(3.0)


def test_derive_never_explodes_on_zero():
    out = derive({"impressions": 0, "clicks": 0, "spend": 0,
                  "conversions": 0, "revenue": 0, "rows": 0})
    assert out["cpc"] == 0.0 and out["cpa"] == 0.0 and out["roas"] == 0.0
