#!/usr/bin/env python3
"""CLI: generate a dataset.

  python scripts/generate.py --rows 1000000 --locale pk --seed 42 [--no-csv]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.service import create_dataset                                    # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate a synthetic ad-performance dataset")
    ap.add_argument("--rows", type=int, default=100_000)
    ap.add_argument("--locale", choices=["pk", "global"], default="pk")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-csv", action="store_true", help="skip the CSV twin (faster)")
    args = ap.parse_args()
    rec = create_dataset(args.rows, args.locale, args.seed, with_csv=not args.no_csv)
    print(f"✓ dataset '{rec['id']}': {rec['rows']:,} rows in {rec['generation_seconds']}s")
    print(f"  parquet: {rec['parquet_path']}")
    if rec["csv_path"]:
        print(f"  csv:     {rec['csv_path']} ({rec['csv_rows']:,} rows)")


if __name__ == "__main__":
    main()
