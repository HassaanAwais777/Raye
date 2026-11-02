"""Multilingual sentiment lexicons: English + Roman Urdu + Urdu script.

Weights are in [-3, 3]. The engine in sentiment.py applies negation windows,
intensifiers/diminishers and clause-level contrast handling on top of this.
"""
from typing import Dict, List

POSITIVE: Dict[str, float] = {
    # English
    "excellent": 3, "amazing": 3, "incredible": 3, "perfect": 3, "best": 3, "love": 3,
    "loved": 3, "awesome": 3, "fantastic": 3, "outstanding": 3, "superb": 3, "brilliant": 3,
    "great": 2.5, "wonderful": 2.5, "impressed": 2.5, "impressive": 2.5, "recommend": 2.5,
    "good": 2, "happy": 2, "beautiful": 2, "stunning": 2.5, "reliable": 2, "worth": 2,
    "solid": 1.5, "smooth": 1.5, "fast": 1.5, "crisp": 1.5, "durable": 1.5, "comfortable": 1.5,
    "premium": 1.5, "responsive": 1.5, "nice": 2, "decent": 1, "clean": 1, "bright": 1,
    "sharp": 1, "clear": 1, "useful": 1.5, "value": 1, "improved": 1.5, "improvement": 1.5,
    "works": 1, "working": 1, "satisfied": 2, "satisfying": 2, "enjoy": 2, "enjoyed": 2,
    "affordable": 1.5, "stylish": 1.5, "convenient": 1.5, "flawless": 3, "gem": 2,
    # Roman Urdu
    "achha": 2, "behtareen": 3, "zabardast": 3, "kamal": 2.5, "damdar": 2.5,
    "shandar": 2.5, "lajawab": 3, "mast": 2, "jhakaas": 2.5, "faadu": 2.5,
    "badiya": 2, "badhiya": 2, "umda": 2, "pasand": 2, "mazedaar": 2.5, "maza": 1.5,
    "theek": 1, "sahi": 1, "ustad": 2, "wah": 2, "shukriya": 1.5, "karra": 2,
    "chalta": 0.5,  # "chalta hai" = it works (weak positive)
    "sasta": 0.5,   # affordable (context: price)
    "vasool": 1.5,  # paisa vasool
    # Urdu script
    "اچھا": 2, "بہترین": 3, "زبردست": 3, "شاندار": 2.5, "پسند": 2, "خوبصورت": 2,
    "عمدہ": 2.5, "کارآمد": 2, "رواں": 1, "کمال": 2.5, "لجواب": 3, "سستا": 0.5,
    "شکریہ": 1.5, "مست": 2,
}

NEGATIVE: Dict[str, float] = {
    # English
    "terrible": -3, "awful": -3, "horrible": -3, "worst": -3, "hate": -3, "garbage": -3,
    "trash": -3, "useless": -2.5, "waste": -2.5, "pathetic": -3, "disgusting": -3,
    "bad": -2, "poor": -2, "disappointing": -2.5, "disappointed": -2.5, "regret": -3,
    "broken": -2.5, "dead": -2.5, "died": -2.5, "defective": -2.5, "faulty": -2.5,
    "flimsy": -2, "cracked": -2, "crack": -2, "scam": -3, "fraud": -3, "fake": -2.5,
    "slow": -1.5, "lag": -1.5, "laggy": -2, "lagging": -2, "hang": -1.5, "hanging": -1.5,
    "overheat": -2, "overheating": -2, "heating": -1.5, "hot": -0.5, "drain": -1.5,
    "draining": -1.5, "drains": -1.5, "expensive": -1.5, "overpriced": -2.5,
    "issue": -1, "issues": -1, "problem": -1.5, "problems": -1.5, "defect": -2,
    "scratch": -1, "scratched": -1, "stopped": -1.5, "quit": -1.5, "failed": -2,
    "refund": -1.5, "return": -1, "returned": -1, "repair": -1.5, "warranty": -0.5,
    "cheap": -1, "ugly": -2, "boring": -1.5, "unusable": -2.5, "annoying": -2,
    "frustrating": -2.5, "frustrated": -2.5, "worry": -1.5, "worried": -1.5,
    # Roman Urdu
    "kharab": -2.5, "ghatia": -3, "bakwas": -3, "faltu": -2.5, "bekaar": -2.5,
    "nakara": -2.5, "kachra": -3, "ganda": -2, "napasand": -2.5, "mehnga": -1.5,
    "pareshan": -2, "shikayat": -1.5, "masla": -1.5, "masle": -1.5, "tanga": -2,
    "zaya": -2.5, "barbaad": -3, "dhoka": -2.5, "fraud": -3, "latk": -1.5,
    "garam": -1, "khot": -2, "ghatiya": -3,
    # Urdu script
    "برا": -2, "خراب": -2.5, "بیکار": -2.5, "گھٹیا": -3, "بکواس": -3, "مہنگا": -1.5,
    "ناپسند": -2.5, "مسئلہ": -1.5, "پریشان": -2, "فراڈ": -3, "دھوکہ": -2.5, "ٹوٹ": -2,
}

# Phrases scored before tokenization (substring match, lowercased).
PHRASES: List[tuple] = [
    ("value for money", 2.5), ("worth every penny", 3), ("worth it", 2), ("waste of money", -3),
    ("waste of time", -2.5), ("not worth", -2), ("paisa vasool", 3), ("paisay vasool", 3),
    ("long lasting", 1.5), ("battery life", 0), ("battery timing", 0), ("no issue", 1),
    ("no issues", 1), ("no problem", 1), ("no complaints", 1.5), ("works fine", 1.5),
    ("working fine", 1.5), ("chalta hai", 1), ("kharab ho gaya", -2.5), ("kharab ho gya", -2.5),
    ("hang ho", -1.5), ("heat ho", -1.5), ("goes dead", -2.5), ("stops working", -2),
]

NEGATORS = {
    "nahi", "nahin", "nai", "nhe", "nh", "na", "not", "never", "no", "without", "kabhi_nahi",
    "نہیں", "نا", "مت", "بغیر",
}
INTENSIFIERS = {
    "bahut", "very", "extremely", "super", "really", "totally", "absolutely", "highly",
    "insanely", "crazily", "itna", "itni", "itne", "kaafi", "kafi", "zyada", "ziada", "bilkul",
    "completely", "utterly", "بہت", "نہایت", "بالکل", "انتہائی",
}
DIMINISHERS = {"thora", "thori", "thore", "thoda", "thodi", "little", "slightly", "somewhat",
               "kuch", "ہلکا", "ذرا", "کچھ"}
CONTRAST = {"but", "however", "although", "though", "yet", "lekin", "lakin", "magar", "balkay",
            "balki", "halanke", "لیکن", "مگر", "بلکہ", "اگرچہ"}
