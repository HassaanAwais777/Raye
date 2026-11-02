"""YouTube crawler — no API key required.

Uses YouTube's public web endpoints (the same innertube API every youtube.com
page uses): search results + watch pages + `youtubei/v1/next` continuations.
Supports both the current `commentEntityPayload` format and the legacy
`commentRenderer` format. Every comment gets a deep link via `&lc=<comment id>`.
"""
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterator, List, Optional
from urllib.parse import quote_plus

import httpx

from ..config import settings
from .base import CrawlController, PlatformAdapter, with_review
from .ratelimit import request_with_retry

_RESULTS_URL = "https://www.youtube.com/results?search_query={q}&sp=EgIQAQ%3D%3D"  # Type=Video
_WATCH_URL = "https://www.youtube.com/watch?v={vid}&bpctr=9999999999&has_verified=1"
_NEXT_URL = "https://www.youtube.com/youtubei/v1/next?prettyPrint=false"
# Public innertube key embedded in every YouTube web page (same one yt-dlp uses).
_PUBLIC_KEY = "AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"
_CONTEXT = {"context": {"client": {"clientName": "WEB", "clientVersion": "2.20240726.00.00",
                                   "hl": "en", "gl": "US"}}}
_JSON_KEY_RE = re.compile(r"var ytInitialData\s*=\s*")


def _extract_json(html: str) -> Dict[str, Any]:
    """Robustly pull the `ytInitialData` JSON blob out of a page."""
    match = _JSON_KEY_RE.search(html)
    if not match:
        raise ValueError("ytInitialData not found in page HTML")
    start = html.index("{", match.end())
    obj, _ = json.JSONDecoder().raw_decode(html[start:])
    return obj


def _walk(obj: Any, key: str) -> Iterator[Any]:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key:
                yield v
            yield from _walk(v, key)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk(item, key)


def _parse_count(text: Optional[str]) -> int:
    if not text:
        return 0
    t = str(text).strip().replace(",", "")
    mult = 1
    if t.endswith("K"):
        mult, t = 1_000, t[:-1]
    elif t.endswith("M"):
        mult, t = 1_000_000, t[:-1]
    m = re.search(r"-?\d+(\.\d+)?", t)
    if not m:
        return 0
    return int(float(m.group()) * mult)


_AGO_RE = re.compile(r"(\d+)\s+(second|minute|hour|day|week|month|year)s?\s+ago", re.IGNORECASE)


def _parse_published(text: Optional[str]) -> str:
    """'3 weeks ago' -> approximate ISO date (raw text is kept separately)."""
    if not text:
        return ""
    m = _AGO_RE.search(text)
    if not m:
        return ""
    n, unit = int(m.group(1)), m.group(2).lower()
    deltas = {"second": timedelta(seconds=n), "minute": timedelta(minutes=n),
              "hour": timedelta(hours=n), "day": timedelta(days=n),
              "week": timedelta(weeks=n), "month": timedelta(days=30 * n),
              "year": timedelta(days=365 * n)}
    return (datetime.now(timezone.utc) - deltas[unit]).date().isoformat()


def _dig_token(obj: Any) -> Optional[str]:
    cir = obj.get("continuationItemRenderer") if isinstance(obj, dict) else None
    if not cir:
        return None
    return (((cir.get("continuationEndpoint") or {}).get("continuationCommand") or {}).get("token"))


def find_comment_token(data: Dict[str, Any]) -> Optional[str]:
    """Locate the top-level comments continuation token on a watch page."""
    for panel in data.get("engagementPanels") or []:
        content = ((panel.get("engagementPanelSectionListRenderer") or {}).get("content") or {})
        for section in (content.get("sectionListRenderer") or {}).get("contents") or []:
            for item in (section.get("itemSectionRenderer") or {}).get("contents") or []:
                tok = _dig_token(item)
                if tok:
                    return tok
    for cir in _walk(data, "continuationItemRenderer"):
        tok = _dig_token(cir)
        if tok:
            return tok
    return None


def _next_token_from_response(data: Dict[str, Any]) -> Optional[str]:
    """Top-level last continuationItemRenderer of continuationItems = next page."""
    token = None
    for endpoint in data.get("onResponseReceivedEndpoints") or []:
        for key in ("appendContinuationItemsAction", "reloadContinuationItemsCommand"):
            items = (endpoint.get(key) or {}).get("continuationItems")
            if items:
                tok = _dig_token(items[-1])
                if tok:
                    token = tok
    return token


def parse_next_response(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract comments from a youtubei/v1/next response (new + legacy formats)."""
    comments: List[Dict[str, Any]] = []
    mutations = (((data.get("frameworkUpdates") or {}).get("entityBatchUpdate") or {})
                 .get("mutations")) or []
    for m in mutations:
        payload = (m.get("payload") or {}).get("commentEntityPayload")
        if not payload:
            continue
        props = payload.get("properties") or {}
        content = ((props.get("content") or {}).get("content")) or ""
        if not content:
            continue
        cid = props.get("commentId") or ((payload.get("key") or "").split("-") or [""])[-1]
        published = props.get("publishedTime") or ""
        if not published:
            published = ((props.get("publishedTimeText") or {}).get("content")) or ""
        comments.append({
            "id": cid,
            "text_raw": content,
            "author": ((payload.get("author") or {}).get("displayName")) or "unknown",
            "likes": _parse_count((payload.get("toolbar") or {}).get("likeCountNotliked")
                                  or (payload.get("toolbar") or {}).get("likeCountLiked") or "0"),
            "published": published,
        })
    if not comments:  # legacy format fallback
        for cr in _walk(data, "commentRenderer"):
            runs = ((cr.get("contentText") or {}).get("runs")) or []
            content = "".join(r.get("text", "") for r in runs)
            if not content:
                continue
            comments.append({
                "id": cr.get("commentId") or "",
                "text_raw": content,
                "author": ((cr.get("authorText") or {}).get("simpleText")) or "unknown",
                "likes": _parse_count((cr.get("voteCount") or {}).get("simpleText")),
                "published": (cr.get("publishedTimeText") or {}).get("simpleText", "")
                if isinstance(cr.get("publishedTimeText"), dict) else "",
            })
    return comments


def parse_search_results(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    videos: List[Dict[str, Any]] = []
    seen: set = set()
    for vr in _walk(data, "videoRenderer"):
        vid = vr.get("videoId")
        if not vid or vid in seen:
            continue
        seen.add(vid)
        title = (((vr.get("title") or {}).get("runs")) or [{}])[0].get("text", "") \
            if isinstance(vr.get("title"), dict) else vr.get("title", {})
        channel_runs = ((vr.get("ownerText") or {}).get("runs")) or [{}]
        videos.append({
            "video_id": vid,
            "title": title,
            "channel": channel_runs[0].get("text", "unknown"),
            "views": _parse_count((vr.get("viewCountText") or {}).get("simpleText")),
            "published": (vr.get("publishedTimeText") or {}).get("simpleText", "")
            if isinstance(vr.get("publishedTimeText"), dict) else "",
        })
    return videos


class YouTubeAdapter(PlatformAdapter):
    name = "youtube"
    label = "YouTube review videos & comments"
    experimental = False
    enabled_by_default = True
    rate = 1.0

    async def crawl(self, ctrl: CrawlController) -> None:
        bucket = self.bucket()
        async with self.make_client() as client:
            videos = await self._search(client, bucket, ctrl.query, ctrl.sources_per_platform)
            for video in videos:
                if ctrl.should_stop:
                    return
                try:
                    await self._video_comments(client, bucket, video, ctrl)
                except Exception as exc:  # degrade per video, never kill the job
                    ctrl.warnings.append(f"youtube: video {video['video_id']} skipped ({exc})")

    async def _search(self, client: httpx.AsyncClient, bucket, query: str,
                      limit: int) -> List[Dict[str, Any]]:
        url = _RESULTS_URL.format(q=quote_plus(with_review(query)))
        resp = await request_with_retry(client, "GET", url, bucket=bucket)
        resp.raise_for_status()
        data = _extract_json(resp.text)
        return parse_search_results(data)[:limit]

    async def _video_comments(self, client: httpx.AsyncClient, bucket, video: Dict[str, Any],
                              ctrl: CrawlController) -> None:
        vid = video["video_id"]
        source = {
            "platform": self.name, "source_id": vid, "title": video.get("title") or vid,
            "url": f"https://www.youtube.com/watch?v={vid}", "channel": video.get("channel", ""),
        }
        resp = await request_with_retry(client, "GET", _WATCH_URL.format(vid=vid), bucket=bucket)
        resp.raise_for_status()
        token = find_comment_token(_extract_json(resp.text))
        if not token:
            return  # comments disabled on this video

        collected = 0
        cap = ctrl.comments_per_source
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        while token and collected < cap and not ctrl.should_stop:
            payload = {**_CONTEXT, "continuation": token}
            resp = await request_with_retry(
                client, "POST", _NEXT_URL, bucket=bucket,
                params={"key": _PUBLIC_KEY}, json=payload,
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
            for c in parse_next_response(data):
                if collected >= cap or ctrl.should_stop:
                    break
                if not c.get("text_raw"):
                    continue
                await ctrl.add_raw({
                    "id": f"yt-{vid}-{c['id']}" if c.get("id") else None,
                    "text_raw": c["text_raw"],
                    "author": c.get("author", "unknown"),
                    "likes": c.get("likes", 0),
                    "published": _parse_published(c.get("published")),
                    "published_raw": c.get("published", ""),
                    "fetched_at": now,
                    "source": {**source, "comment_url": f"https://www.youtube.com/watch?v={vid}&lc={c.get('id', '')}"},
                })
                collected += 1
            token = _next_token_from_response(data)
