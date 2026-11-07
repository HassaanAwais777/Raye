#!/usr/bin/env python3
"""CLI: run the engine benchmark matrix and write results + chart + markdown.

  python scripts/benchmark.py --scales 10000,100000,1000000 \
      --engines pandas,polars,mapreduce,mapreduce-parallel,spark [--repeat 3]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings                                   # noqa: E402
from app.benchmark.harness import run_matrix                      # noqa: E402
from app.benchmark.costs import cost_table                        # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Engine scaling benchmark")
    ap.add_argument("--scales", default="10000,100000,1000000")
    ap.add_argument("--engines", default="pandas,polars,mapreduce,mapreduce-parallel,spark")
    ap.add_argument("--locale", choices=["pk", "global"], default="pk")
    ap.add_argument("--repeat", type=int, default=3)
    ap.add_argument("--mr-procs", type=int, default=2)
    args = ap.parse_args()

    scales = [int(s) for s in args.scales.split(",") if s.strip()]
    engines = [e.strip() for e in args.engines.split(",") if e.strip()]
    print(f"▶ benchmark: scales={scales} engines={engines} repeat={args.repeat}")
    payload = run_matrix(scales, engines, args.locale, args.repeat, args.mr_procs)

    print(json.dumps(payload["results"], indent=2)[:2000])
    out = settings.results_dir / "benchmark_results.json"
    print(f"✓ results  → {out}")
    print(f"✓ markdown → {settings.results_dir / 'scalability.md'}")

    # chart
    try:
        from app.benchmark.chart import plot_runtimes
        png = plot_runtimes(payload)
        print(f"✓ chart    → {png}")
    except Exception as e:                                     # noqa: BLE001
        print(f"(chart skipped: {e})")

    biggest = str(max(scales))
    costs = cost_table(payload["results"], biggest)
    (settings.results_dir / "cost_model.json").write_text(json.dumps(costs, indent=2))
    print(f"✓ costs    → {settings.results_dir / 'cost_model.json'}")


if __name__ == "__main__":
    main()
