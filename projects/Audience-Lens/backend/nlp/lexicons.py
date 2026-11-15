"""Multilingual sentiment lexicons — English, Urdu script, Roman Urdu, code-mixed.

Ported and extended from the Raye (Review-Lens) project. Each entry maps a
surface token to a sentiment weight in [-1, 1]. These are transparent,
auditable lexicons — not a black-box model. A transformer backend can be
dropped in later; this engine remains the explainable baseline.
"""

# Positive words: token -> weight
POSITIVE: dict[str, float] = {
    # English
    "good": 0.8, "great": 1.0, "excellent": 1.1, "amazing": 1.1, "awesome": 1.1,
    "best": 1.0, "love": 1.0, "loved": 1.0, "lovely": 0.9, "nice": 0.7,
    "perfect": 1.1, "fantastic": 1.1, "wonderful": 1.0, "superb": 1.0,
    "happy": 0.8, "satisfied": 0.8, "recommend": 0.9, "recommended": 0.9,
    "worth": 0.7, "durable": 0.6, "fast": 0.5, "smooth": 0.6, "quality": 0.6,
    "premium": 0.7, "reliable": 0.7, "value": 0.5, "impressed": 0.9,
    "brilliant": 1.0, "stunning": 0.9, "beautiful": 0.8, "cool": 0.6,
    "like": 0.5, "liked": 0.5, "enjoy": 0.7, "enjoyed": 0.7, "win": 0.7,
    # Roman Urdu
    "acha": 0.8, "accha": 0.8, "acca": 0.8, "achha": 0.8, "khoob": 0.8,
    "khoobsurat": 0.9, "zabardast": 1.0, "kamal": 1.0, "mast": 0.9,
    "behtareen": 1.0, "bhari": 0.7, "lajawab": 1.0, "pyara": 0.8,
    "wah": 0.7, "shandaar": 1.0, "firstclass": 0.8, "solid": 0.6,
    "pasand": 0.7, "pasand hai": 0.8, "maza": 0.7, "mazaa": 0.7,
    # Urdu script
    "اچھا": 0.8, "اچھی": 0.8, "بہترین": 1.0, "زبردست": 1.0, "کمال": 1.0,
    "شاندار": 1.0, "پسند": 0.7, "محبت": 0.8, "خوبصورت": 0.9,
}

# Negative words: token -> weight (stored positive; sign applied in scoring)
NEGATIVE: dict[str, float] = {
    # English
    "bad": 0.8, "worst": 1.1, "terrible": 1.1, "horrible": 1.1, "awful": 1.0,
    "poor": 0.8, "hate": 1.0, "hated": 1.0, "disappointed": 0.9,
    "disappointing": 0.9, "disappointment": 0.9, "broken": 0.8, "broke": 0.7,
    "fake": 0.8, "waste": 0.9, "useless": 0.9, "pathetic": 1.0,
    "slow": 0.5, "laggy": 0.7, "buggy": 0.7, "crash": 0.7, "crashed": 0.8,
    "expensive": 0.5, "overpriced": 0.7, "cheap": 0.5, "flimsy": 0.6,
    "frustrating": 0.8, "frustrated": 0.8, "annoying": 0.7, "issue": 0.5,
    "issues": 0.5, "problem": 0.5, "defective": 0.8, "faulty": 0.8,
    "refund": 0.6, "return": 0.4, "scam": 0.9, "fraud": 0.9,
    # Roman Urdu
    "bura": 0.8, "bura hai": 0.8, "kharab": 0.9, "kharaab": 0.9,
    "bekaar": 0.9, "bekar": 0.9, "ghaat": 0.8, "ghatiya": 1.0,
    "kharab hai": 0.9, "fraud": 0.9, "dhoka": 0.9, "takleef": 0.7,
    "masla": 0.5, "pareshani": 0.6, "boring": 0.6, "bor": 0.5,
    "zillat": 0.8, "nuqsan": 0.6, "bigaar": 0.7,
    # Urdu script
    "برا": 0.8, "خراب": 0.9, "بیکار": 0.9, "گھٹیا": 1.0, " Dhoka": 0.9,
    "دھوکہ": 0.9, "نقصان": 0.6, "مشکل": 0.5, "مسلہ": 0.5, "پریشانی": 0.6,
}

# Negators — flip sentiment in a window before OR after (Urdu allows post-negation)
NEGATORS: set[str] = {
    "not", "no", "never", "none", "neither", "nor", "without", "isn't", "wasn't",
    "aren't", "don't", "doesn't", "didn't", "won't", "can't", "couldn't",
    "nahi", "nahin", "nai", "nhe", "na", "mat", "nahi hai", "nahi hua",
    "نہیں", "نہ", "مت",
}

# Intensifiers — amplify the next/previous sentiment word
INTENSIFIERS: set[str] = {
    "very", "really", "so", "too", "extremely", "super", "highly", "totally",
    "absolutely", "incredibly", "remarkably",
    "bohat", "bahut", "bohot", "bhot", "bht", "ziyada", "zyada", "kafi",
    "bohut", "bhut", "tairha", "beshumar",
    "بہت", "زیادہ", "کافی",
}

# Diminishers — soften the sentiment word
DIMINISHERS: set[str] = {
    "little", "slightly", "bit", "kinda", "somewhat", "fairly", "rather",
    "thora", "thora sa", "thora", "halka", "kam",
    "تھوڑا", "کم",
}

# Contrast words — split clauses so mixed sentiment is detected correctly
CONTRAST: set[str] = {
    "but", "however", "although", "though", "yet", "still", "nevertheless",
    "nonetheless", "whereas", "while",
    "lekin", "lakin", "magar", "balkay", "balki", "halanke", "phir bhi",
    "لیکن", "مگر", "بلکہ", "اگرچہ", "پھر بھی",
}

# Multi-word phrase overrides (applied before token scoring)
PHRASES: dict[str, float] = {
    "not good": -0.9, "not bad": 0.6, "not worth": -0.8, "not happy": -0.8,
    "acha nahi": -0.8, "accha nahi": -0.8, "achha nahi hai": -0.8,
    "theek nahi": -0.6, "thik nahi": -0.6,
    "worth buying": 0.8, "highly recommend": 1.1, "waste of money": -1.0,
    "value for money": 0.8, "value for the money": 0.8,
}
