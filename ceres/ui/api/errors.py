from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class ApiError(Exception):
    """Single frontend-facing error shape for transport, HTTP, and protocol failures."""

    message: str
    code: str = "api_error"
    status_code: int | None = None
    details: dict[str, Any] | None = None
    request_id: str | None = None

    def __str__(self) -> str:
        return self.message
