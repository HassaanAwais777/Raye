from app.nlp.aspects import extract_aspects
from app.nlp.normalize import normalize_text
from app.nlp.sentiment import analyze_text


def _aspects(text):
    sent = analyze_text(text)
    clauses = [{"text": c["text"], "norm": normalize_text(c["text"]), "score": c["score"]}
               for c in sent["clauses"]]
    return {a["name"]: a for a in extract_aspects(text, clauses, sent["sentiment"], sent["score"])}


def test_battery_aspect_positive():
    res = _aspects("battery backup bohat acha hai is phone ka")
    assert "battery" in res
    assert res["battery"]["sentiment"] == "positive"


def test_price_aspect_negative():
    res = _aspects("qeemat bohat mehnga hai ye phone")
    assert "price" in res
    assert res["price"]["sentiment"] == "negative"


def test_camera_and_battery_mixed():
    res = _aspects("camera acha hai lekin battery kharab hai")
    assert res["camera"]["sentiment"] == "positive"
    assert res["battery"]["sentiment"] == "negative"


def test_multiword_battery_life():
    res = _aspects("battery life is amazing and the display is crisp")
    assert "battery" in res and "display" in res


def test_no_aspects_when_none_mentioned():
    res = _aspects("bohat acha hai")
    # "general" may match via nothing; ensure no battery/camera/price false positives
    assert "battery" not in res and "camera" not in res and "price" not in res
