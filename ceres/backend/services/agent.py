from __future__ import annotations

import asyncio
import json
import threading
import uuid
from typing import Any

from backend.api.schemas.agent import (
    AgentAction,
    AgentMessage,
    AgentMessageRequest,
    AgentMessageResponse,
    AgentSource,
    AgentTraceEventResponse,
    AgentTraceResponse,
)
from backend.services.errors import UnavailableError
from backend.services.serialization import json_safe


class AgentService:
    """Transport adapter for the existing compiled LangGraph agent."""

    def __init__(self) -> None:
        self._graph = None
        self._lock = threading.Lock()

    def chat(self, request: AgentMessageRequest) -> AgentMessageResponse:
        session_id = request.session_id or uuid.uuid4().hex
        try:
            from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
        except Exception as exc:
            raise UnavailableError("The agent message dependency is unavailable.") from exc
        messages = []
        context = request.context.model_dump(exclude_none=True, exclude_defaults=True)
        if context:
            messages.append(
                SystemMessage(
                    content=(
                        "The following is application selection context, not a calculated answer. "
                        "Use existing tools for analytical work when appropriate.\n"
                        + json.dumps(json_safe(context), ensure_ascii=False)
                    )
                )
            )
        messages.append(HumanMessage(content=request.message))
        try:
            result = asyncio.run(
                self._compiled_graph().ainvoke(
                    {"messages": messages},
                    config={"configurable": {"thread_id": session_id}},
                )
            )
        except Exception as exc:
            raise UnavailableError(
                "The intelligence agent could not complete this request.",
                details={"reason": "agent_execution_failed", "error_type": type(exc).__name__},
            ) from exc

        result_messages = list(result.get("messages", []))
        final = next(
            (message for message in reversed(result_messages) if isinstance(message, AIMessage) and self._text(message.content)),
            None,
        )
        tool_messages = [message for message in result_messages if isinstance(message, ToolMessage)]
        warnings = [self._text(message.content) for message in tool_messages if self._text(message.content).startswith("Tool error:")]
        tool_names = list(dict.fromkeys((message.name or "agent_tool") for message in tool_messages))
        return AgentMessageResponse(
            session_id=session_id,
            message=AgentMessage(content=self._text(final.content) if final else "The agent completed without a text response."),
            sources=[AgentSource(label=name.replace("_", " ").title(), detail="Existing LangGraph tool") for name in tool_names],
            warnings=warnings,
            actions=[AgentAction(label=f"Used {name.replace('_', ' ').title()}", tool=name) for name in tool_names],
        )

    def traces(self, session_id: str, limit: int) -> AgentTraceResponse:
        try:
            from radar.support.agent_trace import read_agent_traces

            raw_events = read_agent_traces(session_id, limit=limit)
        except Exception as exc:
            raise UnavailableError("The agent trace store is unavailable.") from exc
        events = [
            AgentTraceEventResponse(
                event_type=str(event.get("event_type", "UNKNOWN")),
                status=str(event.get("status", "unknown")),
                summary=str(event.get("summary", "")),
                created_at=event.get("created_at") or event.get("timestamp"),
                tool=event.get("tool"),
                duration_ms=event.get("duration_ms"),
                metadata=json_safe(event.get("metadata") or {}),
            )
            for event in raw_events
        ]
        return AgentTraceResponse(session_id=session_id, events=events)

    def _compiled_graph(self):
        with self._lock:
            if self._graph is None:
                try:
                    from radar.agent.graph import build_agent_graph

                    self._graph = build_agent_graph()
                except Exception as exc:
                    raise UnavailableError("The LangGraph agent could not be initialized.") from exc
            return self._graph

    @staticmethod
    def _text(content: Any) -> str:
        try:
            from radar.support.support_functions import content_to_text

            return content_to_text(content)
        except Exception:
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return "\n".join(str(item.get("text", "")) for item in content if isinstance(item, dict))
            return str(content or "")
