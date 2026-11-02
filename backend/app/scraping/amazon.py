"""Amazon product review crawler — EXPERIMENTAL.

Amazon uses aggressive bot protection; this adapter often needs residential
proxies in production. It is included to demonstrate the pluggable multi-platform
architecture and fails gracefully (warnings, not crashes) when blocked.
"""
import datetime as _dt
import re
from typing import Any, Dict, List
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from .base import CrawlController, PlatformAdapter
from .ratelimit import request_with_retry

_SEARCH_URL = "https://www.amazon.com/s?k={q}"
_REVIEWS_URL = "https://www.amazon.com/product-reviews/{asin}/?pageNumber={page}&sortBy=recent"
_ASIN_RE = re.compile(r'data-asin="([0-9A-Z]{10})"')


class AmazonAdapter(PlatformAdapter):
    name = "amazon"
    label = "Amazon.com verified purchase reviews (experimental)"
    experimental = True
    enabled_by_default = False
    rate = 0.5

    async def crawl(self, ctrl: CrawlController) -> None:
        bucket = self.bucket()
        async with self.make_client() as client:
            try:
                asins = await self._search(client, bucket, ctrl.query, ctrl.sources_per_platform)
            except Exception as exc:
                ctrl.warnings.append(f"amazon: search failed ({exc})")
                return
            if not asins:
                ctrl.warnings.append("amazon: no products found (possibly bot-blocked)")
            for asin, title in asins:
                if ctrl.should_stop:
                    return
                try:
                    await self._product_reviews(client, bucket, asin, title, ctrl)
                except Exception as exc:
                    ctrl.warnings.append(f"amazon: product {asin} skipped ({exc})")

    async def _search(self, client: httpx.AsyncClient, bucket, query: str,
                      limit: int) -> List[tuple]:
        resp = await request_with_retry(client, "GET", _SEARCH_URL.format(q=quote_plus(query)),
                                        bucket=bucket)
        resp.raise_for_status()
        asins: List[tuple] = []
        seen: set = set()
        for m in _ASIN_RE.finditer(resp.text):
            asin = m.group(1)
            if asin not in seen:
                seen.add(asin)
                asins.append((asin, f"Amazon product {asin}"))
            if len(asins) >= limit:
                break
        return asins

    async def _product_reviews(self, client: httpx.AsyncClient, bucket, asin: str, title: str,
                               ctrl: CrawlController) -> None:
        source = {"platform": self.name, "source_id": asin, "title": title,
                  "url": f"https://www.amazon.com/dp/{asin}", "channel": "amazon.com"}
        now = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
        collected = 0
        for page in range(1, 11):
            if ctrl.should_stop or collected >= ctrl.comments_per_source:
                return
            resp = await request_with_retry(client, "GET", _REVIEWS_URL.format(asin=asin, page=page),
                                            bucket=bucket)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")
            reviews = soup.select('div[data-hook="review"]')
            if not reviews:
                break
            for rev in reviews:
                body_el = rev.select_one('div[data-hook="review-body"]')
                body = body_el.get_text(" ", strip=True) if body_el else ""
                if len(body) < 10:
                    continue
                author_el = rev.select_one("span.a-profile-name")
                date_el = rev.select_one('span[data-hook="review-date"]')
                await ctrl.add_raw({
                    "id": f"am-{asin}-{rev.get('id', collected)}",
                    "text_raw": body[:2000],
                    "author": author_el.get_text(strip=True) if author_el else "unknown",
                    "likes": 0,
                    "published": (date_el.get_text(strip=True) if date_el else "")[:40],
                    "fetched_at": now,
                    "source": {**source, "comment_url": f"https://www.amazon.com/product-reviews/{asin}/"},
                })
                collected += 1
