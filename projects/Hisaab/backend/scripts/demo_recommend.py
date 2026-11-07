"""End-to-end demo: 1M-row dataset → sentiment-aware recommendation.

Produces the numbers quoted in README/docs: allocation, factors, baselines,
Raye overlay effect. Run:  PYTHONPATH=. python scripts/demo_recommend.py
"""
import json
import sys
import time

from app.service import create_dataset, recommend_budget
from app.config import settings


def main() -> int:
    rows = int(sys.argv[1]) if len(sys.argv) > 1 else 1_000_000
    t0 = time.time()
    try:
        rec = create_dataset(rows, "pk", seed=42, with_csv=True)
    except ValueError as e:
        print(f"dataset exists: {e} — reusing")
        from app.db import get_dataset
        rec = get_dataset(f"pk_{rows}_42")
    print(f"dataset ready: {rec['id']} ({rec['rows']:,} rows, "
          f"generated in {rec['generation_seconds']}s)")

    t1 = time.time()
    out = recommend_budget(rec["id"], settings.default_budget, with_ci=True,
                           sentiment_aware=True)
    elapsed = time.time() - t1

    print(f"\n=== recommendation ({elapsed:.1f}s, {out['weekly_points']} weekly points) ===")
    hdr = f"{'platform':10s} {'L3 alloc':>12s} {'share':>7s} {'+Raye':>12s} {'share':>7s} {'factor':>7s}"
    print(hdr)
    sent = {a["platform"]: a for a in out["sentiment"]["allocation"]}
    facs = {p["platform"]: p["factor"] for p in out["sentiment"]["platforms"]}
    for a in out["allocation"]:
        p = a["platform"]
        s = sent.get(p, {})
        print(f"{p:10s} {a['allocated']:>12,.0f} {a['share_pct']:>6.1f}% "
              f"{s.get('allocated', 0):>12,.0f} {s.get('share_pct', 0):>6.1f}% "
              f"{facs.get(p, 1.0):>7.4f}")

    print(f"\nL3 expected incremental revenue : {out['expected_incremental_revenue']:>14,.0f} "
          f"{rec['currency']}")
    print(f"L3+Raye expected incremental    : "
          f"{out['sentiment']['expected_incremental_revenue']:>14,.0f} "
          f"({out['sentiment']['revenue_delta_vs_l3']:+,.0f} vs L3, "
          f"scored under original curves)")
    for k, v in out["baselines"].items():
        print(f"{k:32s}: {v['expected_incremental_revenue']:>14,.0f}")
    print(f"\nglobal brand health: {out['sentiment']['global_brand_health']:+.4f} "
          f"from {out['sentiment']['comments_total']:,} Raye comments")
    if out["warnings"]:
        print("warnings:", *out["warnings"], sep="\n  ")

    # persist for docs
    slim = {
        "dataset": out["dataset"], "budget": out["budget"],
        "weekly_points": out["weekly_points"],
        "l3": [{"platform": a["platform"], "allocated": a["allocated"],
                "share_pct": a["share_pct"], "marginal_roas": a["marginal_roas"],
                "curve_alpha": a["curve_alpha"], "curve_beta": a["curve_beta"],
                "curve_r2": a["curve_r2"]} for a in out["allocation"]],
        "l3_sentiment": out["sentiment"]["allocation"],
        "factors": out["sentiment"]["platforms"],
        "global_brand_health": out["sentiment"]["global_brand_health"],
        "comments_total": out["sentiment"]["comments_total"],
        "expected": {"l3": out["expected_incremental_revenue"],
                     "l3_sentiment": out["sentiment"]["expected_incremental_revenue"],
                     "delta": out["sentiment"]["revenue_delta_vs_l3"],
                     **{k: v["expected_incremental_revenue"]
                        for k, v in out["baselines"].items()}},
        "elapsed_seconds": round(elapsed, 1),
    }

    # ---- what-if: a brand crisis on YouTube (voice +0.20 → −0.20) ------------
    from app.sentiment import load_snapshot, platform_factors, apply_to_fits
    from app.recommender import water_fill, expected_outcomes
    from app.metrics.aggregate import load, clean, weekly_platform
    from app.recommender import fit_all as _fit_all
    from dataclasses import replace as _dc_replace

    snap = load_snapshot()
    crisis = _dc_replace(snap,
                         platforms={**snap.platforms,
                                    "youtube": _dc_replace(snap.platforms["youtube"],
                                                           net_weighted=-0.20)})
    df = clean(load(f"{settings.data_dir}/{out['dataset']}.parquet",
                    columns=["platform", "date", "spend", "revenue", "conversions"]))
    fits = _fit_all(weekly_platform(df))
    plat_list = sorted({f.platform for f in fits})

    def run_alloc(s):
        f = platform_factors(s, plat_list)
        a = water_fill(apply_to_fits(fits, f), out["budget"])
        return f, a

    f_now, a_now = run_alloc(snap)
    f_cri, a_cri = run_alloc(crisis)
    slim["crisis_scenario"] = {
        "description": "YouTube brand voice +0.20 → −0.20 (same n=177k evidence)",
        "factors_now": {p: f_now[p].factor for p in plat_list},
        "factors_crisis": {p: f_cri[p].factor for p in plat_list},
        "allocation_now": a_now, "allocation_crisis": a_cri,
    }
    print("\n=== what-if: YouTube brand crisis (voice +0.20 → −0.20) ===")
    print(f"{'platform':10s} {'factor now':>11s} {'factor crisis':>14s} "
          f"{'alloc now':>12s} {'alloc crisis':>13s} {'shift':>12s}")
    for p in plat_list:
        d = a_cri[p] - a_now[p]
        print(f"{p:10s} {f_now[p].factor:>11.4f} {f_cri[p].factor:>14.4f} "
              f"{a_now[p]:>12,.0f} {a_cri[p]:>13,.0f} {d:>+12,.0f}")

    dest = settings.results_dir / "demo_recommend.json"
    dest.write_text(json.dumps(slim, indent=2))
    print(f"\nwrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
