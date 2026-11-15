"""Standalone CLI for the audience module (Project 3)."""
from __future__ import annotations

import argparse
import json

from .engine import cluster, detect


def main() -> None:
    p = argparse.ArgumentParser(
        prog="backend.audience.cli",
        description="Audience clustering & anomaly detection (Project 3)",
    )
    p.add_argument("--texts", help="File with one comment per line")
    p.add_argument("--method", default="kmeans", choices=["kmeans", "dbscan", "hierarchical"])
    p.add_argument("--k", type=int, default=None)
    p.add_argument("--anomaly", action="store_true", help="Run anomaly detection instead")
    p.add_argument("--series", help="Comma-separated numeric series for anomaly detection")
    args = p.parse_args()

    if args.anomaly:
        vals = [float(x) for x in args.series.split(",") if x.strip()]
        series = [{"label": f"t{i}", "features": [v]} for i, v in enumerate(vals)]
        print(json.dumps(detect(series), indent=2))
        return

    if not args.texts:
        p.error("Provide --texts FILE")
    with open(args.texts, encoding="utf-8") as fh:
        texts = [ln.strip() for ln in fh if ln.strip()]
    print(json.dumps(cluster(texts, method=args.method, k=args.k), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
