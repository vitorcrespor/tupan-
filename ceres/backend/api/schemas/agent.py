from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from backend.api.schemas.common import ApiSchema


class AgentContextRequest(ApiSchema):
    metric: str | None = None
    region: str | None = None
    comparison_region: str | None = None
    period: str | None = None
    selected_region: dict[str, Any] | str | None = None
    selected_property: dict[str, Any] | None = None
    market_filters: dict[str, Any] = Field(default_factory=dict)


class AgentMessageRequest(ApiSchema):
    session_id: str | None = Field(default=None, max_length=200)
    message: str = Field(min_length=1, max_length=20_000)
    context: AgentContextRequest = Field(default_factory=AgentContextRequest)


class AgentMessage(ApiSchema):
    role: Literal["agent"] = "agent"
    content: str


class AgentSource(ApiSchema):
    label: str
    detail: str


class AgentAction(ApiSchema):
    label: str
    tool: str


class AgentMessageResponse(ApiSchema):
    session_id: str
    message: AgentMessage
    sources: list[AgentSource] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    actions: list[AgentAction] = Field(default_factory=list)


class AgentTraceEventResponse(ApiSchema):
    event_type: str
    status: str
    summary: str
    created_at: str | None = None
    tool: str | None = None
    duration_ms: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentTraceResponse(ApiSchema):
    session_id: str
    events: list[AgentTraceEventResponse]
