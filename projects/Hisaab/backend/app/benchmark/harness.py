"""Scaling benchmark harness: engines × scales, isolated processes, honest accounting."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, List

from ..config import settings
from ..db import save_benchmark
from ..engines.base import run_isolated
from ..engines import ENGINE_CLASSES
from ..generator import write_parquet, write_csv


def ensure_dataset(rows: int, locale: str = "pk", seed: int = 42,
                   with_csv: bool = True) -> dict:
    """Generate (once) the parquet+csv pair used by all engines at a given scale."""
    tag = f"bench_{locale}_{rows}"
    parquet = settings.data_dir / f"{tag}.parquet"
    csv = settings.data_dir / f"{tag}.csv"
    if not parquet.exists():
        t0 = time.time()
        write_parquet(parquet, rows, locale, seed)
        gen_s = round(time.time() - t0, 1)
    else:
        gen_s = 0.0
    if with_csv and not csv.exists():
        write_csv(csv, rows, locale, seed)
    return {"parquet": str(parquet), "csv": str(csv) if csv.exists() else None,
            "generated_s": gen_s}


def run_matrix(scales: List[int], engines: List[str], locale: str = "pk",
               repeat: int = 3, procs_mr: int = 2, out_dir: Path = None) -> dict:
    """Run every engine on every scale; keep the MEDIAN of `repeat` isolated runs.

    Results are MERGED into any existing benchmark_results.json, so the matrix can
    be extended incrementally (e.g. add the 10M scale in a second invocation).
    """
    out_dir = Path(out_dir or settings.results_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / "benchmark_results.json"
    prev = {}
    if out_file.exists():
        try:
            prev = json.loads(out_file.read_text())
        except Exception:                                       # noqa: BLE001
            prev = {}
    results: Dict[str, Dict[str, dict]] = dict(prev.get("results", {}))

    for rows in scales:
        with_csv = any(e.startswith("mapreduce") for e in engines)
        ds = ensure_dataset(rows, locale, with_csv=with_csv)
        for engine in engines:
            if engine not in ("pandas", "polars", "spark", "mapreduce", "mapreduce-parallel"):
                raise ValueError(f"unknown engine {engine}")
            cls = ENGINE_CLASSES.get("mapreduce" if engine == "mapreduce" else engine,
                                     ENGINE_CLASSES.get(engine))
            ok, reason = (cls.available() if engine not in ("mapreduce", "mapreduce-parallel")
                          else (True, ""))
            if engine == "mapreduce" and not ds["csv"]:
                results.setdefault(engine, {})[str(rows)] = {
                    "error": "csv source not generated for this scale", "seconds": None,
                    "peak_mb": None}
                continue
            if not ok:
                results.setdefault(engine, {})[str(rows)] = {
                    "error": reason, "seconds": None, "peak_mb": None}
                continue
            runs = []
            last = None
            for _ in range(max(1, repeat)):
                path = ds["csv"] if engine.startswith("mapreduce") else ds["parquet"]
                last = run_isolated(engine, path, rows, procs=procs_mr)
                if last.error:
                    break
                runs.append(last)
            if last.error:
                results.setdefault(engine, {})[str(rows)] = {
                    "error": last.error, "seconds": None, "peak_mb": None}
                continue
            runs.sort(key=lambda r: r.seconds)
            med = runs[len(runs) // 2]
            results.setdefault(engine, {})[str(rows)] = {
                "seconds": round(med.seconds, 3), "peak_mb": round(med.peak_mb, 1),
                "sums_ok": bool(med.sums)}

    all_scales = sorted({int(s) for s in list(prev.get("scales", [])) + list(scales)})
    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "locale": locale, "scales": all_scales, "repeat": repeat,
        "machine": _machine_note(), "results": results,
    }
    out_file = out_dir / "benchmark_results.json"
    out_file.write_text(json.dumps(payload, indent=2))
    save_benchmark(payload)
    _write_markdown(payload, out_dir / "scalability.md")
    return payload


def _machine_note() -> str:
    import os
    import platform
    try:
        import resource
        ram = f"{resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6:.1f} GB peak (self)"
    except Exception:                                          # noqa: BLE001
        ram = "n/a"
    return (f"{platform.system()} · {os.cpu_count()} vCPU · python {platform.python_version()} "
            f"· {ram}")


def _write_markdown(payload: dict, path: Path) -> None:
    lines = [
        "# Scalability benchmark — Pandas vs MapReduce vs PySpark vs Polars",
        "",
        f"*Generated {payload['generated_at']} · locale `{payload['locale']}` · "
        f"median of {payload['repeat']} isolated runs · task: group-by platform, "
        f"sum 5 metrics · {payload['machine']}*",
        "",
        "| Engine | " + " | ".join(f"{rows:,} rows" for rows in payload["scales"]) + " |",
        "|---|" + "---|" * len(payload["scales"]),
    ]
    for engine, by_scale in payload["results"].items():
        cells = []
        for rows in payload["scales"]:
            r = by_scale.get(str(rows), {})
            cells.append(f"{r['seconds']:,} s" if r.get("seconds") is not None
                         else f"⚠️ {r.get('error', 'unavailable')[:40]}")
        lines.append(f"| **{engine}** | " + " | ".join(cells) + " |")
    lines += [
        "",
        "Peak RAM (MB):",
        "",
        "| Engine | " + " | ".join(f"{rows:,} rows" for rows in payload["scales"]) + " |",
        "|---|" + "---|" * len(payload["scales"]),
    ]
    for engine, by_scale in payload["results"].items():
        cells = []
        for rows in payload["scales"]:
            r = by_scale.get(str(rows), {})
            cells.append(f"{r['peak_mb']:,}" if r.get("peak_mb") is not None else "—")
        lines.append(f"| **{engine}** | " + " | ".join(cells) + " |")
    lines += [
        "",
        "Notes: engines run in isolated subprocesses; wall time includes engine startup "
        "(JVM startup is counted for Spark — it is part of Spark's real cost). MapReduce "
        "reads the CSV text stream (Hadoop-style); DataFrame engines read Parquet.",
    ]
    path.write_text("\n".join(lines))
