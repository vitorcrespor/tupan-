"""Bounded, process-local limits for sensitive API routes.

This is intentionally a small first deployment control for one API process.
It is not presented as a distributed limiter; deployment documentation calls
for an edge/WAF limit before scaling to multiple API replicas.
"""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque


class SlidingWindowRateLimiter:
    def __init__(self, *, window_seconds: float = 60.0) -> None:
        self._window_seconds = window_seconds
        self._events: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def allow(self, *, scope: str, identifier: str, limit: int) -> tuple[bool, int]:
        """Return whether this request is allowed and a conservative retry delay."""
        if limit <= 0:
            return True, 0
        now = time.monotonic()
        key = (scope, identifier)
        async with self._lock:
            events = self._events[key]
            cutoff = now - self._window_seconds
            while events and events[0] <= cutoff:
                events.popleft()
            if len(events) >= limit:
                retry_after = max(1, int(self._window_seconds - (now - events[0])) + 1)
                return False, retry_after
            events.append(now)
            # Keep idle keys from growing indefinitely in long-running services.
            if len(self._events) > 20_000:
                self._events = defaultdict(deque, {item: values for item, values in self._events.items() if values and values[-1] > cutoff})
            return True, 0
