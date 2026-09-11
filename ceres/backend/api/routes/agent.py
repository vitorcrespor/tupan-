from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_ai_orchestrator, get_current_principal
from backend.api.schemas.agent import (
    AgentAction,
    AgentInsight,
    AgentInterpretation,
    AgentMessage,
    AgentMessageRequest,
    AgentMessageResponse,
    AgentSource,
    AgentTraceEventResponse,
    AgentTraceResponse,
)
from backend.api.schemas.common import ErrorResponse
from backend.repositories.tenant_data import TenantContext
from backend.services.ai.orchestrator import AiOrchestrator


router = APIRouter(prefix="/agent", tags=["agent"])
ERRORS = {
    401: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
    504: {"model": ErrorResponse},
}


def tenant_context(principal: dict = Depends(get_current_principal)) -> TenantContext:
    """Construct immutable tenant context only from the validated backend session."""
    return TenantContext.from_principal(principal)


@router.post("/chat", response_model=AgentMessageResponse, responses=ERRORS)
async def chat(
    request: AgentMessageRequest,
    context: TenantContext = Depends(tenant_context),
    service: AiOrchestrator = Depends(get_ai_orchestrator),
) -> AgentMessageResponse:
    result = await service.chat(request, context)
    used = [tool for tool in result.tools if tool.status == "success"]
    return AgentMessageResponse(
        session_id=result.session_id,
        message=AgentMessage(content=result.interpretation.answer),
        interpretation=AgentInterpretation(
            answer=result.interpretation.answer,
            answer_evidence_keys=result.interpretation.answer_evidence_keys,
            insights=[AgentInsight(**insight.model_dump()) for insight in result.interpretation.insights],
            follow_up=result.interpretation.follow_up,
        ),
        sources=[
            AgentSource(label=tool.name.replace("_", " ").title(), detail="Authorized deterministic Tupan data")
            for tool in used
        ],
        warnings=result.warnings,
        actions=[AgentAction(label=f"Used {tool.name.replace('_', ' ').title()}", tool=tool.name) for tool in used],
    )


@router.get("/sessions/{session_id}/traces", response_model=AgentTraceResponse, responses=ERRORS)
def agent_traces(
    session_id: str,
    limit: int = Query(default=250, ge=1, le=1_000),
    context: TenantContext = Depends(tenant_context),
    service: AiOrchestrator = Depends(get_ai_orchestrator),
) -> AgentTraceResponse:
    events = [AgentTraceEventResponse(**event) for event in service.traces(context, session_id, limit=limit)]
    return AgentTraceResponse(session_id=session_id, events=events)