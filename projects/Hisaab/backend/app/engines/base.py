"""Benchmark engine contract.

Every engine answers the SAME question on the SAME dataset:
"total impressions / clicks / spend / conversions / revenue / rows per platform".

Engines return raw sums only — derived ratios are computed once in metrics.formulas.
The harness runs each engine in a fresh subprocess and records wall time + peak RSS
(resource.getrusage), so no engine is penalised by another's allocations.
"""
import abc
import json
from typing import Dict, Optional, Tuple

SUM_COLS = ("impressions", "clicks", "spend", "conversions", "revenue")


class EngineResult:
    def __init__(self, sums: Dict[str, Dict[str, float]], seconds: float,
                 peak_mb: float, error: Optional[str] = None) -> None:
        self.sums = sums
        self.seconds = seconds
        self.peak_mb = peak_mb
        self.error = error

    def to_dict(self) -> dict:
        return {"sums": self.sums, "seconds": self.seconds,
                "peak_mb": self.peak_mb, "error": self.error}

    @staticmethod
    def from_dict(d: dict) -> "EngineResult":
        return EngineResult(d["sums"], d["seconds"], d["peak_mb"], d.get("error"))


class Engine(abc.ABC):
    name: str = "base"
    label: str = "Base engine"
    source_format: str = "parquet"          # what it reads (fair-I/O disclosure)
    parallelism: str = "single-core"

    @classmethod
    def available(cls) -> Tuple[bool, str]:
        """(installed?, reason-if-not)"""
        return True, ""

    @abc.abstractmethod
    def run(self, dataset_path: str, rows_hint: int = 0) -> Dict[str, Dict[str, float]]:
        """Compute per-platform raw sums. Must not print or mutate the dataset."""


def child_entry(engine_name: str, dataset_path: str, rows_hint: int, out_path: str,
                procs: int = 1) -> None:
    """Subprocess entry: run one engine, record time + peak RSS, JSON-dump the result."""
    import resource
    import time
    from . import ENGINE_CLASSES
    from .mapreduce_engine import MapReduceEngine

    if engine_name == "mapreduce-parallel":
        engine = MapReduceEngine(procs=max(2, procs))
    else:
        engine = ENGINE_CLASSES[engine_name]()
    t0 = time.perf_counter()
    error = None
    sums = {}
    try:
        sums = engine.run(dataset_path, rows_hint)
    except Exception as exc:                                   # noqa: BLE001 — harness must survive
        error = f"{type(exc).__name__}: {exc}"
    seconds = time.perf_counter() - t0
    peak_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss   # Linux: KB
    res = EngineResult(sums, seconds, peak_kb / 1024.0, error)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(res.to_dict(), f)


def run_isolated(engine_name: str, dataset_path: str, rows_hint: int = 0,
                 procs: int = 1) -> EngineResult:
    """Run one engine in a fresh process (clean memory accounting)."""
    import os
    import tempfile
    import multiprocessing as mp

    ctx = mp.get_context("spawn")
    fd, out_path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    p = ctx.Process(target=child_entry,
                    args=(engine_name, dataset_path, rows_hint, out_path, procs))
    p.start()
    p.join()
    try:
        with open(out_path, encoding="utf-8") as f:
            return EngineResult.from_dict(json.load(f))
    except (json.JSONDecodeError, FileNotFoundError):
        return EngineResult({}, 0.0, 0.0,
                            error=f"worker died before reporting (engine={engine_name})")
    finally:
        os.unlink(out_path)
