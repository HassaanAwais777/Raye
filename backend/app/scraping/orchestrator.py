"""Job orchestrator: fans out crawlers, streams comments through the NLP
pipeline while crawling continues, then builds the evidence-based verdict."""
import asyncio
import time
import traceback
from typing import Dict, List

from ..analysis.verdict import build_result
from ..config import settings
from ..db import insert_comments, update_analysis
from ..nlp.pipeline import analyze_batch
from .base import CrawlController
from .registry import ADAPTERS

_SENTINEL = "__RAYE_SENTINEL__"


class Orchestrator:
    def __init__(self, job) -> None:  # job: jobs.JobState (avoids a circular import)
        self.job = job

    async def run(self) -> None:
        job = self.job
        req = job.request
        t0 = time.monotonic()
        queue: asyncio.Queue = asyncio.Queue(maxsize=8000)
        ctrl = CrawlController(
            query=req.query, sources_per_platform=req.sources_per_platform,
            comments_per_source=req.comments_per_source,
            max_total=min(req.max_comments, settings.max_total_comments), queue=queue)
        job.progress = {"fetched": 0, "analyzed": 0, "duplicates": 0,
                        "per_platform": {}, "phase": "fetching"}

        consumer = asyncio.create_task(self._consume(queue, ctrl))
        try:
            results = await asyncio.gather(
                *(ADAPTERS[name]().crawl(ctrl) for name in job.platforms),
                return_exceptions=True)
            platform_stats: Dict[str, Dict] = {}
            for name, res in zip(job.platforms, results):
                fetched = ctrl.per_platform.get(name, 0)
                if isinstance(res, Exception):
                    platform_stats[name] = {"fetched": fetched, "ok": fetched > 0,
                                            "error": f"{type(res).__name__}: {res}"[:300]}
                else:
                    platform_stats[name] = {"fetched": fetched, "ok": fetched > 0, "error": None}
            job.progress["per_platform"] = platform_stats

            await queue.put(_SENTINEL)
            await consumer

            job.progress["phase"] = "aggregating"
            update_analysis(job.id, phase="aggregating", progress=job.progress)
            result = build_result(req.query, job.comments, platform_stats, ctrl.warnings,
                                  time.monotonic() - t0)
            result["totals"]["fetched"] = ctrl.total_fetched
            result["totals"]["duplicates_removed"] = ctrl.duplicates
            job.result = result
            job.status, job.phase = "done", "done"
            update_analysis(job.id, status="done", phase="done", progress=job.progress,
                            result=result)
        except Exception as exc:
            traceback.print_exc()
            job.status, job.error = "failed", str(exc)[:500]
            update_analysis(job.id, status="failed", error=job.error)
        finally:
            if not consumer.done():
                consumer.cancel()

    async def _consume(self, queue: asyncio.Queue, ctrl: CrawlController) -> None:
        batch: List[Dict] = []
        loop = asyncio.get_running_loop()
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            queue.task_done()
            if item == _SENTINEL:
                break
            batch.append(item)
            if len(batch) >= settings.analyze_batch_size:
                await self._flush(batch, ctrl, loop)
                batch = []
        if batch:
            await self._flush(batch, ctrl, loop)

    async def _flush(self, batch: List[Dict], ctrl: CrawlController, loop) -> None:
        if not self.job.progress.get("phase") == "analyzing":
            self.job.progress["phase"] = "analyzing"
        analyzed = await loop.run_in_executor(None, analyze_batch, batch)
        self.job.comments.extend(analyzed)
        self.job.progress["fetched"] = ctrl.total_fetched
        self.job.progress["analyzed"] = len(self.job.comments)
        self.job.progress["duplicates"] = ctrl.duplicates
        insert_comments(self.job.id, analyzed)
        update_analysis(self.job.id, progress=self.job.progress)
