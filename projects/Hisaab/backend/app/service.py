"""High-level service operations shared by the API, the CLI and the dashboard."""
from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Dict

import pandas as pd

from .config import settings
from .db import save_dataset, get_dataset, save_recommendation
from .generator import write_parquet, write_csv, get_locale
from .metrics.aggregate import aggregate, clean, load, weekly_platform
from .recommender import (fit_all, bootstrap_curves, water_fill, expected_outcomes,
                          roas_proportional, bayes_shrunk_proportional)
from .metrics.formulas import derive
from .engines.base import SUM_COLS
from .sentiment import load_snapshot, platform_factors, product_board, apply_to_fits


def create_dataset(rows: int, locale: str = "pk", seed: int = 42,
                   with_csv: bool = True) -> dict:
    """Generate a dataset, register it, return its registry record."""
    if not (10 <= rows <= 20_000_000):
        raise ValueError("rows must be between 10 and 20,000,000")
    ds_id = f"{locale}_{rows}_{seed}"
    parquet_path = settings.data_dir / f"{ds_id}.parquet"
    csv_path = settings.data_dir / f"{ds_id}.csv"
    if parquet_path.exists():
        raise ValueError(f"dataset '{ds_id}' already exists")
    t0 = time.time()
    written = write_parquet(parquet_path, rows, locale, seed)
    csv_written = write_csv(csv_path, rows, locale, seed) if with_csv else 0
    rec = {
        "id": ds_id, "rows": written, "locale": locale, "seed": seed,
        "parquet_path": str(parquet_path),
        "csv_path": str(csv_path) if csv_written else "",
        "csv_rows": csv_written,
        "currency": get_locale(locale).currency,
        "generation_seconds": round(time.time() - t0, 2),
    }
    save_dataset(rec)
    return rec


def dataset_overview(ds_id: str, by: str = "platform") -> dict:
    """Clean + aggregate a dataset for the dashboard overview."""
    rec = get_dataset(ds_id)
    if not rec:
        raise ValueError(f"unknown dataset '{ds_id}'")
    df = load(rec["parquet_path"])
    n_raw = len(df)
    dfc = clean(df)
    groups = aggregate(dfc, by)
    total = {c: sum(g[c] for g in groups.values()) for c in SUM_COLS}
    return {
        "dataset": rec, "rows_raw": n_raw, "rows_clean": len(dfc),
        "duplicates_removed": n_raw - len(dfc),
        "totals": derive({**total, "rows": float(n_raw)}),
        "groups": groups,
        "currency": rec["currency"],
    }


def sentiment_summary() -> dict:
    """Voice-of-customer snapshot for the dashboard's Raye panel."""
    snap = load_snapshot()
    factors = platform_factors(snap, ["facebook", "instagram", "google", "tiktok", "youtube"])
    board = product_board(snap)
    return {
        "provenance": snap.provenance,
        "comments_total": snap.comments_total,
        "global": {"net_weighted": snap.global_.net_weighted, "n": snap.global_.n},
        "platforms": [vars(f) | {"net_weighted": f.net_weighted} for f in factors.values()],
        "products_top": board[:5],
        "products_risk": [r for r in board if r["flag"] == "risk"][:5],
        "languages": {"n": snap.languages.n, "by_sentiment": snap.languages.by_sentiment},
    }


def recommend_budget(ds_id: str, budget: float, with_ci: bool = True,
                     sentiment_aware: bool = False) -> dict:
    """The flagship: fit saturation curves, water-fill the budget, compare baselines.

    With sentiment_aware=True the allocation is re-optimised with Raye's brand-health
    multipliers applied to the curve scales (see app/sentiment/adjust.py) and both
    allocations are reported side by side.
    """
    rec = get_dataset(ds_id)
    if not rec:
        raise ValueError(f"unknown dataset '{ds_id}'")
    df = clean(load(rec["parquet_path"],
                    columns=["platform", "date", "spend", "revenue", "conversions"]))
    weekly = weekly_platform(df)
    fits = fit_all(weekly)

    # curve-fit sanity guard
    weak = [f.platform for f in fits if f.r2 < 0.5]
    warnings = []
    if weak:
        warnings.append(f"low curve fit (R² < 0.5) for: {', '.join(weak)} — treat those shares with care")

    alloc = water_fill(fits, budget)
    outcomes = expected_outcomes(fits, alloc)

    # baselines, evaluated under the SAME fitted curves → apples-to-apples
    platforms = sorted({f.platform for f in fits})
    l0 = {p: budget / len(platforms) for p in platforms}          # the gut-feel default
    by_platform = weekly.groupby("platform")[["spend", "revenue"]].sum()
    roas_avg = (by_platform["revenue"] / by_platform["spend"]).replace([float("inf")], 0).to_dict()
    l1 = roas_proportional({k: float(v) for k, v in roas_avg.items()}, budget)
    pseudo = max(1.0, 0.05 * float(by_platform["spend"].median()))
    l2 = bayes_shrunk_proportional({k: float(v) for k, v in by_platform["revenue"].items()},
                                   {k: float(v) for k, v in by_platform["spend"].items()},
                                   budget, pseudo)

    def incremental(a: Dict[str, float]) -> float:
        return round(sum(max(0.0, f.predict(a.get(f.platform, 0.0)) - f.intercept)
                         for f in fits), 2)

    ci = bootstrap_curves(weekly, settings.bootstrap_resamples) if with_ci else {}

    result = {
        "dataset": ds_id,
        "currency": rec["currency"],
        "budget": budget,
        "weekly_points": int(len(weekly)),
        "allocation": [
            {"platform": p, **outcomes[p],
             "share_pct": round(100 * outcomes[p]["allocated"] / budget, 1) if budget else 0.0,
             "alpha_ci": ci.get(p, {}).get("alpha_ci"),
             "beta_ci": ci.get(p, {}).get("beta_ci")}
            for p in sorted(outcomes, key=lambda p: -outcomes[p]["allocated"])
        ],
        "expected_incremental_revenue": incremental(alloc),
        "blended_incremental_roas": round(incremental(alloc) / budget, 3) if budget else 0.0,
        "baselines": {
            "l0_equal_split": {"allocation": l0, "expected_incremental_revenue": incremental(l0)},
            "l1_roas_proportional": {"allocation": l1, "expected_incremental_revenue": incremental(l1)},
            "l2_bayes_shrunk": {"allocation": l2, "expected_incremental_revenue": incremental(l2)},
        },
        "warnings": warnings,
        "method": ("Per-platform revenue response fitted as R(s)=a·ln(1+s/β)+c on weekly "
                   "aggregates; budget allocated by equalizing marginal returns "
                   "(water-filling). Baselines scored under the same curves."),
    }

    if sentiment_aware:
        try:
            snap = load_snapshot()
        except FileNotFoundError:
            result["warnings"].append(
                "sentiment_aware requested but Raye aggregates missing — run "
                "scripts/export_raye.py; returning performance-only allocation")
        else:
            platforms = sorted({f.platform for f in fits})
            factors = platform_factors(snap, platforms)
            fits_s = apply_to_fits(fits, factors)
            alloc_s = water_fill(fits_s, budget)
            outcomes_s = expected_outcomes(fits_s, alloc_s)
            inc_s = incremental(alloc_s)
            inc_base = result["expected_incremental_revenue"]
            result["sentiment"] = {
                "enabled": True,
                "source": snap.provenance.get("source_project", "Raye"),
                "comments_total": snap.comments_total,
                "global_brand_health": snap.global_.net_weighted,
                "platforms": [vars(factors[p]) for p in platforms],
                "allocation": [
                    {"platform": p,
                     "allocated": outcomes_s[p]["allocated"],
                     "share_pct": round(100 * outcomes_s[p]["allocated"] / budget, 1) if budget else 0.0,
                     "expected_incremental_revenue": outcomes_s[p]["expected_incremental_revenue"],
                     "factor": factors[p].factor}
                    for p in sorted(outcomes_s, key=lambda p: -outcomes_s[p]["allocated"])
                ],
                "expected_incremental_revenue": inc_s,
                "revenue_delta_vs_l3": round(inc_s - inc_base, 2),
                "note": ("Curve scales aᵢ multiplied by sentiment factors before water-"
                         "filling; expected revenues above are scored under the ORIGINAL "
                         "fitted curves for comparability."),
            }
            result["method"] += (" Sentiment overlay: Raye brand-health multipliers on aᵢ "
                                "(see /api/sentiment/summary).")

    save_recommendation(result)
    return result
