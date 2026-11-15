"""Findings engine — converts NLP + clustering results into evidence-based
business intelligence. Each finding is traceable to the source data that
produced it: description, supporting metrics, evidence, methodology,
confidence, recommended action, and a provenance label.

This is the capstone that ties Project A (sentiment) and Project 3 (clustering)
into actionable insight cards.
"""
from __future__ import annotations

from typing import Any

from ..nlp.pipeline import analyze_batch
from ..audience.engine import cluster as run_cluster

# ---------------------------------------------------------------------------
# Finding assembly
# ---------------------------------------------------------------------------


def _finding(
    fid: str,
    title: str,
    ftype: str,
    description: str,
    provenance: str,
    metrics: list[dict],
    evidence: list[dict] | None = None,
    methodology: str = "",
    confidence: float = 0.0,
    action: str = "",
) -> dict[str, Any]:
    return {
        "id": fid,
        "type": ftype,
        "title": title,
        "description": description,
        "provenance": provenance,
        "supporting_metrics": metrics,
        "evidence": evidence or [],
        "methodology": methodology,
        "confidence": round(confidence, 2),
        "recommended_action": action,
    }


def generate(
    texts: list[str],
    aspect_catalog: str = "general",
    cluster_method: str = "kmeans",
) -> dict[str, Any]:
    """Run NLP + clustering on a comment set and synthesize finding cards."""
    n = len(texts)
    if n == 0:
        return {
            "findings": [],
            "provenance": "INSUFFICIENT_DATA",
            "error": "No comments provided.",
        }

    nlp = analyze_batch(texts, aspect_catalog)
    dist = nlp["distribution"]
    dist_pct = nlp["distribution_pct"]
    avg = nlp["avg_score"]
    topics = nlp["topics"]
    results = nlp["results"]

    findings: list[dict[str, Any]] = []

    # --- 1. Overall sentiment verdict ---
    dominant = max(dist, key=dist.get) if dist else "uncertain"
    pos = dist.get("positive", 0)
    neg = dist.get("negative", 0)
    mixed = dist.get("mixed", 0)
    if pos > neg and pos > 0:
        verdict = "Positive-leaning audience"
        action = "Amplify positive themes in creative; use satisfied quotes as social proof in ads."
        conf = min(1.0, pos / max(1, n) * 1.5)
    elif neg > pos and neg > 0:
        verdict = "Negative-leaning audience"
        action = "Prioritize complaint resolution; address the top negative aspects before scaling spend."
        conf = min(1.0, neg / max(1, n) * 1.5)
    else:
        verdict = "Divided / mixed audience"
        action = "Segment messaging — separate creatives for advocates vs. critics."
        conf = min(1.0, (mixed + min(pos, neg)) / max(1, n) * 1.5)
    findings.append(_finding(
        "F1", "Overall sentiment verdict", "sentiment",
        f"{verdict} across {n} comments. Average sentiment score {avg}. "
        f"Distribution: {dist_pct.get('positive',0)}% positive, "
        f"{dist_pct.get('negative',0)}% negative, {dist_pct.get('mixed',0)}% mixed.",
        "MODEL_PREDICTION",
        metrics=[
            {"label": "Sample size", "value": str(n)},
            {"label": "Avg score", "value": str(avg)},
            {"label": "Positive", "value": f"{dist_pct.get('positive',0)}%"},
            {"label": "Negative", "value": f"{dist_pct.get('negative',0)}%"},
        ],
        methodology="Multilingual lexicon + negation + contrast-clause sentiment (Raye pipeline). 5-class incl. uncertain.",
        confidence=conf,
        action=action,
    ))

    # --- 2. Most discussed topics ---
    if topics:
        top = topics[:5]
        findings.append(_finding(
            "F2", "Most discussed topics", "topics",
            "Top recurring terms across the comment sample, ranked by frequency.",
            "INFERENCE",
            metrics=[{"label": t["topic"], "value": str(t["count"])} for t in top],
            methodology="Token frequency after stopword removal and normalization.",
            confidence=min(1.0, top[0]["count"] / max(1, n)),
            action="Align creative and keyword targeting with the dominant discussion themes.",
        ))

    # --- 3. Top complaints ---
    neg_comments = [r for r in results if r["sentiment"] == "negative"]
    if neg_comments:
        neg_terms: dict[str, int] = {}
        for r in neg_comments:
            for a in r.get("aspects", []):
                if a["sentiment"] == "negative":
                    neg_terms[a["label"]] = neg_terms.get(a["label"], 0) + 1
        top_complaint_aspects = sorted(neg_terms.items(), key=lambda x: -x[1])[:3]
        findings.append(_finding(
            "F3", "Top complaints", "complaints",
            f"{len(neg_comments)} negative comments ({dist_pct.get('negative',0)}% of sample). "
            + (f"Concentrated on: {', '.join(f'{a} ({c})' for a, c in top_complaint_aspects)}."
               if top_complaint_aspects else "No aspect-specific complaints detected."),
            "INFERENCE",
            metrics=[{"label": "Negative comments", "value": str(len(neg_comments))}] +
                    ([{"label": a, "value": str(c)} for a, c in top_complaint_aspects] if top_complaint_aspects else []),
            evidence=[{"label": "Representative", "value": c["text"][:140]} for c in neg_comments[:3]],
            methodology="Aspect-based sentiment (ABSA) over the configured aspect catalog.",
            confidence=min(1.0, len(neg_comments) / max(1, n)),
            action="Address the most-complained aspects in product messaging or fixes before scaling ad spend.",
        ))

    # --- 4. Top praise ---
    pos_comments = [r for r in results if r["sentiment"] == "positive"]
    if pos_comments:
        findings.append(_finding(
            "F4", "Top praise", "praise",
            f"{len(pos_comments)} positive comments ({dist_pct.get('positive',0)}% of sample). "
            "These are candidate social-proof quotes for creative.",
            "INFERENCE",
            metrics=[{"label": "Positive comments", "value": str(len(pos_comments))}],
            evidence=[{"label": "Representative", "value": c["text"][:140]} for c in pos_comments[:3]],
            methodology="Sentiment classification + extraction of highest-confidence positive comments.",
            confidence=min(1.0, len(pos_comments) / max(1, n)),
            action="Use representative praise quotes as social proof in ad creative and landing pages.",
        ))

    # --- 5. Audience segments (clustering) ---
    if n >= 3:
        cl = run_cluster(texts, method=cluster_method)
        if cl.get("clusters"):
            seg_summary = "; ".join(
                f"{c['label']} ({c['size']}, {c['share']}%, avg {c['avg_sentiment_score']})"
                for c in cl["clusters"][:4]
            )
            findings.append(_finding(
                "F5", "Audience segments", "segments",
                f"{cl['n_clusters']} segments detected via {cl['method']}: {seg_summary}.",
                "INFERENCE",
                metrics=[
                    {"label": "Segments", "value": str(cl["n_clusters"])},
                    {"label": "Silhouette", "value": str(cl.get("silhouette", "n/a"))},
                ] + [{"label": c["label"], "value": f"{c['size']} ({c['share']}%)"} for c in cl["clusters"][:4]],
                evidence=[{"label": c["label"], "value": "; ".join(c["sample_comments"][:2])} for c in cl["clusters"][:3]],
                methodology=f"{cl['method']} on TF-IDF + sentiment + intent features. Segments are analytical clusters, not demographics.",
                confidence=0.4 + (cl.get("silhouette") or 0) * 0.5,
                action="Tailor creative per segment; allocate budget toward high-intent, positive segments.",
            ))

    # --- 6. Marketing opportunity (intent-driven) ---
    buy_signals = sum(1 for r in results if any(k in r["text"].lower() for k in ["buy", "price", "worth", "recommend", "deal", "khareed"]))
    if buy_signals > 0:
        findings.append(_finding(
            "F6", "Purchase-intent signals", "opportunity",
            f"{buy_signals} comments show purchase-intent or value language (buy/price/worth/recommend). "
            "Indicates a convertible audience subset worth targeting with performance creative.",
            "INFERENCE",
            metrics=[{"label": "Intent comments", "value": str(buy_signals)},
                     {"label": "Share of sample", "value": f"{round(buy_signals / n * 100, 1)}%"}],
            methodology="Heuristic intent-keyword detection over comment text.",
            confidence=min(1.0, buy_signals / max(1, n) * 2),
            action="Retarget intent-bearing audiences with conversion-focused formats (In-Stream for sales objective).",
        ))

    # --- 7. Sample sufficiency ---
    if n < 30:
        findings.append(_finding(
            "F7", "Sample sufficiency", "limitation",
            f"Only {n} comments analyzed. Findings are directional, not statistically robust. "
            "Collect more comments (target ≥ 150) for a reliable verdict.",
            "INSUFFICIENT_DATA",
            metrics=[{"label": "Sample size", "value": str(n)}, {"label": "Reliable threshold", "value": "150"}],
            methodology="Honesty gate: verdict confidence scales with sample size.",
            confidence=0.3,
            action="Expand the research plan — broaden keywords, add channels, extend the date range.",
        ))

    return {
        "findings": findings,
        "n_findings": len(findings),
        "n_comments": n,
        "sentiment_distribution": dist_pct,
        "provenance": "MODEL_PREDICTION",
        "disclaimer": "Every finding is traceable to the collected sample. Percentages represent the sample, not the entire YouTube audience.",
    }
