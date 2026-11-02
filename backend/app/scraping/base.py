"""Platform adapter contract shared by all crawlers."""
import abc
import asyncio

import httpx

from ..config import settings
from .ratelimit import AsyncTokenBucket


def with_review(query: str) -> str:
    q = query.strip()
    return q if "review" in q.lower() else f"{q} review"


class CrawlController:
    """Shared state all adapters push results through (dedup, queue, budget, progress).

    One controller instance is shared by every enabled adapter so the global
    comment budget (`max_total`) is enforced across platforms.
    """

    def __init__(self, query: str, sources_per_platform: int, comments_per_source: int,
                 max_total: int, queue: "asyncio.Queue") -> None:
        self.query = query
        self.sources_per_platform = sources_per_platform
        self.comments_per_source = comments_per_source
        self.max_total = max_total
        self.queue = queue
        self.stop_event = asyncio.Event()
        self.seen: set = set()
        self.per_platform: dict = {}
        self.total_fetched = 0
        self.duplicates = 0
        self.warnings: list = []

    def note_duplicate(self) -> None:
        self.duplicates += 1

    async def add_raw(self, raw: dict) -> bool:
        """Enqueue a raw comment; returns False if it was a duplicate."""
        platform = raw["source"]["platform"]
        key = (platform, (raw.get("author") or "").lower(),
               (raw.get("text_raw") or "").strip().lower()[:300])
        if key in self.seen:
            self.note_duplicate()
            return False
        self.seen.add(key)
        self.per_platform[platform] = self.per_platform.get(platform, 0) + 1
        self.total_fetched += 1
        await self.queue.put(raw)
        if self.total_fetched >= self.max_total:
            self.stop_event.set()
        return True

    @property
    def should_stop(self) -> bool:
        return self.stop_event.is_set()


class PlatformAdapter(abc.ABC):
    name: str = "base"
    label: str = "Base"
    experimental: bool = False
    enabled_by_default: bool = False
    rate: float = 1.0  # requests per second

    def make_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            headers={"User-Agent": settings.user_agent, "Accept-Language": "en-US,en;q=0.9"},
            timeout=settings.request_timeout,
            follow_redirects=True,
        )

    def bucket(self) -> AsyncTokenBucket:
        return AsyncTokenBucket(self.rate)

    @abc.abstractmethod
    async def crawl(self, ctrl: CrawlController) -> None:
        """Search sources for ctrl.query and push raw comments via ctrl.add_raw()."""
