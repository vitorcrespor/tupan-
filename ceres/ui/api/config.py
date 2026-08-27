from __future__ import annotations

import os
from dataclasses import dataclass


class ApiConfigurationError(RuntimeError):
    """Raised when the frontend API base URL has not been configured."""


@dataclass(frozen=True)
class ApiConfig:
    base_url: str
    timeout_seconds: float = 20.0

    @classmethod
    def from_environment(cls) -> "ApiConfig":
        """Read the desktop variable first, with Vite compatibility for a future web client."""
        base_url = (os.getenv("TUPAN_API_BASE_URL") or os.getenv("VITE_API_BASE_URL") or "").strip()
        if not base_url:
            raise ApiConfigurationError(
                "Set TUPAN_API_BASE_URL (or VITE_API_BASE_URL for a Vite frontend) before using the API client."
            )
        timeout_raw = os.getenv("TUPAN_API_TIMEOUT_SECONDS", "20")
        try:
            timeout_seconds = float(timeout_raw)
        except ValueError as exc:
            raise ApiConfigurationError("TUPAN_API_TIMEOUT_SECONDS must be numeric.") from exc
        if timeout_seconds <= 0:
            raise ApiConfigurationError("TUPAN_API_TIMEOUT_SECONDS must be greater than zero.")
        return cls(base_url=base_url.rstrip("/"), timeout_seconds=timeout_seconds)
