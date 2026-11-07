"""All engines must agree on the raw sums — the benchmark's correctness bedrock.

Engines deliberately return RAW sums (no cleaning): cleaning is a separate, shared
pre-processing step in the metrics layer, so engine equivalence is exact.
"""
import pytest

from app.generator import write_parquet, write_csv
from app.metrics.aggregate import aggregate, load
from app.engines.base import SUM_COLS
from app.engines import ENGINE_CLASSES

ROWS = 12_000
PARQUET = None
CSV = None


def setup_module(module):
    global PARQUET, CSV
    from pathlib import Path
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="hisaab-engines-"))
    PARQUET = str(tmp / "eng.parquet")
    CSV = str(tmp / "eng.csv")
    write_parquet(PARQUET, ROWS, "pk", seed=11)
    write_csv(CSV, ROWS, "pk", seed=11)


def _norm(d):
    return {k: {m: round(float(v), 2) for m, v in s.items()} for k, s in d.items()}


def test_pandas_reference():
    df = load(PARQUET, columns=["platform", "impressions", "clicks", "spend",
                                "conversions", "revenue"])
    ref = _norm(aggregate(df))
    ref = {p: {m: v for m, v in s.items() if m in SUM_COLS}      # engines return raw sums only
           for p, s in ref.items()}
    assert ref and len(ref) == 5
    return ref


def test_all_engines_match_pandas_reference():
    ref = test_pandas_reference()
    for name in ("pandas", "polars", "mapreduce"):
        cls = ENGINE_CLASSES[name]
        ok, reason = cls.available()
        if not ok:
            pytest.skip(reason)
        eng = cls()
        path = CSV if name == "mapreduce" else PARQUET
        got = _norm(eng.run(path, ROWS))
        for platform, sums in ref.items():
            assert platform in got, f"{name}: missing platform {platform}"
            for metric, v in sums.items():
                if metric in ("impressions", "clicks", "conversions"):
                    assert abs(got[platform][metric] - v) < 1.0, \
                        f"{name}/{platform}/{metric}: {got[platform][metric]} != {v}"
                else:
                    assert abs(got[platform][metric] - v) < max(1.0, v * 1e-6), \
                        f"{name}/{platform}/{metric}: {got[platform][metric]} != {v}"


def test_spark_engine_if_available():
    cls = ENGINE_CLASSES["spark"]
    ok, reason = cls.available()
    if not ok:
        pytest.skip(reason)
    got = _norm(cls().run(PARQUET, ROWS))
    ref = test_pandas_reference()
    for platform, sums in ref.items():
        for metric, v in sums.items():
            assert abs(got[platform][metric] - v) < max(1.0, v * 1e-6)


def test_mapreduce_parallel_matches_single():
    single = _norm(ENGINE_CLASSES["mapreduce"]().run(CSV, ROWS))
    par = _norm(ENGINE_CLASSES["mapreduce"](procs=2).run(CSV, ROWS))
    assert single.keys() == par.keys()
    for p in single:
        for m in single[p]:
            assert abs(single[p][m] - par[p][m]) < 1.0
