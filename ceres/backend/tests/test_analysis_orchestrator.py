from __future__ import annotations

import asyncio
import time
import unittest
from datetime import datetime, timezone

from backend.api.schemas.analysis import EstateComparisonQuery
from backend.repositories.tenant_data import TenantContext
from backend.services.analysis_orchestrator import AnalysisOrchestrationSettings, AnalysisOrchestrator
from backend.services.avm_runtime import AvmPrediction
from backend.services.errors import UnavailableError


class FakeAvm:
    async def predict(self, estate):
        await asyncio.sleep(0.04)
        return AvmPrediction(estimated_price=900_000.0, inference_ms=4.0)


class FakeRepository:
    def __init__(self, *, fail_market: bool = False) -> None:
        self.contexts: list[TenantContext] = []
        self.fail_market = fail_market

    @staticmethod
    def estate() -> dict:
        now = datetime.now(timezone.utc)
        return {
            "id": "estate-a", "portfolio_id": "portfolio-a", "title": "Estate A", "property_type": "apartment",
            "status": "active", "asking_price": 1_000_000.0, "area_m2": 100.0, "price_per_m2": 10_000.0,
            "rooms": 3, "bathrooms": 2, "parking_spaces": 2, "city": "São Paulo", "area": "Pinheiros",
            "latitude": -23.56, "longitude": -46.68, "attributes": {}, "created_at": now, "updated_at": now,
        }

    async def get_estate(self, context, estate_id):
        self.contexts.append(context)
        return self.estate()

    async def list_estate_comparables(self, context, estate, *, radius_meters, limit):
        self.contexts.append(context)
        await asyncio.sleep(0.04)
        return [{**self.estate(), "id": "estate-b", "distance_meters": 250.0}]

    async def estate_local_statistics(self, context, estate, *, radius_meters):
        self.contexts.append(context)
        await asyncio.sleep(0.04)
        return {"comparable_count": 1, "average_asking_price": 900_000.0, "median_asking_price": 900_000.0,
                "average_price_per_m2": 9_500.0, "median_price_per_m2": 9_500.0, "average_days_on_market": 45.0}

    async def estate_market_context(self, context, estate):
        self.contexts.append(context)
        await asyncio.sleep(0.04)
        if self.fail_market:
            raise UnavailableError("Market provider unavailable.")
        return [{"metric": "price_m2", "value": 9_500.0, "unit": "BRL/m²", "observed_on": "2026-08-01",
                 "source_name": "test", "scope": "tenant"}]

    async def estate_location_metrics(self, context, estate):
        self.contexts.append(context)
        await asyncio.sleep(0.04)
        return {"h3_index": "8928308280fffff", "h3_resolution": 9, "period_start": "2026-07-01",
                "period_end": "2026-08-01", "metrics": {"market_heat": 0.7}, "calculated_at": "2026-08-01T00:00:00Z"}


class AnalysisOrchestratorTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.context = TenantContext(organization_id="org-a", user_id="user-a", role="admin")
        self.settings = AnalysisOrchestrationSettings(total_timeout_seconds=1, branch_timeout_seconds=0.5, avm_timeout_seconds=0.5)

    async def test_estate_analysis_fans_out_independent_branches(self) -> None:
        repository = FakeRepository()
        service = AnalysisOrchestrator(repository, avm=FakeAvm(), settings=self.settings)

        started = time.perf_counter()
        response = await service.analyse_estate(self.context, "estate-a", EstateComparisonQuery())
        elapsed = time.perf_counter() - started

        self.assertLess(elapsed, 0.13, "five 40ms branches should fan out rather than run serially")
        self.assertEqual(response.valuation.estimated_price, 900_000.0)
        self.assertEqual(len(response.comparables), 1)
        self.assertTrue(all(context == self.context for context in repository.contexts))
        self.assertTrue(all(component.state == "success" for component in response.timing.components))

    async def test_optional_branch_failure_keeps_estate_analysis_usable(self) -> None:
        repository = FakeRepository(fail_market=True)
        service = AnalysisOrchestrator(repository, avm=FakeAvm(), settings=self.settings)

        response = await service.analyse_estate(self.context, "estate-a", EstateComparisonQuery())

        self.assertEqual(response.valuation.estimated_price, 900_000.0)
        market = next(component for component in response.timing.components if component.name == "market_context")
        self.assertEqual(market.state, "degraded")
        self.assertEqual(market.code, "dependency_unavailable")
        self.assertEqual(response.market_context, [])

    async def test_cancelled_request_propagates_to_all_branches(self) -> None:
        repository = FakeRepository()
        service = AnalysisOrchestrator(repository, avm=FakeAvm(), settings=self.settings)
        task = asyncio.create_task(service.analyse_estate(self.context, "estate-a", EstateComparisonQuery()))
        await asyncio.sleep(0.01)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
