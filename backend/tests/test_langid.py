from app.nlp.langid import detect_language


def test_english():
    assert detect_language("This phone is amazing and the battery life is great overall") == "en"


def test_urdu_script():
    assert detect_language("یہ فون بہت اچھا ہے اور بیٹری بھی اچھی ہے") == "ur"


def test_roman_urdu():
    assert detect_language("bohat acha phone hai bhai lekin battery kharab hai") == "ur-Roman"


def test_code_mixed():
    assert detect_language("yaar this phone bohat acha hai and camera bhi great hai") == "code-mixed"


def test_empty_defaults_english():
    assert detect_language("12345 !!!") == "en"
