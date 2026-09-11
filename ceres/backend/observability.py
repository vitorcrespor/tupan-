"""Small, dependency-free structured observability for the modular monolith.

Events deliberately contain identifiers, timing, and statuses only. Request
bodies, authorization headers, cookies, provider prompts, SQL, and exception
messages are never added automatically.
"""

from __future__ import annotations

import contextvars
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

from backend.services.serialization import json_safe


request_id_context: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)
job_id_context: contextvars.ContextVar[str | None] = contextvars.ContextVar("job_id", default=None)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": getattr(record, "event", record.getMessage()),
        }
        fields = getattr(record, "event_fields", None)
        if isinstance(fields, dict):
            payload.update(json_safe(fields))
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging(*, level: str | None = None) -> None:
    """Emit JSON logs to stderr without writing any deployment-local files."""
    resolved_level = (level or os.getenv("LOG_LEVEL", "INFO")).upper()
    root = logging.getLogger()
    root.setLevel(resolved_level)
    formatter = JsonFormatter()
    if not root.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(formatter)
        root.addHandler(handler)
        return
    for handler in root.handlers:
        handler.setFormatter(formatter)


def log_event(logger: logging.Logger, event: str, *, level: int = logging.INFO, **fields: Any) -> None:
    """Write one safe structured event enriched from request/job context."""
    fields = {key: value for key, value in fields.items() if value is not None}
    fields.setdefault("request_id", request_id_context.get())
    fields.setdefault("job_id", job_id_context.get())
    logger.log(level, event, extra={"event": event, "event_fields": json_safe(fields)})
