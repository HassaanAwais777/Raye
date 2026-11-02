"""Aspect-based analysis: 12 aspects with English + Roman Urdu + Urdu-script keywords.

Aspect sentiment comes primarily from the clause that mentions the aspect; if a
comment mentions exactly one aspect, the comment-level sentiment backs it up.
"""
import re
from typing import Dict, List, Optional

ASPECTS: List[Dict] = [
    {"name": "battery", "label": "Battery & charging", "keywords": [
        "battery", "bettry", "battry", "battri", "betari", "backup", "charge", "charging",
        "charger", "drain", "battery life", "battery timing", "بٹری", "بیٹری", "چارج"]},
    {"name": "camera", "label": "Camera", "keywords": [
        "camera", "camra", "kamera", "lens", "photo", "photos", "pic", "pics", "selfie",
        "video quality", "kamera", "کیمرہ", "تصویر"]},
    {"name": "price", "label": "Price & value", "keywords": [
        "price", "qeemat", "keemat", "kimat", "cost", "expensive", "mehnga", "mahnga",
        "cheap", "sasta", "sasti", "value for money", "paisa", "paisay", "vasool", "wasool",
        "worth", "overpriced", "affordable", "budget", "قیمت", "مہنگا", "سستا"]},
    {"name": "display", "label": "Display", "keywords": [
        "display", "screen", "scrren", "amoled", "lcd", "ips", "brightness", "resolution",
        "refresh rate", "سکرین", "ڈسپلے"]},
    {"name": "performance", "label": "Performance & speed", "keywords": [
        "performance", "speed", "fast", "slow", "lag", "laggy", "lagging", "hang", "hanging",
        "latk", "processor", "chipset", "snapdragon", "helio", "exynos", "dimensity", "ram",
        "gaming", "fps", "pubg", "game", "سپیڈ", "رفتار"]},
    {"name": "software", "label": "Software & updates", "keywords": [
        "software", "update", "updates", "ui", "os", "android", "ios", "miui", "hyperos",
        "bloatware", "bug", "bugs", "ad", "ads"]},
    {"name": "audio", "label": "Audio & speakers", "keywords": [
        "sound", "audio", "speaker", "speakers", "bass", "volume", "awaz", "awaaz", "آواز"]},
    {"name": "build", "label": "Build & design", "keywords": [
        "build", "build quality", "design", "look", "looks", "body", "plastic", "metal",
        "glass", "durable", "durability", "premium", "ڈیزائن", "معیار"]},
    {"name": "connectivity", "label": "Network & connectivity", "keywords": [
        "signal", "network", "wifi", "bluetooth", "sim", "5g", "4g", "call", "calls",
        "internet", "net speed", "نیٹ"]},
    {"name": "delivery", "label": "Delivery & service", "keywords": [
        "delivery", "shipping", "service", "warranty", "guarantee", "customer support",
        "return", "refund", "packaging", " packing", "وارنٹی", "ڈیلیوری"]},
    {"name": "accessories", "label": "Box accessories", "keywords": [
        "earphones", "case", "cover", "adapter", "cable", "in box", "no charger"]},
    {"name": "general", "label": "Overall quality", "keywords": [
        "quality", "product", "prodcut", "device", "phone", "item", "چیز"]},
]

_COMPILED = [
    (a["name"], a["label"], [re.compile(rf"\b{re.escape(k.strip())}\b", re.IGNORECASE) for k in a["keywords"] if k.strip()])
    for a in ASPECTS
]


def _clause_sentiment(score: float, pos: float, neg: float) -> Optional[str]:
    if score >= 0.3:
        return "positive"
    if score <= -0.3:
        return "negative"
    return None


def extract_aspects(raw_text: str, clause_infos: List[Dict], overall_label: str,
                    overall_score: float) -> List[Dict]:
    """Extract aspects mentioned in a comment with per-aspect sentiment.

    clause_infos: [{"text": raw, "norm": normalized, "score": float}, ...]
    """
    found: Dict[str, Dict] = {}
    raw_lower = raw_text.lower()

    for ci in clause_infos:
        hay_raw = ci["text"].lower()
        hay_norm = ci.get("norm", "")
        for name, label, patterns in _COMPILED:
            hit = any(p.search(hay_raw) or p.search(hay_norm) for p in patterns)
            if not hit:
                continue
            entry = found.setdefault(name, {"name": name, "label": label, "score": 0.0,
                                            "sentiment": None, "mentions": 0})
            entry["mentions"] += 1
            entry["score"] += ci["score"]
            s = _clause_sentiment(ci["score"], 0, 0)
            if s and not entry["sentiment"]:
                entry["sentiment"] = s

    for entry in found.values():
        if entry["sentiment"] is None:
            avg = entry["score"] / max(1, entry["mentions"])
            if avg >= 0.3:
                entry["sentiment"] = "positive"
            elif avg <= -0.3:
                entry["sentiment"] = "negative"

    # Fallback: single-aspect comment inherits overall sentiment
    if len(found) == 1:
        only = next(iter(found.values()))
        if only["sentiment"] is None and overall_label in ("positive", "negative"):
            only["sentiment"] = overall_label
            only["score"] = overall_score * 0.8

    return [
        {"name": e["name"], "label": e["label"], "sentiment": e["sentiment"] or "neutral",
         "score": round(e["score"] / max(1, e["mentions"]), 3)}
        for e in found.values()
    ]
