<!-- Title: <type>: <short summary> — e.g. "feat: TikTok CPM prior in the generator" -->

## What does this PR change?

<!-- One or two sentences: the what and the why. -->

## Type

- [ ] feat (new capability)
- [ ] fix (bug fix)
- [ ] perf (benchmark-relevant)
- [ ] docs
- [ ] refactor (no behaviour change)
- [ ] test

## Checklist

- [ ] `cd backend && pytest -q` — all tests pass, new behaviour has a test
- [ ] Engines return **raw sums only** (ratios belong to `app/metrics/formulas.py`)
- [ ] Any new signal stays inside documented bounds (sentiment factors ±cap, water-fill Σx = B)
- [ ] Benchmark-affecting changes note the machine + repeat count
- [ ] Docs updated (`README`, `docs/ARCHITECTURE.md`, `docs/API.md` where relevant)
- [ ] No new mandatory dependency without discussion (`requirements*.txt`)

## Benchmark impact (if any)

<!-- Paste the relevant before/after rows from scripts/benchmark.py output. -->

| Engine | before | after |
|---|---|---|
|  |  |  |
