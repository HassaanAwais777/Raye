"""PySpark engine — the industry-standard distributed engine (local[N] mode).

JVM startup is INCLUDED in the measured time (disclosed in the benchmark notes):
spinning up a session is part of the real-world cost of a Spark job.
"""
from .base import Engine, SUM_COLS


class SparkEngine(Engine):
    name = "spark"
    label = "PySpark (local)"
    source_format = "parquet"
    parallelism = "local[N] (JVM threads)"

    @classmethod
    def available(cls):
        try:
            import pyspark  # noqa: F401
            return True, ""
        except ImportError:
            return False, "pyspark not installed (pip install pyspark; needs Java 17/21)"

    def run(self, dataset_path: str, rows_hint: int = 0):
        from pyspark.sql import SparkSession
        from pyspark.sql import functions as F
        import os, tempfile
        warehouse = tempfile.mkdtemp(prefix="hisaab-spark-")
        spark = (SparkSession.builder.master("local[2]")
                 .appName("Hisaab-benchmark")
                 .config("spark.ui.enabled", "false")
                 .config("spark.sql.shuffle.partitions", "2")
                 .config("spark.driver.host", "127.0.0.1")
                 .config("spark.driver.bindAddress", "127.0.0.1")
                 .config("spark.warehouse.dir", warehouse)
                 .getOrCreate())
        try:
            df = spark.read.parquet(dataset_path).select("platform", *SUM_COLS)
            g = (df.groupBy("platform")
                   .agg(*[F.sum(c).alias(c) for c in SUM_COLS])   # PySpark 4.x: Column.sum() removed
                   .collect())
            out = {}
            for row in g:
                out[row["platform"]] = {c: float(row[c]) for c in SUM_COLS}
            return out
        finally:
            spark.stop()
