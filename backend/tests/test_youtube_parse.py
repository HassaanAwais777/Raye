import json

from app.scraping.youtube import (_extract_json, _parse_count, _parse_published,
                                  find_comment_token, parse_next_response,
                                  parse_search_results)

FAKE_WATCH_HTML = 'var ytInitialData = {"engagementPanels":[{"engagementPanelSectionListRenderer":{"content":{"sectionListRenderer":{"contents":[{"itemSectionRenderer":{"contents":[{"continuationItemRenderer":{"continuationEndpoint":{"continuationCommand":{"token":"TOKEN123"}}}}]}}]}}}}]};'

NEXT_RESPONSE_NEW = """
{"frameworkUpdates":{"entityBatchUpdate":{"mutations":[
 {"payload":{"commentEntityPayload":{"key":"EhpVZ3ppWFc1OHRBYW40ZTIzSDJwNEFhQUJBZyAoKAE=","properties":
   {"commentId":"Ugxyz123","content":{"content":"Great phone bahut acha"},
    "publishedTime":"2 weeks ago"},
   "author":{"displayName":"Ali Khan"},"toolbar":{"likeCountNotliked":"1.2K"}}}},
 {"payload":{"other":true}}]}},
 "onResponseReceivedEndpoints":[{"appendContinuationItemsAction":{"continuationItems":[
   {"commentThreadRenderer":{}},
   {"continuationItemRenderer":{"continuationEndpoint":{"continuationCommand":{"token":"NEXTTOKEN"}}}}]}}]}
"""

NEXT_RESPONSE_LEGACY = """
{"onResponseReceivedEndpoints":[{"appendContinuationItemsAction":{"continuationItems":[
 {"commentThreadRenderer":{"comment":{"commentRenderer":{"commentId":"Ugleg456",
   "contentText":{"runs":[{"text":"Waste of money"}]},
   "authorText":{"simpleText":"Bob"},
   "voteCount":{"simpleText":"45"},
   "publishedTimeText":{"simpleText":"3 days ago"}}}}}]}}]}
"""

SEARCH_DATA = """
{"contents":{"twoColumnSearchResultsRenderer":{"primaryContents":{"sectionListRenderer":
 {"contents":[{"itemSectionRenderer":{"contents":[{"videoRenderer":{"videoId":"abc123",
   "title":{"runs":[{"text":"Galaxy S24 Review"}]},
   "ownerText":{"runs":[{"text":"Tech Channel"}]},
   "viewCountText":{"simpleText":"1,234,567 views"},
   "publishedTimeText":{"simpleText":"2 months ago"}}}]}}]}}}}}
"""


def test_extract_json_survives_braces_in_string():
    html = 'var ytInitialData = {"a":{"b":"}; tricky"}};'
    assert _extract_json(html)["a"]["b"] == "}; tricky"


def test_find_comment_token():
    data = _extract_json(FAKE_WATCH_HTML)
    assert find_comment_token(data) == "TOKEN123"


def test_parse_new_format():
    comments = parse_next_response(json.loads(NEXT_RESPONSE_NEW))
    assert len(comments) == 1
    c = comments[0]
    assert c["text_raw"] == "Great phone bahut acha"
    assert c["author"] == "Ali Khan"
    assert c["likes"] == 1200
    assert c["published"] == "2 weeks ago"


def test_parse_legacy_format():
    comments = parse_next_response(json.loads(NEXT_RESPONSE_LEGACY))
    assert len(comments) == 1
    c = comments[0]
    assert c["text_raw"] == "Waste of money"
    assert c["author"] == "Bob"
    assert c["likes"] == 45


def test_next_token_from_response():
    data = json.loads(NEXT_RESPONSE_NEW)
    from app.scraping.youtube import _next_token_from_response
    assert _next_token_from_response(data) == "NEXTTOKEN"


def test_parse_search_results():
    videos = parse_search_results(json.loads(SEARCH_DATA))
    assert videos and videos[0]["video_id"] == "abc123"
    assert videos[0]["views"] == 1234567


def test_parse_count():
    assert _parse_count("1.2K") == 1200
    assert _parse_count("3.5M") == 3500000
    assert _parse_count("1,234") == 1234
    assert _parse_count("") == 0


def test_parse_published():
    assert _parse_published("3 weeks ago").count("-") == 2
    assert _parse_published("just now") == ""
