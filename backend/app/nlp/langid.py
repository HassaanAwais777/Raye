"""Language identification: English, Urdu (script), Roman Urdu, code-mixed.

Urdu script is detected by Unicode range; Roman Urdu by a marker-token statistic
(function words like hai/nahi/ka/ki/ke/lekin/kar that rarely appear in English).
"""
import re
from typing import Set

_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
_TOKEN_RE = re.compile(r"[A-Za-z\u0600-\u06FF']+")

ROMAN_URDU_MARKERS: Set[str] = {
    "hai", "nahi", "ka", "ki", "ke", "ko", "se", "mein", "aur", "bhi", "kuch", "kya",
    "kar", "kiya", "kra", "raha", "rahi", "rahe", "gaya", "gayi", "wala", "wali",
    "lekin", "magar", "acha", "achha", "bahut", "theek", "liye", "wajah", "hota", "hoti",
    "tha", "thi", "hun", "ho", "mera", "meri", "apna", "apni", "yeh", "ye", "woh", "wo",
    "kaafi", "zyada", "itna", "jo", "na", "hain", "wase", "tarah", "sath", "saath",
    "bohat", "acha", "nahi", "hu", "me", "hi", "toh", "to", "pa", "wala",
}
# tokens shared with English are counted for both sides with lower weight
AMBIGUOUS = {"me", "hi", "to", "no", "so", "is", "us", "do", "ho", "na", "haan"}

ENGLISH_MARKERS: Set[str] = {
    "the", "this", "that", "with", "for", "and", "of", "it", "its", "i", "you", "my",
    "we", "they", "very", "but", "have", "has", "was", "were", "are", "been", "just",
    "about", "would", "could", "should", "really", "overall", "because", "from", "a",
    "an", "in", "on", "at", "is", "am", "be", "do", "did", "not", "your", "our", "their",
}

LANG_LABELS = {
    "en": "English",
    "ur": "Urdu (script)",
    "ur-Roman": "Roman Urdu",
    "code-mixed": "Code-mixed (Urdu/English)",
    "other": "Other",
}


def detect_language(text: str) -> str:
    tokens = [t.lower() for t in _TOKEN_RE.findall(text)]
    if not tokens:
        return "en"
    arabic_chars = len(_ARABIC_RE.findall(text))
    latin_chars = sum(1 for ch in text if ch.isascii() and ch.isalpha())
    arabic_ratio = arabic_chars / max(1, arabic_chars + latin_chars)
    latin_ratio = 1 - arabic_ratio

    if arabic_ratio > 0.25 and latin_ratio > 0.25:
        return "code-mixed"
    if arabic_ratio > 0.25:
        return "ur"

    ru_hits = en_hits = 0
    for tok in tokens:
        w = 0.5 if tok in AMBIGUOUS else 1.0
        if tok in ROMAN_URDU_MARKERS:
            ru_hits += w
        if tok in ENGLISH_MARKERS:
            en_hits += w
    n = len(tokens)
    ru_ratio = ru_hits / n
    en_ratio = en_hits / n

    if ru_ratio >= 0.15 and ru_hits >= 2:
        return "code-mixed" if en_ratio >= 0.12 else "ur-Roman"
    if en_ratio >= 0.12:
        return "en"
    return "en"
