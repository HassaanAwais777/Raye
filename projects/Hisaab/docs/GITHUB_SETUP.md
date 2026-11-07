# GitHub Setup — publishing Hisaab

Step-by-step to push this project to **https://github.com/HassaanAwais777/Hisaab**
with everything wired (Actions CI, templates, citation, topics).

## 1. Create the repository

1. GitHub → **New repository** → name `Hisaab`, description:
   *Digital-ad budget optimization on big data — Pandas/Polars/MapReduce/PySpark under one
   contract, water-filling budget allocation, Raye sentiment bridge.*
2. Public, **do not** initialize with a README (this project already has one).
3. Create it, then:

```bash
cd Hisaab
git init -b main
git add .
git commit -m "feat: Hisaab 1.0 — four-engine benchmark, water-filling recommender, Raye sentiment bridge"

git remote add origin https://github.com/HassaanAwais777/Hisaab.git
git push -u origin main
```

If git asks for identity:

```bash
git config --global user.name  "HassaanAwais777"
git config --global user.email "your-email@example.com"
```

## 2. Repository settings worth flipping

- **About panel**: description above + website `https://github.com/HassaanAwais777/Raye`
  (companion project) + topics:
  `big-data`, `mapreduce`, `spark`, `polars`, `pandas`, `fastapi`, `react`,
  `budget-optimization`, `marketing-analytics`, `sentiment-analysis`.
- **Settings → General → Pull Requests**: allow squash merge, auto-delete head branches.
- **Settings → Branches**: protect `main` (require PR before merging once collaborators exist).
- **Settings → Actions**: keep "Allow all actions" (the CI workflow is read-only).

## 3. CI (already included)

`.github/workflows/ci.yml` runs three jobs on every push/PR:

| Job | What it proves |
|---|---|
| core | full test suite on pandas/polars/mapreduce (Python 3.12) |
| spark | the Spark parity test with a real JVM (Temurin 17) |
| frontend | `npm run build` of the dashboard |

Green badge after the first push: `![CI](https://github.com/HassaanAwais777/Hisaab/actions/workflows/ci.yml/badge.svg)`
— add it to the README shields row if you like.

## 4. Community files (already included)

`LICENSE` (MIT) · `CONTRIBUTING.md` · `SECURITY.md` · `CITATION.cff` ·
issue templates (bug / feature) · PR template. GitHub renders CITATION.cff under
**Cite this repository** automatically.

## 5. Large-file notes

Committed on purpose (small, load-bearing):
`backend/data/raye/raye_sentiment_aggregates.json` (6 KB) and
`backend/data/raye/raye_sentiment_sample.csv` (~1.6 MB), plus `backend/results/*`
(benchmark JSON/markdown/chart/cost model — they are the evidence).

Excluded by `.gitignore` (regenerable): parquet/csv datasets, the full 210k Raye CSV
(`scripts/export_raye.py --full` recreates it), `hisaab.db`, `node_modules`, `dist/`.

If you ever see `remote: error: GH007` / file-too-large, you probably committed a dataset:
`git rm --cached backend/data/*.csv backend/data/*.parquet`, commit, push.

## 6. Release tag

```bash
git tag -a v1.0.0 -m "Hisaab 1.0 — engines, recommender, sentiment bridge, dashboard"
git push origin v1.0.0
```

GitHub → Releases → **Draft new release** → choose the tag →
*"Four compute engines under one aggregation contract; L3 water-filling recommender
(+11.7% expected incremental revenue vs L1 on the 1M-row demo); Raye sentiment bridge
over 210,511 comments; React dashboard."* → Publish.

## 7. Link the two projects

In **both** Raye's and Hisaab's READMEs the companion link exists. Consider a GitHub
topic (`companion:raye` / `companion:hisaab`) or pinning both repos on your profile —
the two-project story (listen → decide) is the strongest elevator pitch you have.
