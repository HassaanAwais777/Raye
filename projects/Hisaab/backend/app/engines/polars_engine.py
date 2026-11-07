"""Polars engine — the modern columnar DataFrame engine (multi-threaded, Rust)."""
from .base import Engine, SUM_COLS


class PolarsEngine(Engine):
    name = "polars"
    label = "Polars"
    source_format = "parquet"
    parallelism = "multi-threaded (all cores)"

    @classmethod
    def available(cls):
        try:
            import polars  # noqa: F401
            return True, ""
        except ImportError:
            return False, "polars not installed (pip install polars)"

    def run(self, dataset_path: str, rows_hint: int = 0):
        import polars as pl
        df = pl.read_parquet(dataset_path, columns=["platform", *SUM_COLS])
        g = (df.group_by("platform")
               .agg([pl.col(c).sum() for c in SUM_COLS])
               .sort("platform"))
        return {row["platform"]: {c: float(row[c]) for c in SUM_COLS}
                for row in g.iter_rows(named=True)}
