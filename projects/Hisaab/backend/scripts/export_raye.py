"""Export Raye's sentiment analysis results into Hisaab's sentiment bridge format.

Raye (github.com/HassaanAwais777/Raye) is this repo's companion project: a
multilingual (EN / Urdu / Roman-Urdu) sentiment pipeline that analysed 210k+
product comments from YouTube and Reddit. This script reads Raye's SQLite store
and produces the two committed artefacts the bridge consumes:

  data/raye/raye_sentiment_aggregates.json   per-platform / global / per-product
                                             brand-health aggregates (tiny, committed)
  data/raye/raye_sentiment_sample.csv        stratified 25k-row sample for the
                                             dashboard drill-down (committed)
  data/raye/raye_sentiment_full.csv          full 210k export (optional, --full)

Usage:
  python scripts/export_raye.py --db /path/to/raye.db          # default: try known spots
  python scripts/export_raye.py --db ... --full --sample 25000
"""
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# likes+1 so zero-like comments keep weight 1 while engagement amplifies the voice
def weight(likes: int) -> float:
    return float(likes) + 1.0


def agg_stats(rows) -> dict:
    """rows: iterable of (sentiment, score, likes)."""
    n = 0
    w_sum = 0.0
    ws_sum = 0.0
    s_sum = 0.0
    by_sent = defaultdict(int)
    likes_sum = 0
    for sentiment, score, likes in rows:
        n += 1
        w = weight(likes)
        w_sum += w
        ws_sum += w * float(score)
        s_sum += float(score)
        by_sent[sentiment] += 1
        likes_sum += int(likes)
    if n == 0:
        return {"n": 0, "net": 0.0, "net_weighted": 0.0,
                "by_sentiment": {}, "likes": 0}
    return {
        "n": n,
        "net": round(s_sum / n, 4),                      # plain mean score
        "net_weighted": round(ws_sum / w_sum, 4),        # engagement-weighted brand health
        "by_sentiment": dict(sorted(by_sent.items())),
        "likes": likes_sum,
    }


def export(db_path: str, out_dir: Path, sample_rows: int, full: bool) -> dict:
    con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = con.cursor()

    products = {pid: (slug, name, cat) for pid, slug, name, cat in
                cur.execute("SELECT id, slug, name, category FROM Product")}

    # ---- per-platform + global + per-product aggregation (single pass) --------
    plat_rows = defaultdict(list)
    prod_rows = defaultdict(list)
    all_rows = []
    q = ("SELECT c.platform, c.productId, p.slug, c.lang, c.sentiment, c.score, "
         "c.confidence, c.likes, c.postedAt FROM Comment c JOIN Product p "
         "ON c.productId = p.id")
    t0 = time.time()
    n_total = 0
    for (platform, pid, slug, lang, sentiment, score, confidence, likes, posted) in cur.execute(q):
        n_total += 1
        rec = (platform, slug, lang, sentiment, float(score), float(confidence),
               int(likes), int(posted or 0))
        plat_rows[platform].append((sentiment, score, likes))
        prod_rows[slug].append((sentiment, score, likes))
        all_rows.append(rec)
    print(f"read {n_total:,} comments in {time.time()-t0:.1f}s")

    langs = agg_stats([(s, sc, lk) for (_, _, _, s, sc, _, lk, _) in all_rows])
    platforms = {p: agg_stats(v) for p, v in sorted(plat_rows.items())}
    global_stats = agg_stats([(s, sc, lk) for (_, _, _, s, sc, _, lk, _) in all_rows])
    prod_stats = []
    for slug, v in sorted(prod_rows.items(), key=lambda kv: -len(kv[1])):
        slug_name_cat = next(((nm, ct) for s2, nm, ct in products.values() if s2 == slug),
                             (slug, ""))
        st = agg_stats(v)
        prod_stats.append({"slug": slug, "name": slug_name_cat[0], "category": slug_name_cat[1], **st})

    out_dir.mkdir(parents=True, exist_ok=True)

    aggregates = {
        "provenance": {
            "source_project": "Raye — multilingual sentiment analysis "
                              "(github.com/HassaanAwais777/Raye)",
            "source_db": str(db_path),
            "corpus": "Raye demo corpus (synthetic, isDemo=true) — labels produced by "
                      "Raye's EN/Urdu/Roman-Urdu lexicon + rules pipeline",
            "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "comments_total": n_total,
            "score_range": [-1.0, 1.0],
            "brand_health": "net_weighted = likes-weighted mean of Raye's comment score",
        },
        "global": global_stats,
        "platforms": platforms,
        "languages": langs,
        "products": prod_stats,
    }
    agg_path = out_dir / "raye_sentiment_aggregates.json"
    agg_path.write_text(json.dumps(aggregates, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {agg_path} ({agg_path.stat().st_size//1024} KB)")

    # ---- stratified sample CSV (platform × sentiment proportional) -----------
    strata = defaultdict(list)
    for rec in all_rows:
        strata[(rec[0], rec[3])].append(rec)
    frac = sample_rows / max(1, n_total)
    take: list = []
    for key, rows in sorted(strata.items()):
        k = round(len(rows) * frac)
        if k:
            step = len(rows) / k
            take.extend(rows[int(i * step)] for i in range(k))   # deterministic stride
    sample_path = out_dir / "raye_sentiment_sample.csv"
    with sample_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["platform", "product_slug", "lang", "sentiment", "score",
                    "confidence", "likes", "posted_at"])
        w.writerows(take)
    print(f"wrote {sample_path} ({len(take):,} rows, {sample_path.stat().st_size//1024} KB)")

    if full:
        full_path = out_dir / "raye_sentiment_full.csv"
        with full_path.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["platform", "product_slug", "lang", "sentiment", "score",
                        "confidence", "likes", "posted_at"])
            w.writerows(all_rows)
        print(f"wrote {full_path} ({n_total:,} rows, {full_path.stat().st_size//1024//1024} MB)")

    con.close()
    return aggregates


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default="", help="path to Raye's SQLite database")
    ap.add_argument("--out", default="", help="output dir (default: <repo>/data/raye)")
    ap.add_argument("--sample", type=int, default=25_000)
    ap.add_argument("--full", action="store_true", help="also write the full 210k CSV")
    args = ap.parse_args(argv)

    root = Path(__file__).resolve().parents[1]
    db = args.db
    if not db:
        for cand in (root.parents[1] / "db" / "custom.db",        # raye web-app db
                     root.parents[1] / "raye" / "raye.db",
                     root / "data" / "raye.db"):
            if cand.exists():
                db = str(cand)
                break
    if not db or not Path(db).exists():
        print("ERROR: Raye SQLite DB not found — pass --db /path/to/raye.db", file=sys.stderr)
        return 1
    out_dir = Path(args.out) if args.out else root / "data" / "raye"
    aggs = export(db, out_dir, args.sample, args.full)

    print("\n=== brand health (likes-weighted mean score) ===")
    print(f"global: {aggs['global']['net_weighted']:+.4f}  (n={aggs['global']['n']:,})")
    for p, st in aggs["platforms"].items():
        print(f"{p:8s}: {st['net_weighted']:+.4f}  (n={st['n']:,})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
