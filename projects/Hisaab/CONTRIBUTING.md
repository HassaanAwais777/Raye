# Contributing to Hisaab

Thanks for considering a contribution — the project stays useful by staying
**honest**: measured numbers, disclosed assumptions, properties pinned by tests.

## The three house rules

1. **Engines return raw sums.** Every compute engine answers the same question with
   the same shape (`{platform: {impressions, clicks, spend, conversions, revenue}}`).
   Derived ratios (CTR, CPC, CPA, CVR, ROAS) are computed in exactly one place,
   `app/metrics/formulas.py`. This is what makes engine parity testable.
2. **New signals stay inside documented bounds.** The sentiment overlay clips factors
   to `1 ± cap`; water-filling always sums to the budget; saturated platforms may earn
   zero. If your feature bends an invariant, update the invariant *and its test*, and
   say why in the PR.
3. **Benchmarks disclose.** Machine, repeat count, and what the timer includes
   (Spark's JVM startup is counted — keep it that way).

## Dev setup

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
# optional, for the Spark engine:
pip install -r requirements-spark.txt     # needs Java 17/21

pytest -q                                 # expect: all passed
```

Frontend:

```bash
cd frontend && npm install && npm run dev
```

## What's worth contributing

- **Engines** — DuckDB, Dask, or a Flink/Beam port. Inherit `app/engines/base.Engine`,
  implement `run()`, add the engine to `ENGINE_CLASSES`, add a parity test, done.
- **Signals** — a third overlay for the recommender (creative freshness? audience
  overlap?) with the same shrinkage discipline as the Raye bridge.
- **Real data adapters** — an export path from a real ads platform to the twelve-column
  contract (keeping synthetic data as the reproducible default).
- **Baselines** — a better naive allocator than L1/L2 to test L3 against.

## Commit style

`type: short imperative summary` — `feat:`, `fix:`, `perf:`, `docs:`, `test:`, `refactor:`.
Body (if needed): *why*, not *what*.

## Pull requests

Small, single-purpose, tested. The template asks for benchmark impact — fill it honestly.
