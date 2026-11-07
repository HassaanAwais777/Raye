"""Loading Raye's sentiment export into typed snapshots.

Two paths:
  1. JSON fast path (default): `raye_sentiment_aggregates.json` produced by
     scripts/export_raye.py — a few KB, loads instantly, committed to the repo.
  2. CSV path: recompute aggregates from `raye_sentiment_full.csv` (210k rows) —
     used by tests to prove the JSON aggregates really match the raw export.

Brand health definition (documented in the JSON provenance block):
  net           = plain mean of Raye's per-comment score in [-1, 1]
  net_weighted  = likes-weighted mean score — the *engagement-weighted voice*;
                  comments people actually saw count more. weight = likes + 1.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd


@dataclass
class BrandHealth:
    key: str
    n: int
    net: float
    net_weighted: float
    by_sentiment: Dict[str, int] = field(default_factory=dict)
    likes: int = 0


@dataclass
class ProductHealth(BrandHealth):
    name: str = ""
    category: str = ""


@dataclass
class SentimentSnapshot:
    global_: BrandHealth
    platforms: Dict[str, BrandHealth]
    products: List[ProductHealth]
    languages: BrandHealth
    provenance: dict
    source: str

    @property
    def comments_total(self) -> int:
        return self.global_.n


def _brand(key: str, d: dict) -> BrandHealth:
    return BrandHealth(key=d.get("key", key), n=int(d.get("n", 0)),
                       net=float(d.get("net", 0.0)),
                       net_weighted=float(d.get("net_weighted", 0.0)),
                       by_sentiment={k: int(v) for k, v in d.get("by_sentiment", {}).items()},
                       likes=int(d.get("likes", 0)))


def _default_path() -> Path:
    from ..config import settings
    return settings.raye_dir / "raye_sentiment_aggregates.json"


def load_snapshot(path: Optional[Path] = None) -> SentimentSnapshot:
    """Load the aggregates JSON (fast path). Raises FileNotFoundError if absent."""
    p = Path(path) if path else _default_path()
    if not p.exists():
        raise FileNotFoundError(
            f"Raye aggregates not found at {p} — run scripts/export_raye.py first")
    d = json.loads(p.read_text(encoding="utf-8"))
    platforms = {k: _brand(k, v) for k, v in d.get("platforms", {}).items()}
    products = []
    for pd_ in d.get("products", []):
        ph = ProductHealth(key=pd_.get("key", pd_["slug"]),
                           n=int(pd_.get("n", 0)), net=float(pd_.get("net", 0.0)),
                           net_weighted=float(pd_.get("net_weighted", 0.0)),
                           by_sentiment={k: int(v) for k, v in pd_.get("by_sentiment", {}).items()},
                           likes=int(pd_.get("likes", 0)))
        ph.name = pd_.get("name", "")
        ph.category = pd_.get("category", "")
        products.append(ph)
    return SentimentSnapshot(
        global_=_brand("global", d.get("global", {})),
        platforms=platforms,
        products=products,
        languages=_brand("languages", d.get("languages", {})),
        provenance=d.get("provenance", {}),
        source=str(p),
    )


def aggregate_from_csv(path: Path) -> SentimentSnapshot:
    """Recompute aggregates from a raw export CSV — proves the JSON matches the data."""
    df = pd.read_csv(path)

    def stats(sub: pd.DataFrame) -> dict:
        n = len(sub)
        if n == 0:
            return {"n": 0, "net": 0.0, "net_weighted": 0.0, "by_sentiment": {}, "likes": 0}
        w = sub["likes"] + 1
        return {
            "n": int(n),
            "net": round(float(sub["score"].mean()), 4),
            "net_weighted": round(float((sub["score"] * w).sum() / w.sum()), 4),
            "by_sentiment": {k: int(v) for k, v in sub["sentiment"].value_counts().items()},
            "likes": int(sub["likes"].sum()),
        }

    platforms = {p: stats(g) for p, g in df.groupby("platform")}
    products = []
    for slug, g in df.groupby("product_slug"):
        st = stats(g)
        products.append(ProductHealth(key=slug, name=slug, category="",
                                      n=st["n"], net=st["net"],
                                      net_weighted=st["net_weighted"],
                                      by_sentiment=st["by_sentiment"], likes=st["likes"]))
    products.sort(key=lambda h: -h.n)
    return SentimentSnapshot(
        global_=_brand("global", stats(df)),
        platforms={k: _brand(k, v) for k, v in platforms.items()},
        products=products,
        languages=_brand("languages", stats(df)),
        provenance={"source_db": str(path), "recomputed": True},
        source=str(path),
    )
