"""MapReduce engine — a faithful Hadoop-style implementation in pure Python.

Phases (mirroring Hadoop Streaming):
  1. MAP        — stream CSV lines, emit (platform, partial-accumulator) per LINE
  2. COMBINE    — per input SPLIT (chunk), fold partials in memory (local aggregation)
  3. SHUFFLE    — group combined partials by key (hash-shuffle emulation; Hadoop sorts,
                  see docs/ARCHITECTURE.md §4 for the honest difference)
  4. REDUCE     — fold partials per key into final sums

The same mapper/reducer logic ships as `hadoop_streaming/mapper.py` + `reducer.py`
(runnable on a real Hadoop cluster via `hadoop jar streaming`).

`procs > 1` runs splits across worker processes — demonstrating the MapReduce thesis:
scale OUT, not up.
"""
import csv
import multiprocessing as mp
from collections import defaultdict
from typing import Dict, Tuple

from .base import Engine, SUM_COLS

# column order in the generated CSV (see generator COLUMNS)
COL_IDX = {"platform": 2, "impressions": 3, "clicks": 4, "spend": 5,
           "conversions": 6, "revenue": 7}
CHUNK_LINES = 250_000                      # input-split size


def map_line(row: list) -> Tuple[str, tuple]:
    """MAP: one key-value pair per line — (platform, (imp, clk, spend, conv, rev, 1))."""
    key = row[COL_IDX["platform"]]
    return key, (int(row[COL_IDX["impressions"]]), int(row[COL_IDX["clicks"]]),
                 float(row[COL_IDX["spend"]]), int(row[COL_IDX["conversions"]]),
                 float(row[COL_IDX["revenue"]]), 1)


def combine(pairs) -> Dict[str, tuple]:
    """COMBINE: local fold of one split's mapped pairs (runs on the map node)."""
    acc = defaultdict(lambda: (0, 0, 0.0, 0, 0.0, 0))
    for key, vals in pairs:
        a = acc[key]
        acc[key] = (a[0] + vals[0], a[1] + vals[1], a[2] + vals[2],
                    a[3] + vals[3], a[4] + vals[4], a[5] + vals[5])
    return dict(acc)


def reduce_partials(acc: Dict[str, tuple], partials: Dict[str, tuple]) -> Dict[str, tuple]:
    """REDUCE input step: merge one more combined split into the running totals."""
    for key, v in partials.items():
        a = acc.setdefault(key, (0, 0, 0.0, 0, 0.0, 0))
        acc[key] = (a[0] + v[0], a[1] + v[1], a[2] + v[2], a[3] + v[3], a[4] + v[4], a[5] + v[5])
    return acc


def _map_split(args):
    path, start_line, max_lines = args
    """One map task = one input split: [start_line, start_line+max_lines) of the CSV."""
    acc = defaultdict(lambda: (0, 0, 0.0, 0, 0.0, 0))
    with open(path, newline="", encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i < start_line:
                continue
            if i >= start_line + max_lines:
                break
            if i == 0 or not line.strip():
                continue                      # header / blank
            key, vals = map_line(next(csv.reader([line])))
            a = acc[key]
            acc[key] = (a[0] + vals[0], a[1] + vals[1], a[2] + vals[2],
                        a[3] + vals[3], a[4] + vals[4], a[5] + vals[5])
    return dict(acc)


class MapReduceEngine(Engine):
    name = "mapreduce"
    label = "MapReduce (Python)"
    source_format = "csv (streamed line-by-line)"
    parallelism = "configurable splits"

    def __init__(self, procs: int = 1) -> None:
        self.procs = procs
        if procs > 1:
            self.name = "mapreduce-parallel"
            self.label = f"MapReduce ×{procs} splits"

    def run(self, dataset_path: str, rows_hint: int = 0):
        # count data lines cheaply to size the splits
        n_lines = 0
        with open(dataset_path, "rb") as f:
            for _ in f:
                n_lines += 1
        n_data = max(0, n_lines - 1)
        splits = [(dataset_path, 1 + i * CHUNK_LINES, CHUNK_LINES)
                  for i in range(max(1, -(-n_data // CHUNK_LINES)))]

        acc: Dict[str, tuple] = {}
        if self.procs > 1:
            with mp.Pool(self.procs) as pool:
                for partial in pool.imap_unordered(_map_split, splits):
                    acc = reduce_partials(acc, partial)
        else:
            for s in splits:
                acc = reduce_partials(acc, _map_split(s))

        out = {}
        for key, v in acc.items():
            out[key] = dict(zip(SUM_COLS, (v[0], v[1], v[2], v[3], v[4], v[5])))
            out[key] = {k: float(x) for k, x in out[key].items()}
        return out
