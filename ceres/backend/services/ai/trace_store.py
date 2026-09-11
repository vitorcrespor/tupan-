"""Small process-local, tenant-scoped diagnostic trace store.

Traces are deliberately non-durable and contain only tool/status metadata, not
provider prompts, secrets, or raw tenant evidence.
"""

from __future__ import annotations

from collections import OrderedDict
from threading import Lock
from typing import Any

from backend.repositories.tenant_data import TenantContext


class AiTraceStore:
    def __init__(self, *, max_sessions: int = 200, max_events: int = 100) -> None:
        self._max_sessions = max_sessions
        self._max_events = max_events
        self._entries: OrderedDict[tuple[str, str], list[dict[str, Any]]] = OrderedDict()
        self._lock = Lock()

    def append(self, context: TenantContext, session_id: str, events: list[dict[str, Any]]) -> None:
        key = (context.organization_id, session_id)
        with self._lock:
            saved = self._entries.setdefault(key, [])
            saved.extend(events)
            del saved[:-self._max_events]
            self._entries.move_to_end(key)
            while len(self._entries) > self._max_sessions:
                self._entries.popitem(last=False)

    def read(self, context: TenantContext, session_id: str, *, limit: int) -> list[dict[str, Any]]:
        key = (context.organization_id, session_id)
        with self._lock:
            return list(self._entries.get(key, ())[-limit:])
