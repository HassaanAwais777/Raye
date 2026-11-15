"""Multilingual NLP pipeline — Project A (Raye), ported and extended.

Pipeline per comment:
  language detection → normalization → clause splitting → sentiment scoring
  → aspect-based sentiment → topic extraction

Sentiment classes (5): positive, negative, neutral, mixed, uncertain.
The `uncertain` class is the honesty path: when confidence is low and few
sentiment-bearing words are present, no label is forced.

Aspect catalogs are configurable so product-review aspects are NOT applied to
every video — the catalog is selected per research topic.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from .lexicons import (
    CONTRAST,
    DIMINISHERS,
    INTENSIFIERS,
    NEGATORS,
    NEGATIVE,
    PHRASES,
    POSITIVE,
)

# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------

URDU_SCRIPT_RE = re.compile(r"[\u0600-\u06FF]")
ROMAN_UR_MARKERS = {
    "acha", "accha", "achha", "nahi", "nahin", "hai", "hain", "bohat", "bahut",
    "lekin", "magar", "kharab", "bekaar", "zabardast", "kamal", "mast",
    "kya", "kyun", "kaisa", "aisa", "woh", "yeh", "mera", "tera",
}


def detect_language(text: str) -> str:
    """Return one of: en, ur, roman_ur, mixed."""
    if not text or not text.strip():
        return "en"
    has_urdu = bool(URDU_SCRIPT_RE.search(text))
    tokens = re.findall(r"[a-zA-Z]+", text.lower())
    roman_hits = sum(1 for t in tokens if t in ROMAN_UR_MARKERS)
    has_en = any(t.isascii() and t not in ROMAN_UR_MARKERS and len(t) > 2 for t in tokens)
    if has_urdu and (has_en or roman_hits > 0):
        return "mixed"
    if has_urdu:
        return "ur"
    if roman_hits >= 2 and not has_en:
        return "roman_ur"
    if roman_hits >= 1 and has_en:
        return "mixed"
    return "en"


# ---------------------------------------------------------------------------
# Normalization — collapse Roman Urdu spelling variants + texting forms
# ---------------------------------------------------------------------------

_VARIANT_MAP = {
    "bohat": "bahut", "bohot": "bahut", "bhot": "bahut", "bht": "bahut",
    "bahout": "bahut", "bohut": "bahut",
    "nahi": "nahi", "nahin": "nahi", "nai": "nahi", "nhe": "nahi", "nh": "nahi",
    "acha": "achha", "accha": "achha", "acca": "achha",
    "thik": "theek", "tik": "theek", "thik hai": "theek",
    "gr8": "great", "plz": "please", "pls": "please", "u": "you",
    "ur": "your", "r": "are", "b4": "before",
}
_REPEAT_RE = re.compile(r"(.)\1{2,}", re.I)  # soooo → so
_TEXTING_RE = re.compile(r"\b([a-z]+)\b")


def normalize(text: str) -> str:
    if not text:
        return ""
    t = text.lower()
    # collapse repeated letters (soooo → so), but keep doubles like "ll"
    t = _REPEAT_RE.sub(lambda m: m.group(1) if m.group(1) not in "ls" else m.group(1) * 2, t)
    # variant replacement on token boundaries
    def _sub(m: re.Match) -> str:
        word = m.group(1)
        return _VARIANT_MAP.get(word, word)
    t = _TEXTING_RE.sub(_sub, t)
    return t


# ---------------------------------------------------------------------------
# Clause splitting — on punctuation and contrast words
# ---------------------------------------------------------------------------

_SPLIT_RE = re.compile(
    r"[,;:!?\n\r()\-–—…،؟۔]+"
    r"|\b(?:but|however|although|though|yet|still|nevertheless|nonetheless)\b"
    r"|\b(?:lekin|lakin|magar|balkay|balki|halanke)\b",
    re.IGNORECASE,
)


def split_clauses(text: str) -> list[str]:
    if not text:
        return []
    parts = [p.strip() for p in _SPLIT_RE.split(text) if p and p.strip()]
    return parts or [text.strip()]


# ---------------------------------------------------------------------------
# Clause scoring — lexicon + bidirectional negation + intensifiers/diminishers
# ---------------------------------------------------------------------------

_PHRASE_RE = re.compile(re.escape("__"), re.I)  # placeholder, built below


def _phrase_overrides(clause_lower: str) -> tuple[float, str]:
    """Apply multi-word phrase overrides; return (score_delta, remaining_text)."""
    delta = 0.0
    remaining = clause_lower
    for phrase, w in PHRASES.items():
        if phrase in remaining:
            delta += w
            remaining = remaining.replace(phrase, " ")
    return delta, remaining


def score_clause(clause: str) -> tuple[float, float, float, int]:
    """Return (total, pos_sum, neg_sum, n_sent_words) for a single clause."""
    if not clause:
        return 0.0, 0.0, 0.0, 0
    lower = normalize(clause)
    phrase_delta, lower = _phrase_overrides(lower)
    tokens = re.findall(r"[\u0600-\u06FF]+|[a-zA-Z]+", lower)
    total = phrase_delta
    pos_sum = max(0.0, phrase_delta)
    neg_sum = max(0.0, -phrase_delta)
    n_sent = 0
    for i, tok in enumerate(tokens):
        if tok in POSITIVE:
            w = POSITIVE[tok]
            window = tokens[max(0, i - 3): i] + tokens[i + 1: i + 3]
            if any(t in NEGATORS for t in window):
                w = -w * 0.9  # negation flips polarity (bidirectional)
                neg_sum += abs(w)
            else:
                if any(t in INTENSIFIERS for t in tokens[max(0, i - 2): i]):
                    w *= 1.5
                elif any(t in DIMINISHERS for t in tokens[max(0, i - 2): i]):
                    w *= 0.6
                pos_sum += w
            total += w
            n_sent += 1
        elif tok in NEGATIVE:
            w = NEGATIVE[tok]
            window = tokens[max(0, i - 3): i] + tokens[i + 1: i + 3]
            if any(t in NEGATORS for t in window):
                w = -w * 0.6  # negated negative → milder positive
                pos_sum += abs(w)
            else:
                if any(t in INTENSIFIERS for t in tokens[max(0, i - 2): i]):
                    w *= 1.5
                elif any(t in DIMINISHERS for t in tokens[max(0, i - 2): i]):
                    w *= 0.6
                neg_sum += w
            total += -w
            n_sent += 1
    return total, pos_sum, neg_sum, n_sent


# ---------------------------------------------------------------------------
# Aspect catalogs (configurable ABSA)
# ---------------------------------------------------------------------------

ASPECT_CATALOGS: dict[str, list[dict[str, Any]]] = {
    "product": [
        {"name": "battery", "label": "Battery & charging", "keywords": ["battery", "bettry", "battry", "charge", "charging", "بٹری", "بیٹری", "چارج"]},
        {"name": "camera", "label": "Camera", "keywords": ["camera", "cam", "lens", "کیمرہ"]},
        {"name": "price", "label": "Price & value", "keywords": ["price", "cost", "expensive", "cheap", "value", "money", "daam", "qeemat", "قیمت", "دام"]},
        {"name": "display", "label": "Display", "keywords": ["display", "screen", "panel", "ڈسپلے", "اسکرین"]},
        {"name": "performance", "label": "Performance & speed", "keywords": ["performance", "speed", "fast", "slow", "lag", "hang", "کارکردگی"]},
        {"name": "software", "label": "Software & updates", "keywords": ["software", "update", "os", "ui", "bug", "سافٹ ویئر"]},
        {"name": "audio", "label": "Audio & speakers", "keywords": ["audio", "sound", "speaker", "bass", "noise", "آواز"]},
        {"name": "build", "label": "Build & design", "keywords": ["build", "design", "quality", "material", "build quality", "ڈیزائن"]},
        {"name": "delivery", "label": "Delivery & service", "keywords": ["delivery", "shipping", "service", "support", "warranty", "ڈلیوری"]},
        {"name": "general", "label": "Overall quality", "keywords": ["quality", "overall", "product", "overall", "کوالٹی"]},
    ],
    "youtube": [
        {"name": "content_quality", "label": "Content quality", "keywords": ["content", "informative", "useful", "detailed", "quality", "کونٹنٹ"]},
        {"name": "presentation", "label": "Video presentation", "keywords": ["editing", "cinematography", "production", "visuals", "پریزنٹیشن"]},
        {"name": "creator_credibility", "label": "Creator credibility", "keywords": ["honest", "unbiased", "trust", "reviewer", "genuine", "hra", "امانت"]},
        {"name": "entertainment", "label": "Entertainment value", "keywords": ["funny", "entertaining", "fun", "enjoyed", "mazaa", "مزہ"]},
        {"name": "educational", "label": "Educational value", "keywords": ["learned", "educational", "explained", "tutorial", "guide", "سیکھا"]},
        {"name": "accuracy", "label": "Information accuracy", "keywords": ["accurate", "wrong", "misleading", "correct", "facts", "sahi", "غلط"]},
        {"name": "audience_experience", "label": "Audience experience", "keywords": ["experience", "feeling", "vibe", "تجربہ"]},
        {"name": "ad_relevance", "label": "Ad relevance", "keywords": ["ad", "ads", "sponsor", "sponsored", "advertisement", "ایش"]},
        {"name": "brand_perception", "label": "Brand perception", "keywords": ["brand", "company", "reputation", "برانڈ"]},
    ],
    # Fashion / e-commerce catalog — aligns with Project 3 (Pakistani social
    # audience intelligence): group comments around the audience-need categories
    # the assignment specifies.
    "fashion": [
        {"name": "price", "label": "Price", "keywords": ["price", "prices", "cost", "expensive", "cheap", "rate", "daam", "qeemat", "kitne", "kitna", "kitni", "kam", "zyada", "bohat zyada", "قیمت", "دام"]},
        {"name": "fabric_quality", "label": "Fabric quality", "keywords": ["fabric", "quality", "cloth", "material", "lawn", "cotton", "silk", "kapra", "kapray", "kapre", "thread", "stitching", "کپڑا", "کوالٹی"]},
        {"name": "sizing", "label": "Sizing & fit", "keywords": ["size", "sizing", "fit", "small", "large", "medium", "extra", "mera size", "size kya", "measure", "سائز"]},
        {"name": "delivery", "label": "Delivery & shipping", "keywords": ["delivery", "shipping", "dispatch", "courier", "kitne din", "kab tak", "deliver", "kab aye ga", "reach", "ڈلیوری"]},
        {"name": "discounts", "label": "Discounts & offers", "keywords": ["discount", "sale", "offer", "off", "deal", "sasta", "kam", "11.11", "12.12", "eid", "promotion", "رعایت", "سیل"]},
        {"name": "availability", "label": "Availability", "keywords": ["available", "stock", "in stock", "out of stock", "mujhe mil", "available hai", "milega", "kahan se", "دستیاب"]},
        {"name": "purchase_intent", "label": "Purchase intent", "keywords": ["order", "buy", "khareed", "khareedna", "purchase", "inbox", "dm", "book", "booking", "kaise order", "place order", "خرید"]},
        {"name": "design", "label": "Design & style", "keywords": ["design", "beautiful", "pretty", "style", "color", "colour", "pattern", "print", "embroidery", "pyara", "khoobsurat", "ڈیزائن"]},
    ],
    "general": [
        {"name": "overall", "label": "Overall", "keywords": ["overall", "general", "quality", "product", "کمپنی"]},
    ],
}


# ---------------------------------------------------------------------------
# Purchase-intent detection (Project 3 Table B field)
# Returns one of: inquiry, strong_intent, complaint, none
# ---------------------------------------------------------------------------

PURCHASE_INTENT_KEYWORDS: dict[str, set[str]] = {
    "strong_intent": {
        "order", "buy", "buying", "khareed", "khareedna", "khareedunga", "purchase",
        "inbox", "dm me", "book", "booking", "place order", "kaise order",
        "order karna", "order karonga", "خرید", "اردر",
    },
    "inquiry": {
        "price", "price please", "price kya", "kitne", "kitna", "kitni", "daam",
        "available", "availability", "stock", "milega", "kahan se", "details",
        "detail", "info", "information", "rate", "cost", "kaise", "kya",
        "قیمت", "دستیاب",
    },
    "complaint": {
        "waiting", "still waiting", "delay", "late", "nahi aya", "nahi mili",
        "order nahi", "fraud", "scam", "refund", "return", "takleef",
        "انتظار", "دیر",
    },
}


def detect_purchase_intent(text: str) -> str:
    """Classify the purchase-intent signal in a comment.

    Returns: 'strong_intent' | 'inquiry' | 'complaint' | 'none'.
    Priority: strong_intent > complaint > inquiry (a complaint about an order
    already placed is more actionable than a vague inquiry).
    """
    if not text:
        return "none"
    lower = normalize(text)
    # strong_intent has highest priority (explicit purchase language)
    for kw in PURCHASE_INTENT_KEYWORDS["strong_intent"]:
        if kw in lower:
            return "strong_intent"
    for kw in PURCHASE_INTENT_KEYWORDS["complaint"]:
        if kw in lower:
            return "complaint"
    for kw in PURCHASE_INTENT_KEYWORDS["inquiry"]:
        if kw in lower:
            return "inquiry"
    return "none"


def _clause_polarity(total: float) -> str:
    if total >= 0.3:
        return "positive"
    if total <= -0.3:
        return "negative"
    return "neutral"


def aspect_sentiment(text: str, catalog: str) -> list[dict[str, Any]]:
    aspects = ASPECT_CATALOGS.get(catalog, ASPECT_CATALOGS["general"])
    lower = normalize(text)
    clauses = split_clauses(lower)
    results: list[dict[str, Any]] = []
    for asp in aspects:
        kws = [k.lower() for k in asp["keywords"]]
        mentioned = False
        pos = neg = 0.0
        mentions = 0
        for cl in clauses:
            if any(kw in cl for kw in kws):
                mentioned = True
                t, p, n, _ = score_clause(cl)
                pos += p
                neg += n
                mentions += 1
        if not mentioned:
            continue
        net = pos - neg
        label = _clause_polarity(net)
        results.append({
            "name": asp["name"],
            "label": asp["label"],
            "mentions": mentions,
            "sentiment": label,
            "score": round(net, 3),
            "insufficient": mentions < 3,
        })
    return results


# ---------------------------------------------------------------------------
# Topic extraction — lightweight keyword frequency (no model download)
# ---------------------------------------------------------------------------

_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "this", "that", "it", "i",
    "you", "and", "or", "but", "to", "of", "in", "on", "for", "with", "hai",
    "ka", "ki", "ke", "ko", "se", "ne", "par", "aur", "ya", "nahi", "ho",
    "hota", "hua", "bhi", "tho", "toh", "bohat", "very", "really", "just",
}


def extract_topics(texts: list[str], top_n: int = 8) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for t in texts:
        toks = re.findall(r"[a-zA-Z]{3,}", normalize(t))
        for tok in toks:
            if tok in _STOPWORDS:
                continue
            counter[tok] += 1
    return [{"topic": w, "count": c} for w, c in counter.most_common(top_n)]


# ---------------------------------------------------------------------------
# Main analyzer
# ---------------------------------------------------------------------------

# Thresholds
_POS_T = 0.8
_NEG_T = -0.8
_MIXED_MIN = 0.8  # both pos & neg must reach this for "mixed"
_UNCERTAIN_SCORE = 0.15  # |score| below this AND few sent words → uncertain
_UNCERTAIN_MINWORDS = 2


def analyze_text(text: str, aspect_catalog: str = "general") -> dict[str, Any]:
    """Full analysis of a single comment. Returns a structured result."""
    if not text or not text.strip():
        return {
            "text": text, "language": "en", "normalized": "",
            "sentiment": "uncertain", "score": 0.0, "confidence": 0.0,
            "aspects": [], "clauses": [], "provenance": "MODEL_PREDICTION",
        }

    language = detect_language(text)
    normalized = normalize(text)
    clauses = split_clauses(normalized)

    pos_total = neg_total = 0.0
    n_sent_total = 0
    clause_scores = []
    for cl in clauses:
        t, p, n, ns = score_clause(cl)
        pos_total += p
        neg_total += n
        n_sent_total += ns
        clause_scores.append({"clause": cl, "score": round(t, 3)})

    total = pos_total - neg_total
    score = round(math.tanh(total / 4.0), 3)
    confidence = round(abs(score), 3)

    # 5-class decision
    if pos_total >= _MIXED_MIN and neg_total >= _MIXED_MIN:
        sentiment = "mixed"
    elif n_sent_total < _UNCERTAIN_MINWORDS and abs(score) < _UNCERTAIN_SCORE:
        sentiment = "uncertain"
    elif score >= _UNCERTAIN_SCORE and total >= _POS_T * 0.5 and pos_total > neg_total:
        sentiment = "positive"
    elif score <= -_UNCERTAIN_SCORE and total <= _NEG_T * 0.5 and neg_total > pos_total:
        sentiment = "negative"
    elif abs(score) < _UNCERTAIN_SCORE and n_sent_total < _UNCERTAIN_MINWORDS:
        sentiment = "uncertain"
    else:
        sentiment = "neutral"

    return {
        "text": text,
        "language": language,
        "normalized": normalized,
        "sentiment": sentiment,
        "score": score,
        "confidence": confidence,
        "pos_score": round(pos_total, 3),
        "neg_score": round(neg_total, 3),
        "n_sentiment_words": n_sent_total,
        "clauses": clause_scores,
        "aspects": aspect_sentiment(text, aspect_catalog),
        "purchase_intent": detect_purchase_intent(text),
        "provenance": "MODEL_PREDICTION",
    }


def analyze_batch(
    texts: list[str], aspect_catalog: str = "general"
) -> dict[str, Any]:
    results = [analyze_text(t, aspect_catalog) for t in texts]
    dist = Counter(r["sentiment"] for r in results)
    langs = Counter(r["language"] for r in results)
    intent_dist = Counter(r["purchase_intent"] for r in results)
    total = max(1, len(results))
    return {
        "results": results,
        "count": len(results),
        "distribution": {k: dist.get(k, 0) for k in ["positive", "negative", "neutral", "mixed", "uncertain"]},
        "distribution_pct": {k: round(dist.get(k, 0) / total * 100, 1) for k in ["positive", "negative", "neutral", "mixed", "uncertain"]},
        "purchase_intent_distribution": {k: intent_dist.get(k, 0) for k in ["strong_intent", "inquiry", "complaint", "none"]},
        "purchase_intent_distribution_pct": {k: round(intent_dist.get(k, 0) / total * 100, 1) for k in ["strong_intent", "inquiry", "complaint", "none"]},
        "language_distribution": dict(langs),
        "avg_score": round(sum(r["score"] for r in results) / total, 3),
        "topics": extract_topics(texts),
        "provenance": "MODEL_PREDICTION",
        "sample_disclaimer": "Percentages represent the collected sample, not the entire YouTube audience.",
    }
