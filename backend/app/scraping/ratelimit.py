"""Polite crawling: token-bucket rate limiting + retry with exponential backoff."""
import asyncio
import random
import time
from typing import Optional

import httpx

RETRY_STATUS = {429, 500, 502, 503, 504}


class AsyncTokenBucket:
    """Classic token bucket; `rate` = requests per second."""

    def __init__(self, rate: float, burst: int = 2) -> None:
        self.rate = rate
        self.capacity = float(max(1, burst))
        self.tokens = self.capacity
        self.updated = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        while True:
            async with self._lock:
                now = time.monotonic()
                self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.rate)
                self.updated = now
                if self.tokens >= 1:
                    self.tokens -= 1
                    return
                wait = (1 - self.tokens) / self.rate
            await asyncio.sleep(wait)


async def request_with_retry(client: httpx.AsyncClient, method: str, url: str, *,
                             bucket: Optional[AsyncTokenBucket] = None,
                             max_retries: int = 3, **kwargs) -> httpx.Response:
    last_exc: Optional[Exception] = None
    for attempt in range(max_retries + 1):
        if bucket:
            await bucket.acquire()
        try:
            resp = await client.request(method, url, **kwargs)
            if resp.status_code in RETRY_STATUS:
                last_exc = httpx.HTTPStatusError(f"HTTP {resp.status_code}", request=resp.request, response=resp)
            else:
                return resp
        except httpx.HTTPError as exc:
            last_exc = exc
        if attempt < max_retries:
            await asyncio.sleep((2 ** attempt) + random.uniform(0, 0.5))
    assert last_exc is not None
    raise last_exc
