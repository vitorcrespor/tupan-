from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_agent_service
from backend.api.schemas.agent import AgentMessageRequest, AgentMessageResponse, AgentTraceResponse
from backend.api.schemas.common import ErrorResponse
from backend.services.agent import AgentService


router = APIRouter(prefix="/agent", tags=["agent"])
ERRORS = {422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}}


@router.post("/chat", response_model=AgentMessageResponse, responses=ERRORS)
async def chat(request: AgentMessageRequest, service: AgentService = Depends(get_agent_service)) -> AgentMessageResponse:
    return await asyncio.to_thread(service.chat, request)


@router.get("/sessions/{session_id}/traces", response_model=AgentTraceResponse, responses=ERRORS)
def agent_traces(
    session_id: str,
    limit: int = Query(default=250, ge=1, le=1_000),
    service: AgentService = Depends(get_agent_service),
) -> AgentTraceResponse:
    return service.traces(session_id, limit)
