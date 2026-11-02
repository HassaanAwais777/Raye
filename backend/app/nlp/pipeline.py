"""Per-comment analysis pipeline: language ID -> normalization -> sentiment -> aspects."""
import hashlib
from typing import Any, Dict, List

from .aspects import extract_aspects
from .langid import detect_language
from .normalize import normalize_text
from .sentiment import analyze_text


def comment_id(raw: Dict[str, Any]) -> str:
    """Stable id from platform + text + author (dedup happens in the orchestrator)."""
    basis = f'{raw["source"]["platform"]}|{raw.get("author", "")}|{raw.get("text_raw", "")[:500]}'
    return hashlib.sha1(basis.encode("utf-8")).hexdigest()[:20]


def analyze_comment(raw: Dict[str, Any]) -> Dict[str, Any]:
    text_raw = (raw.get("text_raw") or "").strip()
    lang = detect_language(text_raw)
    sent = analyze_text(text_raw)
    clause_infos = [{"text": c["text"], "norm": normalize_text(c["text"]), "score": c["score"]}
                    for c in sent["clauses"]]
    aspects = extract_aspects(text_raw, clause_infos, sent["sentiment"], sent["score"])

    return {
        "id": raw.get("id") or comment_id(raw),
        "text_raw": text_raw,
        "text_normalized": normalize_text(text_raw),
        "lang": lang,
        "sentiment": sent["sentiment"],
        "score": sent["score"],
        "pos_total": sent["pos_total"],
        "neg_total": sent["neg_total"],
        "aspects": aspects,
        "author": raw.get("author", "unknown"),
        "likes": int(raw.get("likes", 0) or 0),
        "published": raw.get("published", ""),
        "fetched_at": raw.get("fetched_at", ""),
        "source": raw.get("source", {}),
    }


def analyze_batch(raws: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [analyze_comment(r) for r in raws]
