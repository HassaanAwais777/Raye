"""Engine registry — the plug-in point for new compute engines."""
from .base import Engine, EngineResult, run_isolated, SUM_COLS
from .pandas_engine import PandasEngine
from .polars_engine import PolarsEngine
from .spark_engine import SparkEngine
from .mapreduce_engine import MapReduceEngine

ENGINE_CLASSES = {
    PandasEngine.name: PandasEngine,
    PolarsEngine.name: PolarsEngine,
    SparkEngine.name: SparkEngine,
    MapReduceEngine.name: MapReduceEngine,
    "mapreduce-parallel": MapReduceEngine,      # procs>1 variant, instantiated with procs
}


def get_engine(name: str, procs: int = 1) -> Engine:
    if name == "mapreduce-parallel":
        return MapReduceEngine(procs=procs)
    try:
        return ENGINE_CLASSES[name]()
    except KeyError:
        raise ValueError(f"unknown engine '{name}'; available: "
                         f"{', '.join(sorted(set(ENGINE_CLASSES)))}") from None


def engine_catalog() -> list:
    out = []
    for name, cls in ENGINE_CLASSES.items():
        ok, reason = cls.available()
        out.append({"id": name, "label": cls.label, "installed": ok,
                    "install_note": reason, "source_format": cls.source_format,
                    "parallelism": cls.parallelism})
    return out


__all__ = ["Engine", "EngineResult", "run_isolated", "SUM_COLS", "ENGINE_CLASSES",
           "get_engine", "engine_catalog"]
