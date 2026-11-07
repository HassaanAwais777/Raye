---
name: Bug report
about: Something in Hisaab misbehaves — an engine, the recommender, the bridge or the dashboard
labels: bug
---

**What happened?**
A clear description. What did you expect, what did you get instead?

**Where**
- [ ] generator / data
- [ ] metrics (cleaning, aggregation, formulas)
- [ ] engines — which one? `pandas / polars / spark / mapreduce / mapreduce-parallel`
- [ ] recommender (curves, water-filling, baselines)
- [ ] sentiment bridge (Raye export, factors, product board)
- [ ] API
- [ ] frontend dashboard
- [ ] benchmark harness / cost model

**Reproduction**
Steps or a snippet (dataset size, locale, budget, seed):

```python
# minimal repro
```

**Environment**
- OS:
- Python version (`python --version`):
- Hisaab commit (`git rev-parse --short HEAD`):

**Logs / screenshots**
Anything from `pytest -q`, uvicorn or the browser console that helps.
