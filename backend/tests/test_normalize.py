from app.nlp.normalize import normalize_text, normalize_token


def test_variant_spellings_collapse():
    for variant in ["bohat", "bohot", "bhot", "bhut", "bht", "bohut"]:
        assert normalize_token(variant) == "bahut", variant


def test_negation_variants_collapse():
    for variant in ["nahi", "nahin", "nai", "nhe", "nhi"]:
        assert normalize_token(variant) == "nahi", variant


def test_common_texting_forms():
    assert normalize_token("gr8") == "great"
    assert normalize_token("plz") == "please"
    assert normalize_token("gud") == "good"


def test_repeated_letters_collapse():
    assert normalize_token("soooo") == "so"
    assert normalize_token("loooove") == "love"


def test_normalize_text_preserves_urdu_script():
    text = "یہ فون بہت اچھا ہے"
    norm = normalize_text(text)
    assert "بہت" in norm and "اچھا" in norm


def test_normalize_text_lowercases_and_maps():
    assert "bahut" in normalize_text("Bohat aCHA hai")
