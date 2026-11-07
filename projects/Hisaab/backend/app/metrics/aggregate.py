"""Cleaning + aggregation on top of pandas — the reference implementation that
engines are compared against and the dashboard's fast path."""
import pandas as pd

from .formulas import derive

NUMERIC = ("impressions", "clicks", "spend", "conversions", "revenue")
GROUP_COLS = ("platform", "campaign", "city", "device", "age", "gender")


def load(path, columns=None) -> pd.DataFrame:
    return pd.read_parquet(path, columns=columns)


def clean(df: pd.DataFrame, drop_dupes: bool = True, drop_bots: bool = True) -> pd.DataFrame:
    """Documented cleaning policy:
    - drop exact duplicates (the generator injects ~0.5%)
    - drop impression-fraud rows: top 0.5% impressions AND zero clicks (the ~1% bot trap)
    - clip impossible negatives
    Tolerates partial column sets (dashboards may load only the metrics slice).
    """
    df = df.copy()
    if drop_dupes:
        subset = [c for c in CLEAN_SUBSET if c in df.columns]
        df = df.drop_duplicates(subset=subset or None)
    if drop_bots and {"impressions", "clicks"} <= set(df.columns) and len(df):
        thresh = df["impressions"].quantile(0.995)
        mask = (df["impressions"] >= thresh) & (df["clicks"] == 0)
        df = df[~mask]
    for c in NUMERIC:
        if c in df.columns:
            df[c] = df[c].clip(lower=0)
    return df


CLEAN_SUBSET = ("date", "campaign", "platform", "impressions", "clicks", "spend",
                "conversions", "revenue", "age", "gender", "city", "device")


def aggregate(df: pd.DataFrame, by: str = "platform") -> dict:
    """Sum raw metrics per group and attach derived ratios. Returns {group: sums}."""
    g = df.groupby(by, observed=True)[list(NUMERIC)].sum()
    out = {}
    for key, row in g.iterrows():
        out[str(key)] = derive({m: float(row[m]) for m in NUMERIC} | {"rows": 0})
    return out


def weekly_platform(df: pd.DataFrame) -> pd.DataFrame:
    """Weekly spend/revenue per platform — the points the response curves are fitted on."""
    d = df.copy()
    d["week"] = pd.to_datetime(d["date"]).dt.to_period("W").astype(str)
    g = d.groupby(["platform", "week"], observed=True)[["spend", "revenue", "conversions"]].sum()
    return g.reset_index()
