# Scalability benchmark — Pandas vs MapReduce vs PySpark vs Polars

*Generated 2026-11-04T15:31:41Z · locale `pk` · median of 3 isolated runs · task: group-by platform, sum 5 metrics · Linux · 2 vCPU · python 3.12.16 · 0.1 GB peak (self)*

| Engine | 10,000 rows | 100,000 rows | 1,000,000 rows | 10,000,000 rows |
|---|---|---|---|---|
| **pandas** | 0.931 s | 0.945 s | 1.062 s | 2.655 s |
| **polars** | 0.179 s | 0.184 s | 0.227 s | 0.687 s |
| **mapreduce** | 0.03 s | 0.298 s | 3.131 s | 57.867 s |
| **mapreduce-parallel** | 0.447 s | 0.739 s | 2.525 s | 39.579 s |
| **spark** | 11.929 s | 12.042 s | 12.568 s | 15.531 s |

Peak RAM (MB):

| Engine | 10,000 rows | 100,000 rows | 1,000,000 rows | 10,000,000 rows |
|---|---|---|---|---|
| **pandas** | 142.6 | 417.0 | 2,135.4 | 1,300.3 |
| **polars** | 145.6 | 417.0 | 2,135.4 | 799.0 |
| **mapreduce** | 104.8 | 417.0 | 2,135.4 | 107.0 |
| **mapreduce-parallel** | 104.8 | 417.0 | 2,135.4 | 107.0 |
| **spark** | 153.1 | 417.0 | 2,135.4 | 153.0 |

Notes: engines run in isolated subprocesses; wall time includes engine startup (JVM startup is counted for Spark — it is part of Spark's real cost). MapReduce reads the CSV text stream (Hadoop-style); DataFrame engines read Parquet.