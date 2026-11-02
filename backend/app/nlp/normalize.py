"""Roman Urdu / English spelling normalization.

Goal: treat variant spellings as the same meaning — "bohat", "bahut", "bohot",
"bhot", "bht" all collapse to the canonical token "bahut" before sentiment scoring.
The raw text is always preserved for display and traceability.
"""
import re
from typing import Dict

# Canonical word -> accepted variants (variants map TO the key).
VARIANTS: Dict[str, str] = {
    # --- "very / a lot" ---
    "bahut": "bahut", "bohat": "bahut", "bohot": "bahut", "bohut": "bahut",
    "bhot": "bahut", "bhut": "bahut", "bht": "bahut", "bauth": "bahut",
    # --- "no / not" ---
    "nahi": "nahi", "nahin": "nahi", "nai": "nahi", "nhe": "nahi", "nh": "nahi",
    "nahn": "nahi", "nhi": "nahi", "naeen": "nahi",
    # --- "is" ---
    "hai": "hai", "he": "hai", "hy": "hai", "h": "hai", "hain": "hain", "han": "hain",
    # --- "good / nice" ---
    "achha": "achha", "acha": "achha", "accha": "achha", "achaa": "achha", "acca": "achha",
    "asaan": "asaan",
    # --- "what" ---
    "kya": "kya", "kiya": "kya", "kia": "kya",
    # --- "also" ---
    "bhi": "bhi", "bi": "bhi", "bee": "bhi",
    # --- "but" ---
    "lekin": "lekin", "lakin": "lekin", "lkn": "lekin", "lekan": "lekin",
    # --- "very good / excellent" ---
    "behtareen": "behtareen", "behtarin": "behtareen", "behtreen": "behtareen",
    "behtreen": "behtareen", "bahtareen": "behtareen",
    # --- "bad / awful" ---
    "kharab": "kharab", "khrab": "kharab", "kharb": "kharab",
    "ghatia": "ghatia", "ghatya": "ghatia", "ghtya": "ghatia",
    # --- "useless" ---
    "bekaar": "bekaar", "bekar": "bekaar", "bikar": "bekaar", "baikaar": "bekaar",
    # --- "rubbish" ---
    "bakwas": "bakwas", "bkwass": "bakwas", "bakwaas": "bakwas",
    # --- "fine / ok" ---
    "theek": "theek", "thik": "theek", "theekh": "theek", "thk": "theek",
    # --- "amazing / powerful" ---
    "zabardast": "zabardast", "zaberdast": "zabardast", "zbrdst": "zabardast",
    "kamal": "kamal", "kamaal": "kamal", "kml": "kamal",
    "damdar": "damdar", "damdaar": "damdar", "dhamakedar": "damdar",
    # --- "price" ---
    "qeemat": "qeemat", "keemat": "qeemat", "qimat": "qeemat", "kimat": "qeemat",
    "mehnga": "mehnga", "mehnga": "mehnga", "mahnga": "mehnga", "mehga": "mehnga", "mehnga": "mehnga",
    # --- "problem" ---
    "masla": "masla", "maslah": "masla", "msla": "masla", "masle": "masle",
    # --- "battery" ---
    "battery": "battery", "bettry": "battery", "battry": "battery", "batterry": "battery",
    "betari": "battery", "battri": "battery",
    # --- "camera" ---
    "camera": "camera", "camra": "camera", "cammera": "camera", "kamera": "camera",
    # --- texting abbreviations (English side) ---
    "plz": "please", "pls": "please", "thx": "thanks", "thanx": "thanks", "u": "you",
    "ur": "your", "r": "are", "gr8": "great", "w8": "wait", "b4": "before",
    "luv": "love", "nd": "and", "wid": "with", "wthout": "without", "nvr": "never",
    "gud": "good", "vry": "very", "nyc": "nice", "awsm": "awesome", "frm": "from",
    "cuz": "because", "coz": "because", "bcz": "because", "bcoz": "because",
    # --- misc roman urdu common ---
    "shukriya": "shukriya", "paisa": "paisa", "paisay": "paisay", "vasool": "vasool",
    "wasool": "vasool", "wsol": "vasool",
}

# Rules applied to tokens not found in the variant table.
_LEET = {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "8": "ate", "$": "s", "@": "a"}
_REPEAT_RE = re.compile(r"(.)\1{2,}")  # soooo -> so (collapse 3+ repeats)


def normalize_token(token: str) -> str:
    """Canonical form of a single lowercase token."""
    t = token
    if t in VARIANTS:
        return VARIANTS[t]
    # light leetspeak deobfuscation (gr8-style), then retry the table
    if any(ch in _LEET for ch in t):
        t2 = "".join(_LEET.get(ch, ch) for ch in t)
        if t2 in VARIANTS:
            return VARIANTS[t2]
        t = t2
    return _REPEAT_RE.sub(r"\1", t)


def normalize_text(text: str) -> str:
    """Normalize a clause/sentence while preserving Urdu-script characters as-is."""
    tokens = re.findall(r"[\w\u0600-\u06FF]+|[^\w\u0600-\u06FF\s]", text.lower())
    out = []
    for tok in tokens:
        if re.match(r"^[\w\u0600-\u06FF]+$", tok):
            out.append(normalize_token(tok))
        else:
            out.append(tok)
    return " ".join(out)
