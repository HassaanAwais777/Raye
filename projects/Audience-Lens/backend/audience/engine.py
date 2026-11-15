"""Audience intelligence engine — Project 3.

  * features.build() — turns comments into a feature matrix:
    TF-IDF (lexical) ⊕ sentiment score ⊕ aspect count ⊕ intent signals.
    (Production swaps TF-IDF for sentence-transformer embeddings; the interface
    is unchanged — only the vectorizer changes.)
  * clustering.cluster() — K-Means / DBSCAN / Agglomerative, with silhouette
    selection when k is not specified.
  * anomaly.detect() — Isolation Forest on per-video time-series features.

Segments are analytical clusters, NOT verified demographics. No age/gender.
"""
from __future__ import annotations

import re
from typing import Any

import numpy as np
from sklearn.cluster import KMeans, DBSCAN, AgglomerativeClustering
from sklearn.ensemble import IsolationForest
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from ..nlp.pipeline import analyze_text

# ---------------------------------------------------------------------------
# Intent signals
# ---------------------------------------------------------------------------

INTENT_KEYWORDS: dict[str, set[str]] = {
    "buy": {"buy", "buying", "purchase", "order", "khareed", "inbox", "book", "خرید"},
    "research": {"compare", "vs", "versus", "review", "specs", "spec", "benchmark", "alternative", "option"},
    "complaint": {"bad", "worst", "broken", "issue", "problem", "kharab", "bekaar", "return", "refund", "ghatiya", "waiting", "delay", "late", "nahi aya"},
    "praise": {"great", "best", "love", "amazing", "acha", "zabardast", "behtareen", "recommend", "perfect", "beautiful", "pyara"},
    # Project 3 audience-need categories (Pakistani fashion / e-commerce)
    "discount": {"discount", "sale", "offer", "off", "deal", "sasta", "kam", "11.11", "12.12", "eid", "promotion", "رعایت", "سیل"},
    "delivery": {"delivery", "shipping", "dispatch", "courier", "kitne din", "kab tak", "deliver", "reach", "ڈلیوری"},
    "availability": {"available", "stock", "in stock", "out of stock", "milega", "kahan se", "mujhe mil", "دستیاب"},
    "price": {"price", "cost", "expensive", "cheap", "rate", "daam", "qeemat", "kitne", "kitna", "zyada", "قیمت", "دام"},
}


def _intent_vector(text: str) -> dict[str, int]:
    lower = text.lower()
    return {intent: sum(1 for k in kws if k in lower) for intent, kws in INTENT_KEYWORDS.items()}


# ---------------------------------------------------------------------------
# Feature builder
# ---------------------------------------------------------------------------


def build_features(texts: list[str]) -> tuple[np.ndarray, list[dict[str, Any]]]:
    """Return (feature_matrix, per_comment_meta)."""
    nlp_results = [analyze_text(t, "general") for t in texts]

    # TF-IDF lexical vectors
    vec = TfidfVectorizer(max_features=200, stop_words="english")
    try:
        tfidf = vec.fit_transform(texts).toarray()
    except ValueError:
        tfidf = np.zeros((len(texts), 1))

    # Structured features
    structured = []
    for r in nlp_results:
        iv = _intent_vector(r["text"])
        structured.append([
            r["score"],
            r["confidence"],
            r["n_sentiment_words"],
            r["pos_score"],
            r["neg_score"],
            iv["buy"],
            iv["research"],
            iv["complaint"],
            iv["praise"],
            iv["discount"],
            iv["delivery"],
            iv["availability"],
            iv["price"],
        ])
    structured_arr = np.array(structured, dtype=float)

    # Pad tfidf / structured to combine
    if tfidf.shape[0] != structured_arr.shape[0]:
        structured_arr = structured_arr[: tfidf.shape[0]]
    combined = np.hstack([tfidf, structured_arr]) if tfidf.size else structured_arr

    # Scale structured columns only (tfidf already scaled); simpler: scale all
    scaled = StandardScaler().fit_transform(combined)

    meta = [
        {
            "text": r["text"],
            "sentiment": r["sentiment"],
            "score": r["score"],
            "language": r["language"],
            "intent": _intent_vector(r["text"]),
        }
        for r in nlp_results
    ]
    return scaled, meta


# ---------------------------------------------------------------------------
# Clustering
# ---------------------------------------------------------------------------


def _auto_k(X: np.ndarray, k_min: int = 2, k_max: int = 8) -> int:
    """Pick k by silhouette score."""
    n = X.shape[0]
    if n < 4:
        return 2
    k_max = min(k_max, n - 1)
    best_k, best_s = 2, -1.0
    for k in range(max(2, k_min), k_max + 1):
        try:
            labels = KMeans(n_clusters=k, n_init=10, random_state=42).fit_predict(X)
            s = silhouette_score(X, labels)
            if s > best_s:
                best_s, best_k = s, k
        except Exception:
            continue
    return best_k


SEGMENT_LABELS = [
    "Interested buyers", "Price-sensitive", "Product researchers",
    "Brand supporters", "Dissatisfied", "Educational seekers",
    "Entertainment-focused", "Mixed / undecided",
    # Project 3 audience-need segments (Pakistani fashion / e-commerce)
    "Discount-focused", "Delivery-concerned", "Availability-seeking",
]


def _label_cluster(idx: int, meta: list[dict]) -> str:
    """Heuristic segment label based on dominant intent/need + sentiment.

    Surfaces the Project 3 audience-need segments (discount-focused,
    delivery-concerned, availability-seeking, price-sensitive) when those
    signals dominate; otherwise falls back to sentiment/intent labels.
    """
    if not meta:
        return f"Segment {idx + 1}"
    avg_score = sum(m["score"] for m in meta) / len(meta)
    intents = {k: sum(m["intent"].get(k, 0) for m in meta) for k in INTENT_KEYWORDS}
    # Consider only the need/intent signals (exclude pure sentiment intents here)
    need_signals = {k: v for k, v in intents.items() if v > 0}
    top_intent = max(need_signals, key=need_signals.get) if need_signals else None
    top_count = need_signals.get(top_intent, 0) if top_intent else 0

    # Project 3 audience-need segments take priority when the signal is strong
    if top_intent == "discount":
        return "Discount-focused"
    if top_intent == "delivery":
        return "Delivery-concerned"
    if top_intent == "availability":
        return "Availability-seeking"
    if top_intent == "price":
        return "Price-sensitive"
    if top_intent == "buy":
        return "Interested buyers"
    if top_intent == "complaint" or avg_score <= -0.2:
        return "Dissatisfied"
    if top_intent == "research":
        return "Product researchers"
    if top_intent == "praise" and avg_score > 0.2:
        return "Brand supporters"
    if avg_score > 0.1:
        return "Brand supporters"
    return SEGMENT_LABELS[idx % len(SEGMENT_LABELS)]


def cluster(
    texts: list[str],
    method: str = "kmeans",
    k: int | None = None,
) -> dict[str, Any]:
    """Cluster comments into audience segments."""
    if len(texts) < 3:
        return {
            "error": "At least 3 comments required for clustering.",
            "provenance": "INSUFFICIENT_DATA",
            "n_comments": len(texts),
        }

    X, meta = build_features(texts)
    n = X.shape[0]

    if method == "kmeans":
        kk = k or _auto_k(X)
        labels = KMeans(n_clusters=kk, n_init=10, random_state=42).fit_predict(X)
        method_label = f"K-Means (k={kk})"
    elif method == "dbscan":
        labels = DBSCAN(eps=2.0, min_samples=2).fit_predict(X)
        method_label = "DBSCAN"
    elif method == "hierarchical":
        kk = k or _auto_k(X)
        labels = AgglomerativeClustering(n_clusters=kk).fit_predict(X)
        method_label = f"Hierarchical (k={kk})"
    else:
        return {"error": f"Unknown method: {method}", "provenance": "INSUFFICIENT_DATA"}

    unique = sorted(set(labels.tolist()))
    noise = -1 in labels

    clusters = []
    for c in unique:
        if c == -1:
            continue
        members = [meta[i] for i in range(n) if labels[i] == c]
        avg = sum(m["score"] for m in members) / len(members)
        # top terms via simple frequency
        from collections import Counter
        words = Counter()
        for m in members:
            for w in re.findall(r"[a-zA-Z]{4,}", m["text"].lower()):
                words[w] += 1
        top_terms = [w for w, _ in words.most_common(5)]
        clusters.append({
            "cluster_id": int(c),
            "label": _label_cluster(int(c), members),
            "size": len(members),
            "share": round(len(members) / n * 100, 1),
            "avg_sentiment_score": round(avg, 3),
            "top_terms": top_terms,
            "sample_comments": [m["text"][:120] for m in members[:3]],
            "provenance": "INFERENCE",
        })

    sil = None
    try:
        if len(unique) > 1 and not noise and n > len(unique):
            sil = round(float(silhouette_score(X, labels)), 3)
    except Exception:
        pass

    return {
        "method": method_label,
        "n_comments": n,
        "n_clusters": len(clusters),
        "silhouette": sil,
        "labels": labels.tolist(),
        "clusters": sorted(clusters, key=lambda c: c["size"], reverse=True),
        "noise_points": int(sum(1 for l in labels if l == -1)),
        "provenance": "INFERENCE",
        "disclaimer": "Segments are analytical clusters from comment features, not verified customer demographics.",
    }


# ---------------------------------------------------------------------------
# Anomaly detection — Isolation Forest
# ---------------------------------------------------------------------------


def detect(series: list[dict[str, Any]]) -> dict[str, Any]:
    """Detect anomalies in per-item time-series features.

    Each item: {label, features: [v1, v2, ...]} where features are numeric
    (e.g. view_growth, engagement_delta, comment_volume, sentiment_shift...).
    """
    if len(series) < 4:
        return {
            "error": "At least 4 data points required.",
            "provenance": "INSUFFICIENT_DATA",
        }
    labels = [s["label"] for s in series]
    X = np.array([s["features"] for s in series], dtype=float)
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    iso = IsolationForest(contamination=0.2, random_state=42)
    raw = iso.fit_predict(X)
    scores = iso.decision_function(X)
    anomalies = []
    for i, (lab, sc, flag) in enumerate(zip(labels, scores, raw)):
        anomalies.append({
            "label": lab,
            "anomaly": bool(flag == -1),
            "anomaly_score": round(float(sc), 4),
            "features": [float(v) for v in X[i]],
        })
    anomalies.sort(key=lambda a: a["anomaly_score"])
    return {
        "method": "Isolation Forest (contamination=0.2)",
        "n_items": len(series),
        "n_anomalies": int(sum(1 for a in anomalies if a["anomaly"])),
        "anomalies": anomalies,
        "provenance": "INFERENCE",
        "note": "Each anomaly includes a score; lower (more negative) = more anomalous.",
    }
