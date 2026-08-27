from __future__ import annotations

from typing import Any, Mapping

from ui.api.client import ApiClient, get_api_client
from ui.api.types import AgentMessage, AgentTrace


def send_agent_message(
    message: str,
    *,
    context: Mapping[str, Any] | None = None,
    session_id: str | None = None,
    client: ApiClient | None = None,
) -> AgentMessage:
    response = (client or get_api_client()).post(
        "agent/chat",
        body={"session_id": session_id, "message": message, "context": dict(context or {})},
        timeout_seconds=120.0,
    )
    return AgentMessage.from_json(response)


def get_agent_traces(
    session_id: str,
    *,
    limit: int = 250,
    client: ApiClient | None = None,
) -> AgentTrace:
    return AgentTrace.from_json((client or get_api_client()).get(f"agent/sessions/{session_id}/traces", query={"limit": limit}))
