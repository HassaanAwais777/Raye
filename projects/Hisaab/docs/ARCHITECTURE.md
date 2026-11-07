# Hisaab — Architecture

*How twelve columns become a budget split, four different ways.*

```
                    ┌──────────────────────────────────────────────────────────┐
                    │                        generator                         │
                    │  locales.py (PK / Global economics)  synth.py (vectorised│
                    │  day-pools, saturation decay, bot/viral/duplicate traps) │
                    └───────────────┬──────────────────────────────────────────┘
                                    │  Parquet (zstd) + CSV twin
                    ┌───────────────▼──────────────┐
                    │           metrics            │
                    │  aggregate.clean / aggregate │   formulas.py: CTR CPC CPA CVR ROAS
                    │  weekly_platform             │   (single source of derived truth)
                    └──────┬──────────────┬────────┘
                           │              │
          ┌────────────────▼───┐   ┌──────▼─────────────────────────────────┐
          │      engines       │   │             recommender                │
          │ pandas │ polars    │   │ curves.py  R(s)=a·ln(1+s/β)+c          │
          │ spark  │ mapreduce │   │ allocate.py  water-fill  xᵢ=aᵢ/λ−βᵢ     │
          │ (isolated procs,   │   │ baselines.py L1 ROAS-prop, L2 EB-shrunk│
          │  peak-RSS metered) │   └──────┬─────────────────────────────────┘
          └────────────────────┘          │
                                          │      ┌─────────────────────────────┐
                    ┌─────────────────────┼──────┤ sentiment (Raye bridge)     │
                    │   benchmark         │      │ bridge.py  ← data/raye/*    │
                    │ harness · costs ·   │      │ adjust.py  factors ×aᵢ      │
                    │ chart               │      │            product board    │
                    └─────────────────────┴──────┴─────────────────────────────┘
                                    │
                          FastAPI  ─┴─►  React + TS dashboard
```

## 1. Data layer

**Contract.** Twelve columns, campaign grain:
`date, campaign, platform, impressions, clicks, spend, conversions, revenue, age, gender, city, device`.

**Generator (`app/generator/`).** Row economics are *calibrated, not random*: each platform
has CTR / CVR / CPC chosen so blended ROAS ≈ 3 with a credible spread (Google strongest,
TikTok weakest), verified by `test_blended_roas_in_calibration_band`. Structure:

- a pool of daily spend per (day, platform), modulated by weekday (+10% weekend), season
  (PK: Ramadan ×1.45, 11.11; Global: Black Friday ×1.55) and yearly lognormal noise;
- each row spends a noisy share of its pool → `impressions ≈ spend/(CPC·CTR)` → clicks,
  then conversions as a **Poisson draw** on `clicks·CVR·decay·quality` (a counting process —
  integer truncation here would silently crush ROAS 8×), then revenue = conversions·AOV·noise;
- **saturation**: within a (day, platform) pool the marginal CVR decays with cumulative-spend
  rank (`SATURATION_DEPTH = 0.45`) — the concave signal L3 fits;
- **traps on purpose**: ~1% impression-fraud rows (impressions ×20-40, zero clicks), ~2%
  viral rows, ~0.5% exact duplicates.

Streaming writer: chunks of ≤1M rows go straight to Parquet (zstd) and a CSV twin, so 10M
rows never exceed a few hundred MB of RAM.

## 2. Metrics layer

`app/metrics/aggregate.py` implements the documented cleaning policy (drop exact duplicates;
drop top-0.5%-impressions ∧ zero-clicks fraud rows; clip impossible negatives) and the
weekly (platform, spend, revenue, conversions) aggregation the recommender fits on.
`app/metrics/formulas.py` computes **every** derived ratio — engines never compute ratios
themselves. This separation is what makes engine parity exactly assertable.

## 3. Engines

All four implement `Engine.run(path, rows_hint) → {platform: raw sums}` and run in a
**spawned subprocess** with `ru_maxrss` peak-RSS metering (`app/engines/base.py`).

| Engine | Source | Parallelism | Notes |
|---|---|---|---|
| Pandas | Parquet | single-core | the reference implementation |
| Polars | Parquet | multi-core (Rust) | columnar scan + `group_by().sum()` |
| PySpark | Parquet | `local[2]` JVM threads | JVM startup included in timing, on purpose |
| MapReduce | **CSV text stream** | 1 proc or N-way splits | faithful map → combine → shuffle → reduce in pure Python, 250k-line chunks; `hadoop_streaming/{mapper,reducer}.py` run unchanged under Hadoop Streaming |

MapReduce column access is positional (CSV line `split(",")` with fixed indices for the
metrics columns) exactly like a Streaming mapper would do — no CSV parser hospitality.

## 4. Recommender

**Model.** Per platform, weekly points `(sₜ, rₜ)` fit
`R(s) = a·ln(1 + s/β) + c`. For fixed β it is closed-form OLS on `(1, ln(1+s/β))`; β comes
from a log-spaced grid **capped at 2× the largest observed weekly spend** (beyond the data,
saturation is unidentifiable — an unconstrained grid drifts to the linear corner and the
optimizer starves every platform but the steepest). Bootstrap over weekly points gives α/β
confidence intervals.

**Allocation.** Water-filling: maximize `Σ aᵢ·ln(1+xᵢ/βᵢ)` s.t. `Σxᵢ = B, xᵢ ≥ 0`.
Equalize marginals `aᵢ/(βᵢ+xᵢ) = λ` ⇒ `xᵢ(λ) = aᵢ/λ − βᵢ`, decreasing in λ → bisect on λ.
Platforms whose `aᵢ/λ ≤ βᵢ` get **zero** — saturation is punished by the math, not by a rule.
Numeric residue goes to the platform with the highest marginal return.

**Baselines** (scored under the *same* fitted curves — apples to apples):
L1 splits ∝ average ROAS (ignores saturation); L2 splits ∝ empirical-Bayes-shrunk ROAS
(`(revᵢ + k·μ)/(spendᵢ + k)`) — the guard against crowning a platform on 3 lucky weeks.

## 5. Raye sentiment bridge

Raye (companion project) labelled 210,511 product comments from YouTube and Reddit
(EN / اردو / Roman-Urdu) with scores in [−1, 1]. `scripts/export_raye.py` aggregates them
into `data/raye/raye_sentiment_aggregates.json` (platform / global / per-product; brand
health = likes-weighted mean score, weight = likes+1) plus a 25k-row stratified sample.

`app/sentiment/adjust.py` converts health into budget pressure:

- **Evidence mapping** — youtube → youtube (direct), reddit → google (discussion/research
  proxy, 0.5 weight), unmeasured platforms → global fallback. Nothing is invented.
- **Shrinkage** — confidence `c = n/(n+25,000)`; deviation `D = c·proxy·(S_e − S̄)`;
  factor `= clip(1 + 1.5·D, 1 ± 12%)`. With the real corpus (uniform platform voice)
  factors land within ±0.15% — the honest result; a what-if crisis scenario (voice −0.20)
  hits the −12% cap and starves that platform, visible in `results/demo_recommend.json`.
- **Product board** — `shrunkᵢ = (nᵢ·Sᵢ + 2000·S̄)/(nᵢ+2000)`: small samples stay near the
  brand mean, the corpus's real laggards (Tecno Spark 10, 38% negative) survive and flag.

Tests pin the properties: factors monotone in voice, bounded on real data, overlay shifts
budget *toward* healthier platforms when curves are equal, and the committed JSON equals
aggregates recomputed from the 210k-row CSV.

## 6. Benchmark harness

`app/benchmark/harness.py` runs every (engine × scale) in isolated subprocesses, keeps the
median of N repeats, merges results incrementally, and writes `benchmark_results.json`,
`scalability.md` and a log-log `runtime_chart.png`. `app/benchmark/costs.py` translates the
measured 10M-row runtimes into cloud profiles (EMR / on-demand list prices) — teaching the
shape of scale-up vs scale-out, not quoting procurement.

## 7. Service & API

`app/service.py` is the use-case layer (generate, overview, recommend, sentiment summary);
`app/api/routes.py` exposes it over FastAPI; the React dashboard consumes it. The registry
(SQLite in `hisaab.db`) tracks datasets, benchmark runs and recommendation history.
