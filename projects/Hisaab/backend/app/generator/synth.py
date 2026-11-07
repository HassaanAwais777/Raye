"""Synthetic ad-performance data generator (vectorised, up to 10M+ rows).

Design goals
------------
1. Realism: platform-specific CTR/CPC/CVR economics, weekday + seasonal effects,
   campaign quality spread, city purchasing-power tiers, lognormal noise.
2. Saturation signal: within each (day, platform) budget pool the marginal conversion
   rate decays with cumulative spend, so weekly revenue-vs-spend points trace a concave
   response curve — the signal the L3 recommender fits.
3. Data-quality traps (on purpose): ~1% impression-fraud rows (huge impressions, zero
   clicks), ~2% viral outliers, ~0.5% exact duplicates — the metrics layer must clean.
4. Bounded memory: rows are produced in chunks (default 1M) and streamed to
   Parquet/CSV, so 10M-row generation never exceeds a few hundred MB.
"""
from __future__ import annotations

import gc
from datetime import date, timedelta
from typing import Iterator, Dict

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from .locales import CAMPAIGNS, PLATFORMS, LocalePack, get_locale, AGE_BANDS

COLUMNS = ("date", "campaign", "platform", "impressions", "clicks", "spend",
           "conversions", "revenue", "age", "gender", "city", "device")
DAYS_BACK = 365
SATURATION_DEPTH = 0.45          # marginal CVR decay across a day's budget pool
BOT_FRACTION = 0.01
VIRAL_FRACTION = 0.02
DUP_FRACTION = 0.005


def _season_multiplier(lp: LocalePack, month: np.ndarray) -> np.ndarray:
    """month: int months 1..12 → multiplier array (default 1.0)."""
    mult = np.ones(month.shape, dtype=np.float64)
    # months are 1..12; seasons defined by inclusive mm ranges (handles 08..09 spans)
    for _, start_mm, end_mm, m in lp.seasons:
        s, e = int(start_mm), int(end_mm)
        mask = (month >= s) & (month <= e) if s <= e else ((month >= s) | (month <= e))
        mult[mask] *= m
    return mult


def _pools(lp: LocalePack, rng: np.random.Generator, d0: date) -> Dict[str, np.ndarray]:
    """Daily spend pool per (day, platform) with weekday, seasonal and yearly noise."""
    days = np.array([d0 + timedelta(days=i) for i in range(DAYS_BACK)])
    month = np.array([d.month for d in days])
    weekday = np.array([d.weekday() for d in days])          # 0=Mon .. 6=Sun
    wk = np.where(weekday >= 5, 1.10, 1.0)                   # weekend bump
    season = _season_multiplier(lp, month)
    yearly = rng.lognormal(0.0, 0.22, DAYS_BACK)
    pools = {}
    for p in PLATFORMS:
        pools[p] = lp.daily_spend[p] * wk * season * yearly
    return pools


def _city_factors(lp: LocalePack) -> np.ndarray:
    """Purchasing-power multiplier per city (top-3 by weight get a premium)."""
    w = np.array([c[1] for c in lp.cities])
    order = np.argsort(-w)
    f = np.full(len(w), 0.90)
    f[order[:3]] = 1.12
    f[order[3:6]] = 1.00
    return f


def generate_chunk(n: int, lp: LocalePack, rng: np.random.Generator,
                   pools: Dict[str, np.ndarray], city_names: list,
                   city_factors: np.ndarray, day0: date) -> Dict[str, np.ndarray]:
    """Generate one chunk of exactly n rows (vectorised, duplicates included)."""
    n_dup = int(DUP_FRACTION * n)                # exact duplicates appended at the end
    m = n - n_dup                                 # base rows actually simulated

    # --- which (day, platform) does each row belong to? (probability ∝ daily pool)
    pool_matrix = np.stack([pools[p] for p in PLATFORMS])            # 5 × 365
    combo_p = pool_matrix / pool_matrix.sum()                         # joint probability
    combo = rng.choice(pool_matrix.size, size=m, p=combo_p.ravel())
    plat_idx = (combo // DAYS_BACK).astype(np.int8)
    day_idx = (combo % DAYS_BACK).astype(np.int32)

    # --- spend: row's share of its (day, platform) pool × lognormal noise
    counts = np.bincount(combo, minlength=pool_matrix.size).astype(np.float64)
    n_group = counts[combo]
    pool_of_row = pool_matrix.ravel()[combo]
    spend = (pool_of_row / n_group) * rng.lognormal(0.0, 0.12, m)

    # --- saturation: rank rows within (day, platform) by spend order (proxy: random tiebreak)
    order = np.lexsort((rng.random(m), combo))
    u = np.empty(m)
    sorted_combo = combo[order]
    boundaries = np.flatnonzero(np.diff(sorted_combo)) + 1
    starts = np.concatenate(([0], boundaries))
    ends = np.concatenate((boundaries, [m]))
    for s, e in zip(starts, ends):
        mm = e - s
        u[order[s:e]] = ((np.arange(mm) + 0.5) / mm) if mm > 1 else 0.5
    cvr_decay = 1.0 - SATURATION_DEPTH * u ** 1.5                     # ∈ [0.65, 1.0]

    # --- campaign (within platform) — a campaign belongs to exactly one platform
    camp_idx = np.empty(m, dtype=np.int64)
    for i, p in enumerate(PLATFORMS):
        sel = np.flatnonzero(plat_idx == i)
        if sel.size:
            camp_idx[sel] = rng.choice(len(CAMPAIGNS[p]), size=sel.size)
    all_names = [nm for p in PLATFORMS for nm in CAMPAIGNS[p]]
    base_of_platform = {}
    off = 0
    for i, p in enumerate(PLATFORMS):
        base_of_platform[i] = off
        off += len(CAMPAIGNS[p])
    camp_global = camp_idx + np.array([base_of_platform[i] for i in plat_idx])
    campaign = np.array(all_names, dtype=object)[camp_global]

    # --- campaign quality factor (drives ROAS spread)
    q_by_camp = rng.normal(1.0, 0.18, len(all_names)).clip(0.6, 1.5)
    q = q_by_camp[camp_global]

    # --- demographics (platform-conditional)
    city_i = rng.choice(len(city_names), size=m, p=np.array([c[1] for c in lp.cities]))
    city = np.array(city_names, dtype=object)[city_i]
    city_f = city_factors[city_i]

    age = np.empty(m, dtype=object)
    gender = np.empty(m, dtype=object)
    device = np.empty(m, dtype=object)
    for i, p in enumerate(PLATFORMS):
        sel = plat_idx == i
        if not sel.any():
            continue
        age[sel] = np.array(AGE_BANDS, dtype=object)[
            rng.choice(len(AGE_BANDS), size=int(sel.sum()), p=lp.age[p])]
        g = lp.gender[p]
        gender[sel] = np.array(("male", "female", "unknown"), dtype=object)[
            rng.choice(3, size=int(sel.sum()), p=g)]
        d = lp.device[p]
        device[sel] = np.array(("mobile", "desktop", "tablet"), dtype=object)[
            rng.choice(3, size=int(sel.sum()), p=d)]

    # --- funnel economics
    ctr_v = np.array([lp.ctr[p] for p in PLATFORMS])[plat_idx]
    cvr_v = np.array([lp.cvr[p] for p in PLATFORMS])[plat_idx]
    cpc_v = np.array([lp.cpc[p] for p in PLATFORMS])[plat_idx]

    # impressions via CPC target: impressions ≈ spend / (cpc × ctr) [CPM is implied]
    imp_mean = spend / (cpc_v * ctr_v)
    impressions = np.maximum(1, (imp_mean * rng.lognormal(0.0, 0.10, m))).astype(np.int64)
    clicks = np.maximum(0, (impressions * ctr_v * rng.lognormal(0.0, 0.18, m))).astype(np.int64)
    # conversions are a COUNTING process → Poisson draw (unbiased; int truncation would
    # zero out the ~0.5-conv/row regime and crush blended ROAS 8×)
    conversions = rng.poisson(np.maximum(0.0, clicks * cvr_v * cvr_decay * q))
    aov = lp.aov_base * city_f
    revenue = conversions * aov * rng.lognormal(0.0, 0.28, m)

    # --- injected data-quality traps
    bot = rng.random(m) < BOT_FRACTION
    impressions = np.where(bot, impressions * rng.integers(20, 40, m), impressions)
    clicks = np.where(bot, 0, clicks)
    conversions = np.where(bot, 0, conversions)
    revenue = np.where(bot, 0.0, revenue)

    viral = (rng.random(m) < VIRAL_FRACTION) & ~bot
    conversions = np.where(viral, conversions * 4, conversions)
    revenue = np.where(viral, revenue * 3.0, revenue)

    # --- dates
    dates = (np.datetime64(day0) + day_idx.astype("timedelta64[D]"))

    rows = {
        "date": dates, "campaign": campaign, "platform": np.array(PLATFORMS, dtype=object)[plat_idx],
        "impressions": impressions, "clicks": clicks, "spend": spend,
        "conversions": conversions, "revenue": revenue,
        "age": age, "gender": gender, "city": city, "device": device,
    }

    # --- exact duplicates (append copies so the chunk totals exactly n rows)
    if n_dup:
        take = rng.choice(m, size=n_dup, replace=False)
        rows = {k: np.concatenate([v, v[take]]) for k, v in rows.items()}
    return rows


def iter_generated(rows: int, locale: str = "pk", seed: int = 42,
                   chunk_size: int = 1_000_000) -> Iterator[Dict[str, np.ndarray]]:
    """Yield `{column: np.ndarray}` chunks totalling `rows` rows."""
    lp = get_locale(locale)
    rng = np.random.default_rng(seed)
    day0 = date.today() - timedelta(days=DAYS_BACK - 1)
    pools = _pools(lp, rng, day0)
    city_names = [c[0] for c in lp.cities]
    city_f = _city_factors(lp)
    made = 0
    while made < rows:
        n = min(chunk_size, rows - made)
        yield generate_chunk(n, lp, rng, pools, city_names, city_f, day0)
        made += n
        gc.collect()


SCHEMA = pa.schema([
    ("date", pa.date32()), ("campaign", pa.string()), ("platform", pa.string()),
    ("impressions", pa.int64()), ("clicks", pa.int64()), ("spend", pa.float64()),
    ("conversions", pa.int64()), ("revenue", pa.float64()),
    ("age", pa.string()), ("gender", pa.string()), ("city", pa.string()), ("device", pa.string()),
])


def write_parquet(path, rows_total: int, locale: str = "pk", seed: int = 42,
                  chunk_size: int = 1_000_000) -> int:
    """Stream `rows_total` generated rows to a Parquet file; returns rows written."""
    written = 0
    with pq.ParquetWriter(path, SCHEMA, compression="zstd") as w:
        for chunk in iter_generated(rows_total, locale, seed, chunk_size):
            arrays = [pa.array(chunk[c], type=fld.type) for c, fld in zip(COLUMNS, SCHEMA)]
            w.write_table(pa.Table.from_arrays(arrays, schema=SCHEMA))
            written += len(chunk["date"])
    return written


def write_csv(path, rows_total: int, locale: str = "pk", seed: int = 42,
              chunk_size: int = 500_000) -> int:
    """Stream generated rows to CSV (same seed ⇒ same data as write_parquet)."""
    written = 0
    with open(path, "w", encoding="utf-8") as f:
        f.write(",".join(COLUMNS) + "\n")
        for chunk in iter_generated(rows_total, locale, seed, chunk_size):
            n = len(chunk["date"])
            dates = chunk["date"].astype("datetime64[D]").astype(str)
            frame_cols = [dates if c == "date" else
                          (np.char.mod("%.4f", chunk[c]) if c in ("spend", "revenue")
                           else chunk[c].astype(str)) for c in COLUMNS]
            out = np.stack(frame_cols, axis=1)
            np.savetxt(f, out, fmt="%s", delimiter=",")
            written += n
    return written
