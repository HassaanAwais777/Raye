from app.analysis.verdict import build_result


def _comment(i, sentiment, score, likes=0, text=None, aspects=None, platform="youtube"):
    return {
        "id": f"c{i}", "text_raw": text or f"comment number {i} with some opinion text here",
        "text_normalized": "norm", "lang": "en", "sentiment": sentiment, "score": score,
        "aspects": aspects or [], "author": f"user{i}", "likes": likes, "published": "",
        "fetched_at": "", "source": {"platform": platform, "source_id": "vid1",
                                     "title": "Review video", "url": "https://youtu.be/vid1",
                                     "comment_url": "https://youtu.be/vid1"},
    }


def _stats(platforms=("youtube",)):
    return {p: {"fetched": 100, "ok": True, "error": None} for p in platforms}


def test_insufficient_below_threshold():
    comments = [_comment(i, "positive", 0.5) for i in range(10)]
    result = build_result("Test Phone", comments, _stats(), [], 1.0, min_reliable_n=150)
    assert result["verdict"]["status"] == "insufficient_evidence"
    assert result["verdict"]["recommendations"], "must explain how to fix"
    assert result["verdict"]["confidence"]["tier"] in ("low", "insufficient")


def test_sufficient_positive():
    comments = ([_comment(i, "positive", 0.8) for i in range(120)] +
                [_comment(i, "neutral", 0.0) for i in range(30)] +
                [_comment(i, "negative", -0.6) for i in range(20)])
    result = build_result("Test Phone", comments, _stats(), [], 1.0, min_reliable_n=150)
    assert result["verdict"]["status"] == "sufficient"
    assert "positively" in result["verdict"]["headline"].lower()
    assert result["verdict"]["confidence"]["score"] > 0
    assert len(result["evidence"]["positive"]) > 0
    # traceability: evidence links back to the source video
    ev = result["evidence"]["positive"][0]
    assert ev["comment_url"].startswith("https://youtu.be/")


def test_sufficient_mixed():
    comments = ([_comment(i, "positive", 0.9, likes=5) for i in range(80)] +
                [_comment(i, "negative", -0.9, likes=5) for i in range(80)])
    result = build_result("Test Phone", comments, _stats(), [], 1.0, min_reliable_n=150)
    assert result["verdict"]["status"] == "sufficient"
    assert "divided" in result["verdict"]["headline"].lower()


def test_aspect_scorecard_and_honesty_badge():
    aspects = [{"name": "battery", "label": "Battery & charging",
                "sentiment": "positive", "score": 0.8}]
    comments = [_comment(i, "positive", 0.8, aspects=aspects) for i in range(160)]
    result = build_result("Test Phone", comments, _stats(), [], 1.0, min_reliable_n=150)
    battery = [a for a in result["aspects"] if a["name"] == "battery"][0]
    assert battery["mentions"] == 160
    assert battery["status"] == "ok"
    # single rare aspect gets the insufficient badge instead of a trusted score
    rare = [{"name": "audio", "label": "Audio & speakers", "sentiment": "positive", "score": 0.5}]
    comments_rare = [_comment(i, "positive", 0.8, aspects=rare) for i in range(5)]
    result2 = build_result("Test Phone", comments_rare, _stats(), [], 1.0, min_reliable_n=150)
    assert result2["verdict"]["status"] == "insufficient_evidence"


def test_no_platform_data_warning():
    result = build_result("Test Phone", [], {"youtube": {"fetched": 0, "ok": False,
                                                         "error": "blocked"}}, [], 1.0)
    assert result["verdict"]["status"] == "insufficient_evidence"
    assert any("No platform" in w for w in result["warnings"])
