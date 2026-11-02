"""Evidence-based verdict builder with the honesty gate.

Aggregates analyzed comments into: overall verdict, confidence breakdown,
aspect scorecards, language distribution, evidence quotes (each traceable to
its source), platform stats, warnings and recommendations.
"""
import math
import time
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional

from ..config import settings
from ..nlp.langid import LANG_LABELS
from ..scraping.registry import ADAPTERS

METHODOLOGY_NOTE = (
    "Sentiment is computed with a transparent lexicon + rules engine (multilingual word "
    "weights, negation windows, contrast clauses). It is auditable but heuristic — always "
    "cross-check the linked evidence comments before deciding."
)


def _engagement_weight(likes: int) -> float:
    return 1.0 + math.log10(1 + max(0, likes)) / 2.0


def _share(n: int, total: int) -> float:
    return round(100.0 * n / total, 1) if total else 0.0


def build_result(query: str, comments: List[Dict[str, Any]], platform_stats: Dict[str, Dict],
                 warnings: List[str], duration_seconds: float,
                 min_reliable_n: Optional[int] = None) -> Dict[str, Any]:
    min_reliable_n = min_reliable_n or settings.min_reliable_n
    n = len(comments)
    sent_counts = Counter(c["sentiment"] for c in comments)
    pos_n, neg_n = sent_counts.get("positive", 0), sent_counts.get("negative", 0)
    mixed_n, neutral_n = sent_counts.get("mixed", 0), sent_counts.get("neutral", 0)
    pos_share, neg_share = pos_n / max(1, n), neg_n / max(1, n)

    weighted = [c["score"] * _engagement_weight(c.get("likes", 0)) for c in comments]
    weights = [_engagement_weight(c.get("likes", 0)) for c in comments]
    overall_score = round(sum(weighted) / sum(weights), 3) if comments else 0.0

    platforms_ok = [p for p, s in platform_stats.items() if s.get("ok")]
    platform_list = []
    for pid, stat in platform_stats.items():
        platform_list.append({
            "id": pid, "label": ADAPTERS[pid].label, "experimental": ADAPTERS[pid].experimental,
            "fetched": stat.get("fetched", 0), "ok": stat.get("ok", False),
            "error": stat.get("error"),
        })

    # ---- confidence factors (all explainable) ----
    sample_factor = min(1.0, n / max(1, settings.ideal_n))
    clarity_factor = min(1.0, abs(pos_share - neg_share) / 0.5) if (pos_share + neg_share) > 0 else 0.0
    diversity_factor = min(1.0, len(platforms_ok) / 3.0)
    lang_counts = Counter(c.get("lang", "other") for c in comments)
    known_lang = sum(v for k, v in lang_counts.items() if k in LANG_LABELS and k != "other")
    language_factor = known_lang / max(1, n)
    confidence = round(0.45 * sample_factor + 0.25 * clarity_factor
                       + 0.15 * diversity_factor + 0.15 * language_factor, 3)
    tier = ("high" if confidence >= 0.75 else "medium" if confidence >= 0.5
            else "low" if confidence >= 0.3 else "insufficient")

    # ---- honesty gate ----
    sufficient = n >= min_reliable_n and bool(platforms_ok)
    warnings = list(warnings)
    if not platforms_ok:
        warnings.append("No platform returned any comments — the verdict cannot be trusted.")
    if n < min_reliable_n:
        warnings.append(
            f"Only {n} analyzable comments collected (minimum for a reliable verdict: {min_reliable_n}).")
    exp_only = bool(platform_list) and all(p["experimental"] for p in platform_list if p["fetched"] > 0)
    if exp_only and n > 0:
        warnings.append("All data came from experimental adapters; coverage may be partial.")
    warnings.append(METHODOLOGY_NOTE)

    if not sufficient:
        recommendations = [
            f"Increase the comment cap (current result: {n} comments).",
            "Enable more platforms (e.g. add Reddit alongside YouTube, or the experimental store adapters).",
            "Broaden the search query — include the full product name + 'review' (e.g. 'Galaxy S24 review').",
            "Raise sources per platform so more videos/threads are crawled.",
        ]
        label = "Insufficient evidence"
        headline = f"Not enough real comments to conclude about “{query}”."
        summary = (f"Raye collected {n} analyzable comments, below the reliability threshold of "
                   f"{min_reliable_n}. Rather than invent a conclusion, Raye reports this "
                   f"transparently — retry with the recommendations below to gather more evidence.")
    else:
        recommendations = []
        if overall_score >= 0.15:
            label = "Positive — buy-leaning"
            headline = f"Reviewers broadly respond positively to “{query}”."
        elif overall_score <= -0.15:
            label = "Negative — avoid-leaning"
            headline = f"Reviewers broadly respond negatively to “{query}”."
        else:
            label = "Mixed — divided feedback"
            headline = f"Feedback on “{query}” is clearly divided — notable praise and criticism in similar measure."
        summary = (
            f"{n} real comments analyzed across {len(platforms_ok)} platform(s): "
            f"{_share(pos_n, n)}% positive, {_share(neg_n, n)}% negative, "
            f"{_share(mixed_n, n)}% mixed, {_share(neutral_n, n)}% neutral. "
            f"Every claim below links back to the exact source comment."
        )

    # ---- aspect scorecards ----
    aspect_acc: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"label": "", "mentions": 0, "sent": Counter(), "score": 0.0, "quote": None,
                 "quote_score": -999.0})
    for c in comments:
        w = _engagement_weight(c.get("likes", 0)) * max(0.2, abs(c["score"]))
        for a in c.get("aspects", []):
            acc = aspect_acc[a["name"]]
            acc["label"] = a["label"]
            acc["mentions"] += 1
            acc["sent"][a["sentiment"]] += 1
            acc["score"] += a.get("score", 0.0)
            if len(c.get("text_raw", "")) >= 40 and w > acc["quote_score"]:
                acc["quote_score"] = w
                acc["quote"] = _evidence_item(c)
    aspects_out = []
    for name, acc in aspect_acc.items():
        mentions = acc["mentions"]
        avg = round(acc["score"] / mentions, 3) if mentions else 0.0
        dominant = acc["sent"].most_common(1)[0][0] if acc["sent"] else "neutral"
        aspects_out.append({
            "name": name, "label": acc["label"], "mentions": mentions,
            "positive": acc["sent"].get("positive", 0), "negative": acc["sent"].get("negative", 0),
            "mixed": acc["sent"].get("mixed", 0), "neutral": acc["sent"].get("neutral", 0),
            "dominant": dominant, "avg_score": avg,
            "status": "ok" if mentions >= settings.min_aspect_mentions else "insufficient_mentions",
            "sample_quote": acc["quote"],
        })
    aspects_out.sort(key=lambda a: -a["mentions"])

    # ---- evidence quotes ----
    def pick(kind: str, count: int) -> List[Dict[str, Any]]:
        pool = [c for c in comments if c["sentiment"] == kind and len(c.get("text_raw", "")) >= 40]
        pool.sort(key=lambda c: c["score"] * _engagement_weight(c.get("likes", 0)),
                  reverse=(kind == "positive"))
        return [_evidence_item(c) for c in pool[:count]]

    evidence = {"positive": pick("positive", 3), "negative": pick("negative", 3),
                "mixed": pick("mixed", 2)}

    # ---- sources ----
    src_acc: Dict[tuple, Dict[str, Any]] = {}
    for c in comments:
        s = c.get("source", {})
        key = (s.get("platform"), s.get("source_id"))
        entry = src_acc.setdefault(key, {
            "platform": s.get("platform"), "source_id": s.get("source_id"),
            "title": s.get("title"), "url": s.get("url"), "channel": s.get("channel"),
            "comment_url": s.get("comment_url"), "comments": 0})
        entry["comments"] += 1
    sources = sorted(src_acc.values(), key=lambda s: -s["comments"])

    languages = [{"lang": lang, "label": LANG_LABELS.get(lang, lang), "count": cnt,
                  "share": _share(cnt, n)}
                 for lang, cnt in lang_counts.most_common()]

    return {
        "query": query,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "verdict": {
            "status": "sufficient" if sufficient else "insufficient_evidence",
            "label": label,
            "headline": headline,
            "summary": summary,
            "overall_score": overall_score,
            "sentiment_counts": {"positive": pos_n, "negative": neg_n, "mixed": mixed_n,
                                 "neutral": neutral_n},
            "shares": {"positive": _share(pos_n, n), "negative": _share(neg_n, n),
                       "mixed": _share(mixed_n, n), "neutral": _share(neutral_n, n)},
            "confidence": {"score": confidence, "tier": tier, "min_reliable_n": min_reliable_n,
                           "factors": {"sample_size": round(sample_factor, 3),
                                       "verdict_clarity": round(clarity_factor, 3),
                                       "platform_diversity": round(diversity_factor, 3),
                                       "language_coverage": round(language_factor, 3)}},
            "recommendations": recommendations,
        },
        "totals": {"fetched": sum(s.get("fetched", 0) for s in platform_stats.values()),
                   "analyzed": n, "duplicates_removed": 0,
                   "sources": len(sources), "duration_seconds": round(duration_seconds, 1)},
        "platforms": platform_list,
        "languages": languages,
        "aspects": aspects_out,
        "evidence": evidence,
        "sources": sources[:50],
        "warnings": warnings,
    }


def _evidence_item(c: Dict[str, Any]) -> Dict[str, Any]:
    s = c.get("source", {})
    return {
        "comment_id": c["id"],
        "text": c["text_raw"][:400],
        "sentiment": c["sentiment"],
        "score": c["score"],
        "likes": c.get("likes", 0),
        "lang": c.get("lang"),
        "platform": s.get("platform"),
        "source_title": s.get("title"),
        "source_url": s.get("url"),
        "comment_url": s.get("comment_url"),
    }
