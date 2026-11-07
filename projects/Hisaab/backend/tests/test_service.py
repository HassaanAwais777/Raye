"""End-to-end: generate → recommend on a real (small) dataset; result invariants."""
import pytest

from app.service import create_dataset, recommend_budget


@pytest.fixture(scope="module")
def dataset(tmp_path_factory):
    # NOTE: module-scoped fixture — plain assignment instead of function-scoped
    # monkeypatch (ScopeMismatch). Pointing settings at a throwaway dir is fine to
    # keep for the rest of the test session.
    from app.config import settings
    tmp = tmp_path_factory.mktemp("hisaab-data")
    settings.data_dir = tmp
    settings.db_path = tmp / "test.db"
    settings.bootstrap_resamples = 40
    return create_dataset(60_000, "pk", seed=42, with_csv=False)


def test_recommend_result_shape(dataset):
    out = recommend_budget(dataset["id"], 1_000_000, with_ci=True)
    assert out["currency"] == "PKR"
    alloc = {a["platform"]: a["allocated"] for a in out["allocation"]}
    assert sum(alloc.values()) == pytest.approx(1_000_000, abs=1.0)
    assert len(alloc) == 5
    shares = {a["platform"]: a["share_pct"] for a in out["allocation"]}
    assert sum(shares.values()) == pytest.approx(100.0, abs=0.5)
    # every platform's expected incremental revenue is consistent with its curve
    for a in out["allocation"]:
        assert a["expected_incremental_revenue"] >= 0
        assert a["marginal_roas"] >= 0
    # L3 beats (or matches) both baselines under the same curves
    l3 = out["expected_incremental_revenue"]
    l1 = out["baselines"]["l1_roas_proportional"]["expected_incremental_revenue"]
    l2 = out["baselines"]["l2_bayes_shrunk"]["expected_incremental_revenue"]
    assert l3 >= l1 - 1e-6 and l3 >= l2 - 1e-6, (l3, l1, l2)


def test_bigger_budget_never_lower_returns(dataset):
    small = recommend_budget(dataset["id"], 300_000, with_ci=False)
    big = recommend_budget(dataset["id"], 2_000_000, with_ci=False)
    assert big["expected_incremental_revenue"] > small["expected_incremental_revenue"]
    # marginal efficiency falls as budget grows (diminishing returns)
    assert big["blended_incremental_roas"] < small["blended_incremental_roas"]
