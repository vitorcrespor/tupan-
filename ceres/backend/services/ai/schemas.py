"""Internal, provider-independent schemas for the AI interpretation layer."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AiSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ToolResult(AiSchema):
    name: str
    status: Literal["success", "degraded"]
    data: dict[str, Any] | None = None
    duration_ms: float = Field(ge=0)
    warning: str | None = None


class InterpretationInsight(AiSchema):
    statement: str = Field(min_length=1, max_length=1_200)
    evidence_keys: list[str] = Field(default_factory=list, max_length=12)
    caveat: str | None = Field(default=None, max_length=600)


class InterpretationOutput(AiSchema):
    """The only output shape accepted from an LLM provider."""

    answer: str = Field(min_length=1, max_length=4_000)
    answer_evidence_keys: list[str] = Field(default_factory=list, max_length=12)
    insights: list[InterpretationInsight] = Field(default_factory=list, max_length=8)
    follow_up: str | None = Field(default=None, max_length=600)


class AiChatResult(AiSchema):
    session_id: str
    interpretation: InterpretationOutput
    tools: list[ToolResult] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
