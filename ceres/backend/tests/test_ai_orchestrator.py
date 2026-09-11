from __future__ import annotations

import asyncio
import time
import unittest
from datetime import datetime, timezone

from backend.api.schemas.agent import AgentContextRequest, AgentMessageRequest
from backend.api.schemas.analysis import AnalysisComponentStatus, AnalysisTiming, EstateAnalysisResponse, EstateValuation, LocalStatistics
from backend.api.schemas.estate import EstateResponse
from backend.repositories.tenant_data import TenantContext
from backend.services.ai.orchestrator import AiOrchestrationSettings, AiOrchestrator
from backend.services.ai.schemas import InterpretationInsight, InterpretationOutput
from backend.services.errors import DomainValidationError


class FakeAnalysis:
    def __init__(self) -> None:
        self.contexts: list[TenantContext] = []
        self.analysis_calls = 0

    async def analyse_estate(self, context, estate_id, query) -> EstateAnalysisResponse:
        self.contexts.append(context)
        self.analysis_calls += 1
        await asyncio.sleep(0.04)
        now = datetime.now(timezone.utc)
        return EstateAnalysisResponse(
            estate=EstateResponse(id=estate_id, title="Verified estate", asking_price=1_000_000, area_m2=100, created_at=now, updated_at=now),
            comparables=[],
            local_statistics=LocalStatistics(comparable_count=2, average_asking_price=900_000),
            market_context=[],
            location_metrics=None,
            valuation=EstateValuation(estimated_price=900_000, listed_price=1_000_000, difference=100_000, difference_percent=11.11, inference_ms=2),
            timing=AnalysisTiming(total_ms=40, components=[
                AnalysisComponentStatus(name="avm", state="success", duration_ms=2),
                AnalysisComponentStatus(name="comparables", state="success", duration_ms=2),
                AnalysisComponentStatus(name="local_statistics", state="success", duration_ms=2),
                AnalysisComponentStatus(name="market_context", state="success", duration_ms=2),
                AnalysisComponentStatus(name="location_metrics", state="success", duration_ms=2),
            ]),
        )


class FakeClient:
    def __init__(self, *, unknown_reference: bool = False) -> None:
        self.evidence: dict = {}
        self.unknown_reference = unknown_reference

    async def interpret(self, *, message: str, evidence: dict) -> InterpretationOutput:
        self.evidence = evidence
        return InterpretationOutput(
            answer="A interpretação usa somente evidência autorizada.",
            answer_evidence_keys=["estimate_estate_value"],
            insights=[InterpretationInsight(
                statement="A avaliação foi disponibilizada pelo AVM.",
                evidence_keys=["not-authorized" if self.unknown_reference else "estimate_estate_value"],
            )],
        )


class AiOrchestratorTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tenant_a = TenantContext(organization_id="tenant-a", user_id="user-a", role="admin")
        self.tenant_b = TenantContext(organization_id="tenant-b", user_id="user-b", role="admin")

    async def test_estate_tools_share_one_deterministic_analysis_and_preserve_tenant(self) -> None:
        analysis, client = FakeAnalysis(), FakeClient()
        service = AiOrchestrator(
            analysis,
            client=client,
            settings=AiOrchestrationSettings(request_timeout_seconds=1, max_evidence_bytes=10_000),
        )

        started = time.perf_counter()
        result = await service.chat(
            AgentMessageRequest(message="Explique este imóvel", context=AgentContextRequest(estate_id="estate-a")),
            self.tenant_a,
        )
        elapsed = time.perf_counter() - started

        self.assertLess(elapsed, 0.12, "independent estate tool views should fan out")
        self.assertEqual(analysis.analysis_calls, 1, "tool views must share one estate analysis")
        self.assertTrue(all(context == self.tenant_a for context in analysis.contexts))
        self.assertEqual({tool.name for tool in result.tools}, {
            "get_estate", "find_comparables", "estimate_estate_value", "get_market_metrics", "get_location_metrics",
        })
        self.assertIn("estimate_estate_value", client.evidence)
        self.assertEqual(result.interpretation.answer, "A interpretação usa somente evidência autorizada.")
        self.assertTrue(service.traces(self.tenant_a, result.session_id, limit=20))
        self.assertEqual(service.traces(self.tenant_b, result.session_id, limit=20), [])

    async def test_provider_cannot_reference_data_outside_authorized_evidence(self) -> None:
        service = AiOrchestrator(
            FakeAnalysis(),
            client=FakeClient(unknown_reference=True),
            settings=AiOrchestrationSettings(request_timeout_seconds=1, max_evidence_bytes=10_000),
        )
        with self.assertRaises(DomainValidationError):
            await service.chat(
                AgentMessageRequest(message="Explique", context=AgentContextRequest(estate_id="estate-a")),
                self.tenant_a,
            )

    async def test_invalid_heatmap_hint_is_a_controlled_validation_error(self) -> None:
        service = AiOrchestrator(
            FakeAnalysis(),
            client=FakeClient(),
            settings=AiOrchestrationSettings(request_timeout_seconds=1, max_evidence_bytes=10_000),
        )
        with self.assertRaises(DomainValidationError):
            await service.chat(
                AgentMessageRequest(message="Mapa", context=AgentContextRequest(market_filters={"h3_resolution": "invalid"})),
                self.tenant_a,
            )
    def test_context_only_forwards_whitelisted_heatmap_filters(self) -> None:
        context = AgentContextRequest(region="São Paulo", market_filters={"h3_resolution": 9, "max_cells": 10, "sql": "DROP"})
        self.assertEqual(context.resolved_heatmap(), {"h3_resolution": 9, "max_cells": 10, "city": "São Paulo"})


if __name__ == "__main__":
    unittest.main()
