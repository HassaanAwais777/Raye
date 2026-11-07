"""Cloud cost model — what each architecture would cost to run 10M rows in the cloud.

Pricing is approximate public list pricing (us-east-1, on-demand, 2025–26) and exists to
teach the *shape* of the trade-off (fixed cluster overhead vs parallel wall time), not to
be a procurement quote. Sources: aws.amazon.com/emr pricing, ec2instances.info.
"""
from __future__ import annotations

# $/hour, on-demand us-east-1
M5_XLARGE = 0.192
M5_2XLARGE = 0.384
EBS_GB_MONTH = 0.08


def estimate(engine: str, seconds_10m_local: float, rows_10m: int = 10_000_000) -> dict:
    """Translate a measured local run into a realistic cloud configuration + cost."""
    data_gb = rows_10m * 90 / 1e9 * 3      # ≈ raw CSV + parquet + intermediate shuffle
    profiles = {
        "pandas": {
            "config": "1× r5.xlarge (32 GB) single node",
            "nodes": 1, "hours": max(seconds_10m_local, 1) / 3600 * 1.2,   # slower single core
            "hourly": 0.252,
            "note": "Scale-UP only: one big box. Simple, cheap, but bounded by one machine's RAM.",
        },
        "polars": {
            "config": "1× m5.2xlarge single node",
            "nodes": 1, "hours": max(seconds_10m_local, 1) / 3600 * 1.2,
            "hourly": M5_2XLARGE,
            "note": "Same single node, but multi-core + columnar engine: fastest per $.",
        },
        "mapreduce": {
            "config": "EMR 1 master + 4× m5.xlarge core (Hadoop Streaming)",
            "nodes": 5,
            "hours": max(seconds_10m_local, 1) / 3600 * 4 / 4 + 0.25,     # ÷4 workers + overhead
            "hourly": M5_XLARGE,
            "note": "Scale-OUT: per-node work drops with workers, but cluster boot + IO overhead dominates at 10M rows — the classic 'Hadoop tax' for small data.",
        },
        "spark": {
            "config": "EMR 1 master + 2× m5.xlarge core (Spark local[2] per node in prod: Glue/EMR managed autoscaling)",
            "nodes": 3,
            "hours": max(seconds_10m_local, 1) / 3600 * 1.5,
            "hourly": M5_XLARGE,
            "note": "In-memory shuffle beats disk-based MapReduce; EMR startup overhead still applies.",
        },
    }
    p = profiles[engine]
    cost = p["nodes"] * p["hours"] * p["hourly"]
    return {
        "engine": engine,
        "config": p["config"],
        "estimated_node_hours": round(p["nodes"] * p["hours"], 3),
        "estimated_cost_usd": round(max(cost, 0.02), 3),
        "data_gb": round(data_gb, 1),
        "note": p["note"],
        "pricing_basis": "on-demand list prices, us-east-1; storage not included "
                         f"(S3 {data_gb:.1f} GB ≈ ${data_gb * 0.023:.3f}/mo)",
    }


def cost_table(results: dict, rows_label: str = "10000000") -> list:
    """Build the cost comparison from measured 10M runtimes (when available)."""
    out = []
    for engine in ("pandas", "mapreduce", "spark", "polars"):
        r = results.get(engine, {}).get(rows_label, {})
        s = r.get("seconds")
        est = estimate(engine, s) if s else estimate(engine, 0.0)
        est["measured_local_seconds"] = s
        out.append(est)
    return out
