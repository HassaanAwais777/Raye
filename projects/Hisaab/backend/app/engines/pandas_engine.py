"""Pandas engine — the familiar baseline."""
from .base import Engine, SUM_COLS


class PandasEngine(Engine):
    name = "pandas"
    label = "Pandas"
    source_format = "parquet"
    parallelism = "single-core"

    def run(self, dataset_path: str, rows_hint: int = 0):
        import pandas as pd
        df = pd.read_parquet(dataset_path, columns=["platform", *SUM_COLS])
        g = df.groupby("platform", observed=True)[list(SUM_COLS)].sum()
        return {str(k): {c: float(v) for c, v in row.items()} for k, row in g.iterrows()}
