"""Retained v1 characterization tests for the bidirectional reconciliation.

These test observable provider/transport behavior, not database population or
model accuracy. All records and predictions are isolated fixtures; no real API,
database, OpenAI call, model artifact or training operation is used.
"""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from backend.api.routes.agent import chat
from backend.api.schemas.agent import AgentMessageRequest
from backend.api.schemas.analysis import EstateComparisonQuery, HeatmapQuery
from backend.repositories.tenant_data import TenantContext
from backend.services.ai.schemas import AiChatResult, InterpretationInsight, InterpretationOutput, ToolResult
from backend.services.analysis_orchestrator import AnalysisOrchestrator
from backend.services.avm_runtime import AvmPrediction
from backend.services.errors import NotFoundError, UnavailableError


FIXED_TIME = datetime(2026, 1, 15, tzinfo=timezone.utc)
TENANT = TenantContext(organization_id="test-org", user_id="test-user", role="admin")


class ContractRepository:
    def __init__(self, *, asking_price=80_000.0, area_m2=100.0):
        self.record = {
            "id": "test-estate", "title": "Contract fixture", "status": "active",
            "asking_price": asking_price, "area_m2": area_m2, "price_per_m2": 999.0,
            "rooms": 0, "bathrooms": None, "parking_spaces": 0,
            "created_at": FIXED_TIME, "updated_at": FIXED_TIME,
        }
        self.contexts = []

    async def get_estate(self, context, estate_id):
        self.contexts.append(context)
        if estate_id != self.record["id"]:
            raise NotFoundError("Estate not found.")
        return self.record.copy()

    async def list_estate_comparables(self, context, estate, *, radius_meters, limit):
        self.contexts.append(context)
        return [{"id": "test-peer", "asking_price": 90_000.0, "distance_meters": 250.0}][:limit]

    async def estate_local_statistics(self, context, estate, *, radius_meters):
        self.contexts.append(context)
        return {"comparable_count": 20, "median_price_per_m2": 900.0}

    async def estate_market_context(self, context, estate):
        self.contexts.append(context)
        return [{"metric": "price_m2", "value": 900.0, "unit": "BRL/m²",
                 "observed_on": "2026-01-01", "source_name": "fixture", "scope": "platform"}]

    async def estate_location_metrics(self, context, estate):
        self.contexts.append(context)
        return None

    async def list_heatmap_aggregates(self, context, **filters):
        self.contexts.append(context)
        return [{
            "h3_index": "8928308280fffff", "h3_resolution": 9,
            "period_start": "2026-01-01", "period_end": "2026-01-01",
            "boundary": '{"type":"Polygon","coordinates":[[[-46.7,-23.6],[-46.6,-23.6],[-46.7,-23.5],[-46.7,-23.6]]]}',
            "center": '{"type":"Point","coordinates":[-46.7,-23.6]}',
            "metrics": {"inventory": 2, "average_asking_price": 90_000.0,
                        "average_price_m2": None, "average_dom_days": 0.0},
            "input_version": "fixture-v1", "calculated_at": "2026-01-15T00:00:00Z", "scope": "platform",
        }]


class ContractAvm:
    def __init__(self, *, unavailable=False):
        self.calls = 0
        self.unavailable = unavailable

    async def predict(self, estate):
        self.calls += 1
        if self.unavailable:
            raise UnavailableError("Fixture artifact unavailable.")
        return AvmPrediction(estimated_price=100_000.0, inference_ms=2.0)


class InformationContractCharacterizationTests(unittest.IsolatedAsyncioTestCase):
    async def analyse(self, **record_options):
        repository = ContractRepository(**record_options)
        response = await AnalysisOrchestrator(repository, avm=ContractAvm()).analyse_estate(
            TENANT, "test-estate", EstateComparisonQuery(limit=1),
        )
        self.assertTrue(all(context == TENANT for context in repository.contexts))
        return response.model_dump(mode="json")

    async def test_v1_signed_deviation_is_percent_not_fraction_and_m2_is_calculated_once(self):
        response = await self.analyse()
        valuation = response["valuation"]
        self.assertEqual(valuation["estimated_price"], 100_000.0)
        self.assertEqual(valuation["difference"], -20_000.0)
        self.assertEqual(valuation["difference_percent"], -20.0)
        self.assertEqual(valuation["price_per_m2"], 800.0)
        self.assertEqual(valuation["estimated_price_per_m2"], 1_000.0)
        # Existing estate snapshot can carry an independently stored m² value.
        self.assertEqual(response["estate"]["price_per_m2"], 999.0)

    async def test_missing_price_is_not_zero_and_model_does_not_invent_confidence(self):
        valuation = (await self.analyse(asking_price=None, area_m2=None))["valuation"]
        self.assertEqual(valuation["estimated_price"], 100_000.0)
        for field in ("listed_price", "difference", "difference_percent", "price_per_m2", "estimated_price_per_m2"):
            self.assertIsNone(valuation[field])
        for absent in ("confidence", "prediction_interval", "lower_bound", "upper_bound", "model_version"):
            self.assertNotIn(absent, valuation)

    async def test_v1_zero_asking_price_is_preserved_as_fact_but_not_usable_valuation_input(self):
        # A legacy contract quirk: facts accept zero; the valuation requires >0.
        response = await self.analyse(asking_price=0)
        self.assertEqual(response["estate"]["asking_price"], 0)
        self.assertIsNone(response["valuation"]["listed_price"])
        self.assertIsNone(response["valuation"]["difference_percent"])
        self.assertEqual(response["estate"]["parking_spaces"], 0)
        self.assertIsNone(response["estate"]["bathrooms"])

    async def test_comparable_support_and_cosine_status_are_explicit(self):
        response = await self.analyse()
        self.assertEqual(len(response["comparables"]), 1)
        self.assertEqual(response["local_statistics"]["comparable_count"], 20)
        self.assertEqual(response["comparables"][0]["distance_meters"], 250.0)
        self.assertIsNone(response["comparables"][0]["similarity_score"])
        self.assertEqual(response["comparables"][0]["similarity_status"], "target_incomplete_features")
        self.assertEqual(response["comparable_metadata"]["eligible_count"], 20)
        self.assertEqual(response["comparable_metadata"]["scored_count"], 0)
        self.assertEqual(response["market_context"][0]["unit"], "BRL/m²")
        self.assertEqual(response["market_context"][0]["observed_on"], "2026-01-01")

    async def test_avm_failure_keeps_successful_comparables_and_market_context(self):
        response = await AnalysisOrchestrator(ContractRepository(), avm=ContractAvm(unavailable=True)).analyse_estate(
            TENANT, "test-estate", EstateComparisonQuery(),
        )
        self.assertIsNone(response.valuation)
        self.assertEqual(response.local_statistics.comparable_count, 20)
        self.assertEqual(len(response.comparables), 1)
        self.assertEqual(len(response.market_context), 1)
        status = next(component for component in response.timing.components if component.name == "avm")
        self.assertEqual(status.state, "degraded")
        self.assertEqual(status.code, "dependency_unavailable")

    async def test_required_estate_access_failure_prevents_model_execution(self):
        avm = ContractAvm()
        with self.assertRaises(NotFoundError):
            await AnalysisOrchestrator(ContractRepository(), avm=avm).analyse_estate(
                TENANT, "not-authorized-or-missing", EstateComparisonQuery(),
            )
        self.assertEqual(avm.calls, 0)

    async def test_heatmap_preserves_geojson_null_zero_and_publication_metadata(self):
        repository = ContractRepository()
        response = await AnalysisOrchestrator(repository, avm=ContractAvm()).heatmap(TENANT, HeatmapQuery())
        cell = response.model_dump(mode="json")["cells"][0]
        self.assertEqual(cell["center"], {"type": "Point", "coordinates": [-46.7, -23.6]})
        self.assertEqual(cell["boundary"]["type"], "Polygon")
        self.assertEqual(cell["metrics"]["inventory"], 2)
        self.assertEqual(cell["metrics"]["average_dom_days"], 0.0)
        self.assertIsNone(cell["metrics"]["average_price_m2"])
        self.assertNotIn("market_heat", cell["metrics"])
        self.assertEqual(cell["scope"], "platform")
        self.assertEqual(cell["calculated_at"], "2026-01-15T00:00:00Z")
        self.assertEqual(repository.contexts, [TENANT])

    async def test_agent_transport_preserves_evidence_but_does_not_dump_tool_payloads(self):
        class FixtureAi:
            async def chat(self, request, context):
                return AiChatResult(
                    session_id="fixture-session",
                    interpretation=InterpretationOutput(
                        answer="Interpretation only.", answer_evidence_keys=["get_estate"],
                        insights=[InterpretationInsight(statement="Supported fact.", evidence_keys=["get_estate"], caveat="Limited support.")],
                    ),
                    tools=[ToolResult(name="get_estate", status="success", data={"id": "test-estate"}, duration_ms=1)],
                    warnings=["Location unavailable."],
                )

        response = (await chat(AgentMessageRequest(message="Explain"), TENANT, FixtureAi())).model_dump(mode="json")
        self.assertEqual(response["message"]["content"], response["interpretation"]["answer"])
        self.assertEqual(response["interpretation"]["insights"][0]["caveat"], "Limited support.")
        self.assertEqual(response["sources"][0]["label"], "Get Estate")
        self.assertEqual(response["warnings"], ["Location unavailable."])
        self.assertEqual(response["actions"], [{"label": "Used Get Estate", "tool": "get_estate"}])
        self.assertEqual(response["session_id"], "fixture-session")
        self.assertNotIn("tools", response)


if __name__ == "__main__":
    unittest.main()
