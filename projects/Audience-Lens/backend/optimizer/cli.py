"""Standalone CLI for the optimizer module (Project B — Hisaab)."""
from __future__ import annotations

import argparse
import json

from .engine import optimize


def main() -> None:
    p = argparse.ArgumentParser(
        prog="backend.optimizer.cli",
        description="Water-fill budget optimization (Project B / Hisaab)",
    )
    p.add_argument("--budget", type=float, required=True)
    p.add_argument("--objective", default="awareness",
                   choices=["awareness", "views", "traffic", "leads", "sales"])
    p.add_argument("--strategy", default="balanced",
                   choices=["balanced", "performance_focused", "exploratory"])
    p.add_argument("--formats", default="in_stream,shorts,in_feed",
                   help="Comma-separated format ids")
    args = p.parse_args()

    res = optimize(
        budget=args.budget,
        formats=[f.strip() for f in args.formats.split(",") if f.strip()],
        objective=args.objective,
        strategy=args.strategy,
    )
    # Print a compact human-readable summary + full JSON
    print(f"\nBudget: {args.budget} | Objective: {args.objective} | Strategy: {args.strategy}")
    print(f"Provenance: {res['provenance']} | Sums to budget: {res['constraints']['sums_to_budget_exactly']}")
    print("\nAllocation:")
    for a in res["allocation"]:
        print(f"  {a['label']:<20} {a['amount']:>12.2f}  ({a['share']}%)")
    print(f"\n  {'Total':<20} {res['total_allocated']:>12.2f}")
    print("\nScenarios (expected revenue):")
    for name, sc in res["scenarios"].items():
        print(f"  {name:<20} {sc['expected_revenue']:>12.4f}")
    print("\n--- full JSON ---")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
