"""Evidence-first AI orchestration with bounded deterministic fan-out/fan-in."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from backend.observability import log_event
from backend.api.schemas.agent import AgentContextRequest, AgentMessageRequest
from backend.api.schemas.market import MarketIntelligenceRequest
from backend.repositories.tenant_data import TenantContext
from backend.services.ai.client import InterpretationClient, OpenAiInterpretationClient
from backend.services.ai.schemas import AiChatResult, InterpretationOutput, ToolResult
from backend.services.ai.tools.analysis_tools import AuthorizedAiTools, EstateToolInput, HeatmapToolInput, PortfolioToolInput
from backend.services.ai.trace_store import AiTraceStore
from backend.services.analysis_orchestrator import AnalysisOrchestrator
from backend.services.market import MarketService
from backend.services.errors import DomainValidationError, RequestTimeoutError
from backend.services.serialization import json_safe


logger = logging.getLogger(__name__)

@dataclass(frozen=True)
class AiOrchestrationSettings:
    request_timeout_seconds: float = 20.0
    max_evidence_bytes: int = 180_000


class AiOrchestrator:
    """Coordinates existing deterministic services, then asks an LLM to interpret.

    It never permits the provider to access a database, execute SQL, create
    arbitrary tool calls, or decide authorization. All tenant resolution and
    tool selection happens before any provider request.
    """

    def __init__(
        self,
        analysis: AnalysisOrchestrator,
        *,
        market: MarketService | None = None,
        client: InterpretationClient | None = None,
        trace_store: AiTraceStore | None = None,
        settings: AiOrchestrationSettings | None = None,
    ) -> None:
        self._analysis = analysis
        self._market = market
        self._client = client or OpenAiInterpretationClient()
        self._traces = trace_store or AiTraceStore()
        self._settings = settings or AiOrchestrationSettings()

    async def chat(self, request: AgentMessageRequest, context: TenantContext) -> AiChatResult:
        session_id = request.session_id or uuid.uuid4().hex
        started = time.perf_counter()
        tools = AuthorizedAiTools(context=context, analysis=self._analysis, market=self._market)
        try:
            async with asyncio.timeout(self._settings.request_timeout_seconds):
                outcomes = await self._gather_evidence(tools, request.context)
                evidence = self._bounded_evidence(outcomes)
                interpretation = await self._client.interpret(message=request.message, evidence=evidence)
                self._validate_evidence_references(interpretation, evidence)
        except asyncio.CancelledError:
            raise
        except TimeoutError as exc:
            raise RequestTimeoutError("AI interpretation exceeded its request-time deadline.") from exc

        warnings = [outcome.warning for outcome in outcomes if outcome.warning]
        elapsed_ms = (time.perf_counter() - started) * 1_000
        self._traces.append(
            context,
            session_id,
            [
                {
                    "event_type": "TOOL",
                    "status": outcome.status,
                    "summary": outcome.name.replace("_", " ").title(),
                    "tool": outcome.name,
                    "duration_ms": round(outcome.duration_ms, 2),
                }
                for outcome in outcomes
            ]
            + [
                {
                    "event_type": "INTERPRETATION",
                    "status": "success",
                    "summary": "Validated AI interpretation",
                    "duration_ms": round(elapsed_ms, 2),
                }
            ],
        )
        log_event(logger, "ai_interpretation_completed", operation="ai.interpretation", latency_ms=round(elapsed_ms, 2), status="success", tool_count=len(outcomes), degraded_tool_count=sum(tool.status != "success" for tool in outcomes))
        return AiChatResult(
            session_id=session_id,
            interpretation=interpretation,
            tools=outcomes,
            warnings=warnings,
        )

    def traces(self, context: TenantContext, session_id: str, *, limit: int) -> list[dict[str, Any]]:
        return self._traces.read(context, session_id, limit=limit)

    async def _gather_evidence(self, tools: AuthorizedAiTools, context: AgentContextRequest) -> list[ToolResult]:
        operations = []
        estate_id = context.resolved_estate_id()
        if estate_id:
            estate = EstateToolInput(
                estate_id=estate_id,
                radius_meters=context.comparison_radius_meters or 2_500,
                limit=context.comparison_limit or 12,
            )
            # These tools share a single request-local estate analysis task;
            # its AVM, comparables, market and location branches fan out once.
            operations.extend(
                [
                    tools.get_estate(estate),
                    tools.find_comparables(estate),
                    tools.estimate_estate_value(estate),
                    tools.get_market_metrics(estate),
                    tools.get_location_metrics(estate),
                ]
            )
        if context.portfolio_id:
            operations.append(tools.get_portfolio_metrics(PortfolioToolInput(portfolio_id=context.portfolio_id)))
        market_metric = context.resolved_market_metric()
        if market_metric and self._market is not None:
            operations.append(
                tools.get_market_metric(
                    MarketIntelligenceRequest(
                        metric=market_metric,
                        region=context.region or 'All neighborhoods',
                        period=context.resolved_market_period(),
                    )
                )
            )
        heatmap = context.resolved_heatmap()
        if heatmap:
            try:
                heatmap_input = HeatmapToolInput(**heatmap)
            except ValidationError as exc:
                raise DomainValidationError(
                    "The selected heatmap filters are invalid.",
                    details={"reason": "invalid_heatmap_tool_input"},
                ) from exc
            operations.append(tools.get_heatmap_metrics(heatmap_input))
        if not operations:
            return []
        return list(await asyncio.gather(*operations))

    def _bounded_evidence(self, outcomes: list[ToolResult]) -> dict[str, Any]:
        evidence = {outcome.name: outcome.data for outcome in outcomes if outcome.status == "success" and outcome.data is not None}
        safe = json_safe(evidence)
        encoded = __import__("json").dumps(safe, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        if len(encoded) > self._settings.max_evidence_bytes:
            raise DomainValidationError(
                "Authorized analysis evidence exceeds the AI request limit.",
                details={"reason": "evidence_too_large", "max_bytes": self._settings.max_evidence_bytes},
            )
        return safe

    @staticmethod
    def _validate_evidence_references(interpretation: InterpretationOutput, evidence: dict[str, Any]) -> None:
        allowed = set(evidence)
        cited = set(interpretation.answer_evidence_keys)
        cited.update(key for insight in interpretation.insights for key in insight.evidence_keys)
        unknown = cited - allowed
        if allowed and (not interpretation.answer_evidence_keys or any(not insight.evidence_keys for insight in interpretation.insights)):
            raise DomainValidationError(
                "AI interpretation omitted evidence references for an evidence-backed statement.",
                details={"reason": "missing_evidence_reference"},
            )
        if unknown:
            raise DomainValidationError(
                "AI interpretation referenced data that was not supplied by an authorized tool.",
                details={"reason": "unknown_evidence_reference", "keys": sorted(unknown)},
            )
