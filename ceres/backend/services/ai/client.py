"""Small backend-only client for structured LLM interpretations."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Mapping
from typing import Any, Protocol

from backend.services.ai.prompts import interpretation_messages
from backend.services.ai.schemas import InterpretationOutput
from backend.services.errors import DomainValidationError, UnavailableError


class InterpretationClient(Protocol):
    async def interpret(self, *, message: str, evidence: dict[str, Any]) -> InterpretationOutput: ...


class OpenAiInterpretationClient:
    """Uses OpenAI only from the FastAPI process; API keys never cross this boundary."""

    def __init__(self, *, api_key: str | None = None, model: str | None = None, timeout_seconds: float = 15.0) -> None:
        self._api_key = api_key if api_key is not None else os.getenv("OPENAI_API_KEY", "").strip()
        self._model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
        self._timeout_seconds = timeout_seconds
        self._client: Any | None = None

    async def interpret(self, *, message: str, evidence: dict[str, Any]) -> InterpretationOutput:
        if not self._api_key:
            raise UnavailableError(
                "AI interpretation is unavailable because the backend provider is not configured.",
                details={"reason": "openai_api_key_missing"},
            )
        try:
            from openai import AsyncOpenAI
        except Exception as exc:  # pragma: no cover - depends on optional runtime install
            raise UnavailableError("The backend OpenAI client dependency is unavailable.") from exc

        if self._client is None:
            self._client = AsyncOpenAI(api_key=self._api_key, timeout=self._timeout_seconds)
        try:
            async with asyncio.timeout(self._timeout_seconds):
                completion = await self._client.chat.completions.create(
                    model=self._model,
                    messages=interpretation_messages(message=message, evidence=evidence),
                    response_format={"type": "json_object"},
                    temperature=0,
                )
            content = completion.choices[0].message.content if completion.choices else None
        except asyncio.CancelledError:
            raise
        except TimeoutError as exc:
            raise UnavailableError("AI interpretation exceeded its provider deadline.", details={"reason": "provider_timeout"}) from exc
        except Exception as exc:
            raise UnavailableError(
                "AI interpretation is temporarily unavailable.",
                details={"reason": "provider_request_failed", "error_type": type(exc).__name__},
            ) from exc
        if not content:
            raise UnavailableError("AI interpretation provider returned an empty response.")
        try:
            return InterpretationOutput.model_validate_json(content)
        except Exception as exc:
            raise DomainValidationError(
                "AI interpretation provider returned an invalid structured response.",
                details={"reason": "invalid_provider_schema"},
            ) from exc
