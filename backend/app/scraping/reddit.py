"""Reddit crawler — public JSON endpoints, no API key required."""
import datetime as _dt
from typing import Any, Dict, List

import httpx

from ..config import settings
from .base import CrawlController, PlatformAdapter, with_review
from .ratelimit import request_with_retry

_SEARCH_URL = "https://www.reddit.com/search.json?q={q}&limit=100&sort=top&t=year&raw_json=1"
_COMMENTS_URL = "https://www.reddit.com/comments/{id}.json?limit={cap}&sort=top&raw_json=1"

_SKIP_AUTHORS = {"automoderator", "[deleted]", "none"}


class RedditAdapter(PlatformAdapter):
    name = "reddit"
    label = "Reddit discussions (r/… product threads)"
    experimental = False
    enabled_by_default = True
    rate = 1.0

    async def crawl(self, ctrl: CrawlController) -> None:
        bucket = self.bucket()
        async with self.make_client() as client:
            posts = await self._search(client, bucket, ctrl.query)
            for post in posts[: ctrl.sources_per_platform]:
                if ctrl.should_stop:
                    return
                try:
                    await self._post_comments(client, bucket, post, ctrl)
                except Exception as exc:
                    ctrl.warnings.append(f"reddit: post {post['id']} skipped ({exc})")

    async def _search(self, client: httpx.AsyncClient, bucket, query: str) -> List[Dict[str, Any]]:
        from urllib.parse import quote_plus
        url = ("https://www.reddit.com/search.json?q=" + quote_plus(with_review(query)) +
               "&limit=100&sort=top&t=year&raw_json=1")
        resp = await request_with_retry(client, "GET", url, bucket=bucket,
                                        headers={"User-Agent": settings.user_agent})
        resp.raise_for_status()
        children = (resp.json().get("data") or {}).get("children") or []
        posts = []
        for ch in children:
            d = ch.get("data") or {}
            if int(d.get("num_comments") or 0) <= 0:
                continue
            posts.append({
                "id": d.get("id"),
                "title": d.get("title", ""),
                "subreddit": d.get("subreddit", ""),
                "permalink": d.get("permalink", ""),
            })
        return posts

    async def _post_comments(self, client: httpx.AsyncClient, bucket, post: Dict[str, Any],
                             ctrl: CrawlController) -> None:
        source = {
            "platform": self.name, "source_id": post["id"], "title": post["title"],
            "url": f"https://www.reddit.com{post['permalink']}", "channel": f"r/{post['subreddit']}",
        }
        resp = await request_with_retry(
            client, "GET", _COMMENTS_URL.format(id=post["id"], cap=ctrl.comments_per_source),
            bucket=bucket)
        resp.raise_for_status()
        payload = resp.json()
        now = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        for ch in ((payload[1] or {}).get("data") or {}).get("children") or []:
            d = ch.get("data") or {}
            body = (d.get("body") or "").strip()
            author = (d.get("author") or "unknown")
            if (not body or body in ("[deleted]", "[removed]") or len(body) < 10
                    or author.lower() in _SKIP_AUTHORS):
                continue
            created = d.get("created_utc")
            published = (_dt.datetime.fromtimestamp(created, _dt.timezone.utc).date().isoformat()
                         if created else "")
            await ctrl.add_raw({
                "id": f"rd-{post['id']}-{d.get('id', '')}",
                "text_raw": body,
                "author": author,
                "likes": int(d.get("score") or 0),
                "published": published,
                "fetched_at": now,
                "source": {**source, "comment_url": f"https://www.reddit.com{d.get('permalink', post['permalink'])}"},
            })
