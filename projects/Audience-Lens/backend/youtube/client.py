"""YouTube Data API v3 client — official REST endpoints via httpx.

No scraping, no innertube. Uses search.list, videos.list, commentThreads.list,
channels.list, playlistItems.list. Tracks quota cost per the official unit costs.
If no API key is configured, every call returns an honest INSUFFICIENT_DATA error.
"""
from __future__ import annotations

import asyncio
from typing import Any

import httpx

from ..config import settings

BASE = "https://www.googleapis.com/youtube/v3"

# Official per-call unit costs
UNIT_COST = {
    "search.list": 100,
    "videos.list": 1,
    "commentThreads.list": 1,
    "channels.list": 1,
    "playlistItems.list": 1,
    "commentThreads.list.replies": 1,
}

# In-process quota counter (production persists to api_quota_usage table)
_quota_used = 0


def quota_state() -> dict[str, Any]:
    return {
        "used": _quota_used,
        "total": settings.youtube_quota_daily,
        "remaining": max(0, settings.youtube_quota_daily - _quota_used),
    }


class YouTubeError(Exception):
    pass


def _require_key() -> str:
    if not settings.youtube_api_key:
        raise YouTubeError(
            "YouTube Data API v3 key not configured. Set YOUTUBE_API_KEY. "
            "Live collection unavailable."
        )
    return settings.youtube_api_key


async def _get(path: str, params: dict[str, Any], cost_key: str) -> dict[str, Any]:
    global _quota_used
    key = _require_key()
    params = {**params, "key": key}
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(f"{BASE}/{path}", params=params)
    _quota_used += UNIT_COST.get(cost_key, 1)
    if resp.status_code == 403 and "quota" in resp.text.lower():
        raise YouTubeError("YouTube API daily quota exhausted.")
    if resp.status_code >= 400:
        raise YouTubeError(f"YouTube API {resp.status_code}: {resp.text[:200]}")
    return resp.json()


async def search_videos(
    query: str,
    country: str = "",
    language: str = "",
    published_after: str = "",
    published_before: str = "",
    video_category_id: str = "",
    limit: int = 25,
    page_token: str = "",
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "part": "snippet",
        "type": "video",
        "q": query,
        "maxResults": min(limit, 50),
    }
    if country:
        params["regionCode"] = country
    if language:
        params["relevanceLanguage"] = language
    if published_after:
        params["publishedAfter"] = published_after
    if published_before:
        params["publishedBefore"] = published_before
    if video_category_id:
        params["videoCategoryId"] = video_category_id
    if page_token:
        params["pageToken"] = page_token
    data = await _get("search", params, "search.list")
    items = []
    for it in data.get("items", []):
        sn = it.get("snippet", {})
        items.append({
            "video_id": it.get("id", {}).get("videoId", ""),
            "title": sn.get("title", ""),
            "channel_id": sn.get("channelId", ""),
            "channel_name": sn.get("channelTitle", ""),
            "published_at": sn.get("publishedAt", ""),
            "description": sn.get("description", "")[:300],
            "thumbnail": (sn.get("thumbnails", {}).get("medium", {}) or {}).get("url", ""),
        })
    return {
        "videos": items,
        "next_page_token": data.get("nextPageToken", ""),
        "total_results": data.get("pageInfo", {}).get("totalResults", len(items)),
        "quota": quota_state(),
        "provenance": "LIVE_DATA",
    }


async def get_videos(video_ids: list[str]) -> dict[str, Any]:
    if not video_ids:
        return {"videos": [], "provenance": "LIVE_DATA"}
    params = {"part": "snippet,statistics,contentDetails", "id": ",".join(video_ids[:50])}
    data = await _get("videos", params, "videos.list")
    items = []
    for it in data.get("items", []):
        sn = it.get("snippet", {})
        st = it.get("statistics", {})
        cd = it.get("contentDetails", {})
        items.append({
            "video_id": it.get("id", ""),
            "title": sn.get("title", ""),
            "channel_id": sn.get("channelId", ""),
            "channel_name": sn.get("channelTitle", ""),
            "published_at": sn.get("publishedAt", ""),
            "duration": cd.get("duration", ""),
            "category_id": sn.get("categoryId", ""),
            "tags": sn.get("tags", []),
            "description": sn.get("description", "")[:500],
            "view_count": int(st.get("viewCount", 0)),
            "like_count": int(st.get("likeCount", 0)),
            "comment_count": int(st.get("commentCount", 0)),
            "thumbnail": (sn.get("thumbnails", {}).get("medium", {}) or {}).get("url", ""),
        })
    return {"videos": items, "quota": quota_state(), "provenance": "LIVE_DATA"}


async def get_comments(video_id: str, limit: int = 100, page_token: str = "") -> dict[str, Any]:
    params = {"part": "snippet", "videoId": video_id, "maxResults": min(limit, 100), "textFormat": "plainText"}
    if page_token:
        params["pageToken"] = page_token
    try:
        data = await _get("commentThreads", params, "commentThreads.list")
    except YouTubeError as e:
        if "disabled" in str(e).lower() or "comments" in str(e).lower():
            return {"comments": [], "disabled": True, "provenance": "INSUFFICIENT_DATA", "error": str(e)}
        raise
    comments = []
    for it in data.get("items", []):
        top = it.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
        comments.append({
            "comment_id": it.get("id", ""),
            "video_id": video_id,
            "text": top.get("textDisplay", top.get("textOriginal", "")),
            "author": top.get("authorDisplayName", ""),
            "author_channel_id": top.get("authorChannelId", {}).get("value", ""),
            "published_at": top.get("publishedAt", ""),
            "like_count": int(top.get("likeCount", 0)),
            "reply_count": int(it.get("snippet", {}).get("totalReplyCount", 0)),
            "comment_url": f"https://www.youtube.com/watch?v={video_id}&lc={it.get('id', '')}",
        })
    return {
        "comments": comments,
        "next_page_token": data.get("nextPageToken", ""),
        "quota": quota_state(),
        "provenance": "LIVE_DATA",
    }


async def get_channel(channel_id_or_handle: str) -> dict[str, Any]:
    params = {"part": "snippet,contentDetails,statistics"}
    if channel_id_or_handle.startswith("@"):
        params["forHandle"] = channel_id_or_handle
    elif channel_id_or_handle.startswith("UC"):
        params["id"] = channel_id_or_handle
    else:
        params["forUsername"] = channel_id_or_handle
    data = await _get("channels", params, "channels.list")
    items = []
    for it in data.get("items", []):
        sn = it.get("snippet", {})
        st = it.get("statistics", {})
        cd = it.get("contentDetails", {})
        items.append({
            "channel_id": it.get("id", ""),
            "title": sn.get("title", ""),
            "description": sn.get("description", "")[:300],
            "country": sn.get("country", ""),
            "uploads_playlist_id": cd.get("relatedPlaylists", {}).get("uploads", ""),
            "subscriber_count": int(st.get("subscriberCount", 0)),
            "video_count": int(st.get("videoCount", 0)),
            "view_count": int(st.get("viewCount", 0)),
            "thumbnail": (sn.get("thumbnails", {}).get("medium", {}) or {}).get("url", ""),
        })
    return {"channels": items, "quota": quota_state(), "provenance": "LIVE_DATA"}


async def get_playlist_videos(playlist_id: str, limit: int = 50, page_token: str = "") -> dict[str, Any]:
    params = {"part": "snippet,contentDetails", "playlistId": playlist_id, "maxResults": min(limit, 50)}
    if page_token:
        params["pageToken"] = page_token
    data = await _get("playlistItems", params, "playlistItems.list")
    items = []
    for it in data.get("items", []):
        cd = it.get("contentDetails", {})
        sn = it.get("snippet", {})
        items.append({
            "video_id": cd.get("videoId", ""),
            "title": sn.get("title", ""),
            "published_at": cd.get("videoPublishedAt", ""),
            "position": sn.get("position", 0),
        })
    return {
        "videos": items,
        "next_page_token": data.get("nextPageToken", ""),
        "quota": quota_state(),
        "provenance": "LIVE_DATA",
    }


async def research(
    query: str,
    country: str = "",
    max_videos: int = 5,
    comments_per_video: int = 40,
    aspect_catalog: str = "general",
) -> dict[str, Any]:
    """Integrated collection → analysis pipeline.

    Searches videos for a query, fetches comments for each, then runs the full
    multilingual NLP batch (Project A) over every collected comment. Returns
    videos, comments, and the sentiment distribution in one call.
    """
    from ..nlp.pipeline import analyze_batch

    search_res = await search_videos(query, country=country, limit=max_videos)
    videos = search_res["videos"]
    all_comments: list[dict[str, Any]] = []
    video_summaries: list[dict[str, Any]] = []

    for v in videos:
        try:
            cres = await get_comments(v["video_id"], limit=comments_per_video)
            comments = cres.get("comments", [])
        except YouTubeError:
            comments = []
        all_comments.extend(comments)
        video_summaries.append({
            **v,
            "comment_count": len(comments),
            "thumbnail": v.get("thumbnail", ""),
        })

    comment_texts = [c["text"] for c in all_comments if c.get("text")]
    nlp = analyze_batch(comment_texts, aspect_catalog) if comment_texts else {
        "results": [], "count": 0, "distribution": {},
        "distribution_pct": {}, "language_distribution": {},
        "avg_score": 0.0, "topics": [], "provenance": "INSUFFICIENT_DATA",
        "sample_disclaimer": "No comments collected.",
    }

    return {
        "query": query,
        "country": country,
        "videos": video_summaries,
        "n_videos": len(video_summaries),
        "comments": all_comments,
        "n_comments": len(all_comments),
        "sentiment": nlp,
        "quota": quota_state(),
        "provenance": "LIVE_DATA",
        "note": "Collection via official YouTube Data API v3. Organic metrics only — not advertising performance.",
    }
