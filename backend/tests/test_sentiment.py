import pytest

from app.nlp.sentiment import analyze_text


def test_positive_roman_urdu_with_intensifier():
    res = analyze_text("bohat acha phone hai bhai")
    assert res["sentiment"] == "positive"
    assert res["score"] > 0.5


def test_negative_roman_urdu():
    res = analyze_text("bohot kharab hai ye phone, paisa waste")
    assert res["sentiment"] == "negative"


def test_variant_spelling_same_result():
    a = analyze_text("bohat acha hai")
    b = analyze_text("bhut accha hai")
    assert a["sentiment"] == b["sentiment"] == "positive"


def test_mixed_with_contrast():
    res = analyze_text("camera acha hai lekin battery kharab hai")
    assert res["sentiment"] == "mixed"
    assert res["pos_total"] >= 0.8 and res["neg_total"] >= 0.8


def test_post_negation_urdu_order():
    res = analyze_text("achha nahi hai ye phone")
    assert res["sentiment"] == "negative"


def test_english_negation():
    res = analyze_text("this phone is not good at all")
    assert res["sentiment"] == "negative"


def test_negated_problem_is_positive():
    res = analyze_text("no heating issue at all, works fine")
    assert res["sentiment"] in ("positive",)


def test_english_waste_phrase():
    res = analyze_text("absolute waste of money")
    assert res["sentiment"] == "negative"


def test_urdu_script_positive():
    res = analyze_text("یہ فون بہت اچھا ہے")
    assert res["sentiment"] == "positive"


def test_urdu_script_negative():
    res = analyze_text("یہ فون بہت خراب ہے")
    assert res["sentiment"] == "negative"


def test_neutral_question():
    res = analyze_text("what is the launch date of this phone?")
    assert res["sentiment"] == "neutral"


def test_score_bounds():
    res = analyze_text("amazing excellent perfect love it best purchase ever zabardast")
    assert -1.0 <= res["score"] <= 1.0
