"""
AjayaDesign Automation — Async build queue.

Simple FIFO queue with configurable concurrency.
One build at a time by default (to avoid resource contention).
"""

import asyncio
import logging
from collections import deque
from typing import Callable, Awaitable, Optional

logger = logging.getLogger(__name__)


class BuildQueue:
    """Async FIFO build queue with semaphore-based concurrency control."""

    def __init__(self, max_concurrent: int = 1):
        self._queue: deque[str] = deque()
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
        self._process_fn: Optional[Callable[[str], Awaitable[None]]] = None
        self._processed: list[str] = []  # Track processed build IDs (for testing)

    def set_processor(self, fn: Callable[[str], Awaitable[None]]) -> None:
        """Set the async function to process each build.

        Signature: ``async fn(build_id: str) -> None``
        """
        self._process_fn = fn

    async def enqueue(self, build_id: str) -> None:
        """Add a build to the queue. Starts the worker if not already running."""
        self._queue.append(build_id)
        logger.info("Build %s queued (position %d)", build_id, len(self._queue))

        if not self._running:
            self._worker_task = asyncio.create_task(self._worker())

    async def _worker(self) -> None:
        """Process builds one at a time from the queue."""
        self._running = True
        try:
            while self._queue:
                build_id = self._queue.popleft()
                async with self._semaphore:
                    try:
                        if self._process_fn:
                            await self._process_fn(build_id)
                        self._processed.append(build_id)
                    except Exception as e:
                        logger.error("Build %s failed in queue: %s", build_id, e)
                        self._processed.append(build_id)  # Still track it
        finally:
            self._running = False

    @property
    def pending(self) -> int:
        """Number of builds waiting in queue."""
        return len(self._queue)

    @property
    def is_running(self) -> bool:
        """Whether the worker is currently processing."""
        return self._running

    @property
    def processed(self) -> list[str]:
        """List of build IDs that have been processed (for testing)."""
        return list(self._processed)

    async def drain(self) -> None:
        """Wait for all queued builds to finish. Useful for testing."""
        if self._worker_task:
            await self._worker_task
