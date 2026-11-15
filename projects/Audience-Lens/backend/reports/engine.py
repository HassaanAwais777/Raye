"""Reports engine — composes the findings engine output into a structured,
evidence-based report with sections. The report is rendered to PDF (reportlab)
and DOCX (python-docx) by generator.py.

Every section carries its provenance label. No fabricated metrics — all numbers
come from the real findings engine run on the supplied comments.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from ..findings.engine import generate as generate_findings


def build_report(
    texts: list[str],
    meta: dict[str, Any] | None = None,
    aspect_catalog: str = "general",
    cluster_method: str = "kmeans",
) -> dict[str, Any]:
    """Build a structured report from a comment set.

    meta: {title, objective, prepared_by, country, industry}
    """
    meta = meta or {}
    findings = generate_findings(texts, aspect_catalog, cluster_method)

    if findings.get("error"):
        return {
            "error": findings["error"],
            "provenance": "INSUFFICIENT_DATA",
        }

    dist = findings["sentiment_distribution"]
    n = findings["n_comments"]
    cards = {f["id"]: f for f in findings["findings"]}

    # Assemble readable sections from the finding cards + raw findings data
    verdict = cards.get("F1", {})
    topics = cards.get("F2", {})
    complaints = cards.get("F3", {})
    praise = cards.get("F4", {})
    segments = cards.get("F5", {})
    opportunity = cards.get("F6", {})
    sufficiency = cards.get("F7", {})

    sections = [
        {
            "id": "executive_summary",
            "title": "Executive Summary",
            "provenance": verdict.get("provenance", "MODEL_PREDICTION"),
            "body": verdict.get("description", ""),
            "metrics": verdict.get("supporting_metrics", []),
            "confidence": verdict.get("confidence", 0),
        },
        {
            "id": "sentiment_distribution",
            "title": "Sentiment Distribution",
            "provenance": "MODEL_PREDICTION",
            "body": f"Across {n} analyzed comments, the sentiment split is: "
                    + ", ".join(f"{k} {v}%" for k, v in dist.items() if v > 0)
                    + ".",
            "metrics": [{"label": k, "value": f"{v}%"} for k, v in dist.items()],
        },
        {
            "id": "top_topics",
            "title": "Most Discussed Topics",
            "provenance": topics.get("provenance", "INFERENCE"),
            "body": topics.get("description", ""),
            "metrics": topics.get("supporting_metrics", []),
        },
        {
            "id": "complaints",
            "title": "Top Complaints",
            "provenance": complaints.get("provenance", "INFERENCE"),
            "body": complaints.get("description", "No significant complaints detected."),
            "metrics": complaints.get("supporting_metrics", []),
            "evidence": complaints.get("evidence", []),
            "recommended_action": complaints.get("recommended_action", ""),
        },
        {
            "id": "praise",
            "title": "Top Praise",
            "provenance": praise.get("provenance", "INFERENCE"),
            "body": praise.get("description", "No significant praise detected."),
            "metrics": praise.get("supporting_metrics", []),
            "evidence": praise.get("evidence", []),
            "recommended_action": praise.get("recommended_action", ""),
        },
        {
            "id": "segments",
            "title": "Audience Segments",
            "provenance": segments.get("provenance", "INFERENCE"),
            "body": segments.get("description", "Insufficient comments for clustering (need ≥ 3)."),
            "metrics": segments.get("supporting_metrics", []),
            "evidence": segments.get("evidence", []),
        },
        {
            "id": "opportunities",
            "title": "Opportunities & Recommendations",
            "provenance": opportunity.get("provenance", "INFERENCE"),
            "body": opportunity.get("description", "No purchase-intent signals detected in this sample."),
            "metrics": opportunity.get("supporting_metrics", []),
            "recommended_action": opportunity.get("recommended_action", ""),
        },
        {
            "id": "methodology",
            "title": "Methodology",
            "provenance": "MODEL_PREDICTION",
            "body": (
                "Sentiment: multilingual lexicon + bidirectional negation + contrast-clause "
                "splitting (Raye pipeline), 5 classes including uncertain. "
                "Aspects: configurable ABSA (catalog=" + aspect_catalog + "). "
                "Clustering: " + cluster_method + " on TF-IDF + sentiment + intent features. "
                "Findings: evidence-based cards with confidence scores. "
                "Anomaly: Isolation Forest (available in the platform)."
            ),
        },
        {
            "id": "limitations",
            "title": "Limitations & Data Provenance",
            "provenance": sufficiency.get("provenance", "INSUFFICIENT_DATA"),
            "body": sufficiency.get("description", ""),
            "note": findings.get("disclaimer", ""),
        },
    ]

    return {
        "meta": {
            "title": meta.get("title", "YouTube Audience Intelligence Report"),
            "objective": meta.get("objective", ""),
            "prepared_by": meta.get("prepared_by", ""),
            "country": meta.get("country", ""),
            "industry": meta.get("industry", ""),
            "generated_at": datetime.utcnow().isoformat() + "Z",
        },
        "n_comments": n,
        "n_findings": findings["n_findings"],
        "sentiment_distribution": dist,
        "sections": sections,
        "findings": findings["findings"],
        "provenance": "MODEL_PREDICTION",
        "disclaimer": findings.get("disclaimer", ""),
    }
