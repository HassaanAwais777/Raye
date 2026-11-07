# Hisaab Lab Guide

A hands-on path from an empty directory to a defended demo — sized for a lab session
(≈90 min) or a self-study evening. Every command below was run to produce the numbers
in the README.

---

## 0. Setup (10 min)

```bash
git clone https://github.com/HassaanAwais777/Hisaab.git
cd Hisaab/backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
pytest -q                                              # expect: all passed
```

Optional (Spark engine): `pip install -r requirements-spark.txt` — needs Java 17/21
(`java -version` to check).

Verify the API boots:

```bash
uvicorn app.main:app --port 8000       # visit http://localhost:8000/docs, Ctrl-C when done
```

---

## 1. Generate data — and meet the traps (10 min)

```bash
python scripts/generate.py --rows 1000000 --locale pk
```

Open the Python shell and *look* at what was injected:

```python
import pandas as pd
df = pd.read_parquet("data/pk_1000000_42.parquet")
df.platform.value_counts()                       # five platforms, weighted shares
df.duplicated().sum()                            # ~0.5% exact duplicates
fraud = df[(df.impressions >= df.impressions.quantile(0.995)) & (df.clicks == 0)]
len(fraud)                                       # ~1% impression-fraud rows
(df.revenue / df.spend).describe()               # per-row ROAS is noisy; sums are not
```

**Question for the report:** why is per-row ROAS nearly meaningless while aggregate ROAS
is stable? (Noise averages; bias does not — which is exactly why the fraud rows must be
*dropped*, not averaged.)

Compare locales:

```bash
python scripts/generate.py --rows 100000 --locale global
```

Same funnel shape, different currency / cities / seasons (Black Friday vs Ramadan).

---

## 2. The four engines, one answer (15 min)

```bash
python - <<'PY'
from app.metrics.aggregate import load, aggregate
from app.engines.pandas_engine import PandasEngine
from app.engines.polars_engine import PolarsEngine
from app.engines.mapreduce_engine import MapReduceEngine

parquet, csv = "data/pk_1000000_42.parquet", "data/pk_1000000_42.csv"
ref = aggregate(load(parquet, columns=["platform", "impressions", "clicks", "spend",
                                       "conversions", "revenue"]))
for eng, path in [(PandasEngine(), parquet), (PolarsEngine(), parquet),
                  (MapReduceEngine(), csv), (MapReduceEngine(procs=2), csv)]:
    out = eng.run(path)
    diff = max(abs(out[p][m] - ref[p][m]) for p in ref for m in ("spend", "revenue"))
    print(f"{eng.name:20s} max abs diff vs pandas: {diff:.4f}")
PY
```

Four architectures, zero disagreement. **Why it matters:** the benchmark can now measure
*speed* without arguing about *correctness* — the parity is a test, not a claim.

### Bonus: the same MapReduce on a real Hadoop cluster

`hadoop_streaming/mapper.py` and `reducer.py` are plain stdin/stdout scripts:

```bash
python hadoop_streaming/mapper.py < data/pk_1000000_42.csv | sort | python hadoop_streaming/reducer.py | head
# on a cluster:
# hadoop jar streaming.jar -files mapper.py,reducer.py \
#   -mapper mapper.py -reducer reducer.py -input /data/ads.csv -output /out/hisaab
```

---

## 3. Benchmark — the honest race (20 min)

```bash
python scripts/benchmark.py --scales 10000,100000,1000000 --repeat 3
# when comfortable with time (10M generation ≈ 2 min):
python scripts/benchmark.py --scales 10000000 --repeat 3      # results MERGE incrementally
```

Read `results/scalability.md` and `results/runtime_chart.png`, then explain three curves:

1. **Polars** — why columnar + multi-core wins in-process.
2. **Spark** — why the line is flat (~12 s JVM startup amortising across scales).
3. **MapReduce** — why pure-Python streaming loses, and what the parallel-splits variant
   recovers. Connect to the cloud cost model in `results/cost_model.json`: where does the
   "Hadoop tax" invert? (Hint: it doesn't at 10M — do the arithmetic for 10B.)

Each engine runs in its own subprocess with peak-RSS metering — find your engine's memory
in `results/benchmark_results.json`.

---

## 4. The recommender — from curves to a budget split (20 min)

```bash
python scripts/demo_recommend.py 1000000
```

This prints the allocation table (L3 vs L3+Raye), the baselines, and a **crisis what-if**
(YouTube brand voice +0.20 → −0.20). Then open the dashboard:

```bash
# terminal 2
cd ../frontend && npm install && npm run dev       # http://localhost:5173
```

Walk through the four panels: platform performance → budget recommender → Raye voice panel
→ benchmark. Toggle the sentiment overlay off/on and watch the factors column.

Understand the two numbers that drive everything:

```python
from app.recommender.curves import fit_curve
import pandas as pd
from app.metrics.aggregate import load, clean, weekly_platform

df = clean(load("data/pk_1000000_42.parquet",
                columns=["platform", "date", "spend", "revenue", "conversions"]))
wk = weekly_platform(df)
g = wk[wk.platform == "google"]
fit = fit_curve("google", g.spend, g.revenue)
print(fit)                              # α (scale), β (half-saturation), R²
print(fit.marginal_roas(0), fit.marginal_roas(500_000))   # strictly decreasing
```

**Why log?** `dR/ds = a/(β+s)` is strictly decreasing — the property water-filling needs.
**Why the β grid caps at 2× observed spend?** Beyond the data, curvature is unidentifiable;
an unconstrained grid drifts to the linear corner and the optimizer starves everyone but
the steepest platform. (Try removing the cap in `curves.py` and watch the demo degenerate
to 100%-google — then restore it.)

### The water-filling property the tests pin

```python
from app.recommender.allocate import water_fill
alloc = water_fill([fit], 300_000)      # tiny budget → goes where the FIRST rupee returns most
```

A saturated platform earns **zero** — not because a rule says so, but because at the
optimal λ its marginal return is below the cut.

---

## 5. The Raye sentiment bridge (15 min)

Hisaab's companion project **Raye** ([github.com/HassaanAwais777/Raye](https://github.com/HassaanAwais777/Raye))
analysed **210,511** product comments (YouTube + Reddit; EN / اردو / Roman-Urdu). The
aggregated export ships in `data/raye/`; to refresh it from Raye's own database:

```bash
python scripts/export_raye.py --db /path/to/raye/custom.db
```

Inspect what the bridge sees:

```python
import json
d = json.load(open("data/raye/raye_sentiment_aggregates.json"))
print(d["provenance"])                     # where the numbers come from — always disclosed
print(d["global"])                         # brand health +0.204 over 210,511 comments
print(d["platforms"])                      # youtube +0.2047, reddit +0.2008 (uniform voice)
for p in d["products"][:4]: print(p["name"], p["net_weighted"], p["by_sentiment"])
```

Three honest-design points to articulate in a defense:

1. **Measured ≠ invented.** Only measured surfaces get factors (YouTube direct; Reddit
   proxies Google at 0.5 weight). Facebook/Instagram/TikTok fall back to the global index
   — factor exactly 1.0.
2. **Shrinkage.** A surface's factor scales with `n/(n+25000)` confidence; a product with
   4 comments cannot swing the risk board (empirical Bayes, same pattern as L2).
3. **Signal-strength honesty.** The corpus's platform voice is uniform (±0.3%) → factors
   ≈ ±0.1%; the *product* spread is 0.45 → decisive risk flags (Tecno Spark 10 at 38%
   negative). The overlay reports small numbers because the evidence is small — it does
   not manufacture drama.

---

## 6. Suggested lab-report outline

1. **Contract & parity** — the twelve-column schema; four engines, one answer (§2).
2. **Scaling** — the runtime table + chart; JVM-flat vs columnar-slope vs Hadoop-tax (§3).
3. **Optimization** — curve model, water-filling, why L3 > L1/L2 under the same curves (§4).
4. **Qualitative signal** — the Raye bridge: evidence mapping, shrinkage, crisis what-if (§5).
5. **Threats to validity** — synthetic calibration disclosed; traps modelled explicitly;
   bounded extrapolation (β cap); sentiment factors capped at ±12%.

Each claim above has a test behind it — cite `backend/tests/` in the report.
