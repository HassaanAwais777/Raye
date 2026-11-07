# Hisaab API

Base URL: `http://localhost:8000` · interactive docs: `/docs` (Swagger) · `/redoc`.

## Health & meta

### `GET /api/health`
```json
{"status": "ok", "version": "1.0.0", "app": "Hisaab API"}
```

### `GET /api/locales`
Registered locale packs (id, label, currency, cities, seasons).

### `GET /api/engines`
Engine catalog with install status:
```json
[{"id": "pandas", "label": "Pandas", "installed": true, "source_format": "parquet",
  "parallelism": "single-core", "install_note": ""},
 {"id": "spark", "install_note": "pyspark not installed (pip install pyspark; needs Java 17/21)", ...}]
```

## Datasets

### `POST /api/datasets`
```json
{"rows": 1000000, "locale": "pk", "seed": 42, "with_csv": true}
```
Generates the parquet (+CSV twin for MapReduce) and registers it.
`rows` ∈ [10, 20,000,000] · `locale` ∈ `pk | global`.
Errors: `409` if the id already exists.

### `GET /api/datasets`
List registered datasets (id, rows, locale, currency, generation time).

### `GET /api/datasets/{ds_id}/overview?by=platform`
Cleaned totals + per-group sums with derived metrics:
```json
{"rows_raw": 1005000, "rows_clean": 1000000, "duplicates_removed": 5000,
 "totals": {"spend": 956967.9, "revenue": 3112760.5, "roas": 3.25,
            "ctr": 0.0061, "cpc": 16.3, "cpa": 118.4, "cvr": 0.0138, ...},
 "groups": {"google": {...}, "facebook": {...}, ...},
 "currency": "PKR"}
```
`by` ∈ `platform | campaign | city | device | age | gender`.

## Benchmark

### `POST /api/benchmark`
```json
{"scales": [10000, 100000, 1000000], "engines": ["pandas", "polars", "mapreduce", "spark"],
 "locale": "pk", "repeat": 3, "mr_procs": 2}
```
Runs every engine × scale in isolated subprocesses (medians). Results **merge** into the
stored matrix, so you can extend it scale by scale. Long-running — prefer the CLI
(`scripts/benchmark.py`) for the 10M scale.

### `GET /api/benchmark/latest`
Stored matrix + `cost_model` (cloud profiles priced from the measured 10M runtimes) or
`404` if nothing ran yet.

## Recommender

### `POST /api/recommend`
```json
{"dataset": "pk_1000000_42", "budget": 1000000, "with_ci": true, "sentiment_aware": true}
```
Response (trimmed):
```json
{
  "allocation": [
    {"platform": "google", "allocated": 656921.0, "share_pct": 65.7,
     "expected_incremental_revenue": 2952770.1, "marginal_roas": 4.1267,
     "curve_alpha": 40526195.0, "curve_beta": 8820474.6, "curve_r2": 0.934,
     "alpha_ci": [38100000.0, 43200000.0], "beta_ci": [7900000.0, 9900000.0]},
    ...
  ],
  "expected_incremental_revenue": 4392595.0,
  "blended_incremental_roas": 4.393,
  "baselines": {
    "l1_roas_proportional": {"allocation": {...}, "expected_incremental_revenue": 3931613.0},
    "l2_bayes_shrunk":      {"allocation": {...}, "expected_incremental_revenue": 3918576.0}
  },
  "sentiment": {
    "enabled": true,
    "comments_total": 210511,
    "global_brand_health": 0.2041,
    "platforms": [
      {"platform": "youtube", "evidence": "youtube", "n_comments": 177234,
       "net_weighted": 0.2047, "deviation": 0.0005, "factor": 1.0008}, ...
    ],
    "allocation": [...],
    "expected_incremental_revenue": 4392591.0,
    "revenue_delta_vs_l3": -4.36,
    "note": "Curve scales aᵢ multiplied by sentiment factors before water-filling; ..."
  },
  "warnings": ["low curve fit (R² < 0.5) for: ... — treat those shares with care"],
  "method": "Per-platform revenue response fitted as R(s)=a·ln(1+s/β)+c ..."
}
```
`sentiment` block appears only when `sentiment_aware: true` and the Raye aggregates exist;
otherwise a warning explains how to run `scripts/export_raye.py`.

### `GET /api/recommend/history`
Stored recommendations (latest first).

## Sentiment bridge

### `GET /api/sentiment/summary`
Voice-of-customer snapshot for the dashboard:
```json
{
  "comments_total": 210511,
  "global": {"net_weighted": 0.2041, "n": 210511},
  "platforms": [{"platform": "google", "evidence": "reddit", "n_comments": 33277,
                 "net_weighted": 0.2008, "deviation": -0.0014, "factor": 0.9986}, ...],
  "products_top":    [{"slug": "xiaomi-smart-band-8", "net_shrunk": 0.323, "flag": "tailwind", ...}],
  "products_risk":   [{"slug": "tecno-spark-10", "net_shrunk": -0.083, "flag": "risk", ...}],
  "languages": {"n": 210511, "by_sentiment": {"positive": 96922, ...}}
}
```
`404` with a setup hint if `data/raye/raye_sentiment_aggregates.json` is missing.

## Static results

`GET /results/{file}` — benchmark artefacts: `benchmark_results.json`, `scalability.md`,
`runtime_chart.png`, `cost_model.json`, `demo_recommend.json`.

## Error model

Validation errors → `422` (Pydantic); unknown ids / missing files → `404` with a
human-readable `detail`; conflicts (e.g. dataset exists) → `409`.
