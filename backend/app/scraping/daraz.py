"""Daraz (Pakistan) crawler — EXPERIMENTAL.

Reviews are embedded in each product page's `window.pageData` JSON. Daraz
changes its markup frequently and some regions are bot-protected, so this
adapter degrades gracefully: failures surface as job warnings, never crashes.
"""
import datetime as _dt
import json
from typing import Any, Dict, Iterator, List
from urllib.parse import quote_plus

import httpx

from .base import CrawlController, PlatformAdapter, with_review
from .ratelimit import request_with_retry

_SEARCH_URL = "https://www.daraz.pk/catalog/?q={q}"
_PAGE_DATA_RE = "window.pageData="


def _extract_page_data(html: str) -> Dict[str, Any]:
    idx = html.find(_PAGE_DATA_RE)
    if idx == -1:
        raise ValueError("pageData not found")
    start = html.index("{", idx)
    obj, _ = json.JSONDecoder().raw_decode(html[start:])
    return obj


def _walk_dicts(obj: Any) -> Iterator[Dict[str, Any]]:
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _walk_dicts(v)
    elif isinstance(obj, list):
        for item in obj:
            yield from _walk_dicts(item)


class DarazAdapter(PlatformAdapter):
    name = "daraz"
    label = "Daraz.pk product reviews (experimental)"
    experimental = True
    enabled_by_default = False
    rate = 0.7

    async def crawl(self, ctrl: CrawlController) -> None:
        bucket = self.bucket()
        async with self.make_client() as client:
            try:
                products = await self._search(client, bucket, ctrl.query, ctrl.sources_per_platform)
            except Exception as exc:
                ctrl.warnings.append(f"daraz: search failed ({exc})")
                return
            for url, title in products:
                if ctrl.should_stop:
                    return
                try:
                    await self._product_reviews(client, bucket, url, title, ctrl)
                except Exception as exc:
                    ctrl.warnings.append(f"daraz: product skipped ({exc})")

    async def _search(self, client: httpx.AsyncClient, bucket, query: str,
                      limit: int) -> List[tuple]:
        resp = await request_with_retry(client, "GET", _SEARCH_URL.format(q=quote_plus(query)),
                                        bucket=bucket)
        resp.raise_for_status()
        data = _extract_page_data(resp.text)
        items = []
        for d in _walk_dicts(data):
            item_url = d.get("itemUrl")
            if item_url and item_url.startswith("//"):
                name = d.get("name", "product")
                items.append((f"https:{item_url}", name))
            if len(items) >= limit:
                break
        return items

    async def _product_reviews(self, client: httpx.AsyncClient, bucket, url: str, title: str,
                               ctrl: CrawlController) -> None:
        resp = await request_with_retry(client, "GET", url, bucket=bucket)
        resp.raise_for_status()
        data = _extract_page_data(resp.text)
        source = {"platform": self.name, "source_id": url.rsplit("/", 1)[-1].split(".")[0],
                  "title": title, "url": url, "channel": "daraz.pk"}
        now = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        collected = 0
        for d in _walk_dicts(data):
            if ctrl.should_stop or collected >= ctrl.comments_per_source:
                return
            text = d.get("reviewContent") or d.get("review")
            if not text or not isinstance(text, str) or len(text.strip()) < 5:
                continue
            await ctrl.add_raw({
                "id": f"dz-{source['source_id']}-{collected}",
                "text_raw": text.strip(),
                "author": d.get("buyerName") or d.get("reviewerName") or "unknown",
                "likes": 0,
                "published": (d.get("reviewTime") or "")[:10],
                "fetched_at": now,
                "source": {**source, "comment_url": url},
            })
            collected += 1
