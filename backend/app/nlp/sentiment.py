"""Sentiment engine: multilingual lexicon + negation + intensifiers + contrast clauses.

Returns one of: positive / negative / mixed / neutral plus a score in [-1, 1].
Clauses are split on punctuation AND contrast words (but / lekin / magar / بلکہ …)
so that "camera acha hai lekin battery kharab hai" is detected as mixed.
"""
import math
import re
from typing import Dict, List, Tuple

from .lexicons import (CONTRAST, DIMINISHERS, INTENSIFIERS, NEGATORS, NEGATIVE, PHRASES, POSITIVE)
from .normalize import normalize_text

_SPLIT_RE = re.compile(
    r"[,;:!?\n\r()\-–—…،؟۔]+|\b(?:but|however|although|though|yet|lekin|lakin|magar|balkay|balki|halanke)\b"
    r"|\b(?:لیکن|مگر|بلکہ|اگرچہ)\b",
    re.IGNORECASE,
)
_WORD_RE = re.compile(r"[\w\u0600-\u06FF']+")

_LABELS = ("positive", "negative", "mixed", "neutral")


def split_clauses(text: str) -> List[str]:
    parts = [p.strip() for p in _SPLIT_RE.split(text) if p and p.strip()]
    return parts or ([text.strip()] if text.strip() else [])


def _apply_phrases(clause_lower: str) -> Tuple[str, float]:
    """Score multi-word phrases once, then remove them to avoid double counting."""
    score = 0.0
    for phrase, w in PHRASES:
        if phrase in clause_lower:
            score += w
            clause_lower = clause_lower.replace(phrase, " ")
    return clause_lower, score


def score_clause(clause: str) -> Tuple[float, float]:
    """Returns (positive_total, negative_total) for one clause."""
    clause_lower, phrase_score = _apply_phrases(clause.lower())
    norm = normalize_text(clause_lower)
    tokens = _WORD_RE.findall(norm)

    total = phrase_score
    for i, tok in enumerate(tokens):
        base = POSITIVE.get(tok) or NEGATIVE.get(tok)
        if base is None:
            continue
        w = base
        # negation window: before or after the sentiment word (Urdu allows post-negation)
        window_before = tokens[max(0, i - 3):i]
        window_after = tokens[i + 1:i + 3]
        if any(t in NEGATORS for t in window_before) or any(t in NEGATORS for t in window_after):
            w = -w * 0.9
        else:
            if any(t in INTENSIFIERS for t in tokens[max(0, i - 2):i]):
                w *= 1.5
            elif any(t in DIMINISHERS for t in tokens[max(0, i - 2):i]):
                w *= 0.6
        total += w
    return (total, 0.0) if total >= 0 else (0.0, -total)


def analyze_text(text: str) -> Dict:
    """Full sentiment analysis of a raw comment."""
    clauses = []
    pos_total = neg_total = 0.0
    for raw_clause in split_clauses(text):
        pos, neg = score_clause(raw_clause)
        clause_score = pos - neg
        pos_total += pos
        neg_total += neg
        clauses.append({
            "text": raw_clause.strip()[:300],
            "score": round(clause_score, 3),
            "sentiment": ("positive" if clause_score >= 0.3 else
                          "negative" if clause_score <= -0.3 else "neutral"),
        })

    total = pos_total - neg_total
    if pos_total >= 0.8 and neg_total >= 0.8:
        label = "mixed"
    elif total >= 0.8:
        label = "positive"
    elif total <= -0.8:
        label = "negative"
    else:
        label = "neutral"
    score = round(math.tanh(total / 4.0), 3)
    return {
        "sentiment": label,
        "score": score,
        "pos_total": round(pos_total, 3),
        "neg_total": round(neg_total, 3),
        "clauses": clauses,
    }
