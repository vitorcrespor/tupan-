"""Contract repair tests, separate from retained v1 characterization tests."""
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import unittest
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.api.dependencies import get_analysis_orchestrator, get_tenant_data_repository
from backend.api.routes import analysis, production_data
from backend.api.schemas.analysis import AnalysisTiming, PortfolioPositions, ReportScope, ReportSummaryMetrics, ReportSummaryResponse
from backend.repositories.tenant_data import TenantContext, _record
from backend.services.analysis_orchestrator import AnalysisOrchestrationSettings, AnalysisOrchestrator
from backend.services.estate_comparison import comparison_metrics
from backend.services.errors import NotFoundError, RequestTimeoutError
from backend.tests.test_tenant_repository import _Connection, _Pool, _ControlPlane
from backend.repositories.tenant_data import TenantDataRepository

CONTEXT = TenantContext("org-a", "user-a", "member")

def estate(estate_id=None, **values):
    now = datetime.now(timezone.utc)
    return dict(id=estate_id or str(uuid4()), title="Estate", status="active",
                asking_price=1000, estimated_price=800, created_at=now, updated_at=now,
                attributes={}, **values)


class ComparisonContractTests(unittest.IsolatedAsyncioTestCase):
    def test_signed_difference_units_missing_zero_and_stored_estimate(self):
        a = dict(asking_price=1000, estimated_price=800, rooms=0, market_heat=72)
        b = dict(asking_price=900, estimated_price=1000, rooms=2, market_heat=81)
        rows = {row.key: row for row in comparison_metrics(a, b)}
        self.assertEqual(rows["price"].difference, -100)
        self.assertEqual(rows["price_deviation"].a_value, 25)
        self.assertEqual(rows["price_deviation"].b_value, -10)
        self.assertEqual(rows["price_deviation"].difference, -35)
        self.assertEqual(rows["price_deviation"].unit, "percentage_points")
        self.assertEqual(rows["bedrooms"].difference, 2)
        self.assertEqual(rows["market_heat"].difference, 9)
        self.assertEqual(rows["market_heat"].unit, "score_0_100")
        self.assertIsNone(rows["area_m2"].difference)
        self.assertNotIn("valuation_confidence", rows)

    async def test_pair_reads_authorized_entities_and_propagates_missing(self):
        repository = AsyncMock()
        repository.get_estate.side_effect = [estate(), NotFoundError("Estate not found.")]
        with self.assertRaises(NotFoundError):
            await AnalysisOrchestrator(repository).compare_pair(CONTEXT, "a", "b")
        self.assertEqual([call.args[0] for call in repository.get_estate.call_args_list], [CONTEXT, CONTEXT])

    async def test_pair_cancellation_cancels_both_reads(self):
        repository = AsyncMock()
        cancelled = []
        async def read(context, estate_id):
            try:
                await asyncio.sleep(10)
            finally:
                cancelled.append(estate_id)
        repository.get_estate.side_effect = read
        task = asyncio.create_task(AnalysisOrchestrator(repository).compare_pair(CONTEXT, "a", "b"))
        await asyncio.sleep(.02)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertCountEqual(cancelled, ["a", "b"])

    async def test_pair_exposes_only_normalized_published_heat(self):
        repository = AsyncMock()
        repository.get_estate.side_effect = [estate("a"), estate("b")]
        repository.estate_location_metrics.side_effect = [
            {"metrics": {"market_heat": 74, "units": {"market_heat": "score_0_100"}}},
            {"metrics": {"market_heat": 0.82, "units": {"market_heat": "score_0_1"}}},
        ]
        response = await AnalysisOrchestrator(repository).compare_pair(CONTEXT, "a", "b")
        self.assertEqual(response.a.market_heat, 74)
        self.assertEqual(response.b.market_heat, 82)

    async def test_pair_total_deadline_includes_post_read_enrichment(self):
        repository = AsyncMock()
        repository.get_estate.side_effect = [estate("a"), estate("b")]

        async def slow_artifact(_context):
            await asyncio.sleep(0.05)
            return None

        repository.latest_liquidity_survival_model.side_effect = slow_artifact
        service = AnalysisOrchestrator(
            repository,
            settings=AnalysisOrchestrationSettings(
                total_timeout_seconds=0.01,
                branch_timeout_seconds=0.5,
                avm_timeout_seconds=0.5,
            ),
        )

        with self.assertRaises(RequestTimeoutError):
            await service.compare_pair(CONTEXT, "a", "b", liquidity_horizon_days=90)

    def test_asyncpg_attributes_decode_without_decoding_plain_text(self):
        row = _record({"id": uuid4(), "attributes": '{"source":"listing"}', "title": '{"not":"json-field"}'})
        self.assertEqual(row["attributes"], {"source": "listing"})
        self.assertEqual(row["title"], '{"not":"json-field"}')

    def test_positions_preserve_total_counts_beyond_bounded_rows(self):
        positions = PortfolioPositions(above_count=130, below_count=0, equal_count=2,
                                       missing_count=4, asking_count=136, estimated_count=132, rows=[])
        self.assertEqual(positions.above_count, 130)
        self.assertEqual(positions.rows, [])


class CatalogContractTests(unittest.TestCase):
    def setUp(self):
        self.repository = AsyncMock()
        self.analysis = AsyncMock()
        self.app = FastAPI()
        self.app.include_router(production_data.router, prefix="/v1")
        self.app.dependency_overrides[production_data.tenant_context] = lambda: CONTEXT
        self.app.dependency_overrides[get_tenant_data_repository] = lambda: self.repository
        self.app.dependency_overrides[get_analysis_orchestrator] = lambda: self.analysis
        self.client = TestClient(self.app)

    def test_catalog_typed_whitelist_and_server_deviation(self):
        record = estate()
        record.update(organization_id="org-a", created_by_user_id="internal", attributes='{}',
                      asking_price=Decimal("1000"), estimated_price=Decimal("800"), comparable_count=7,
                      market_heat=72)
        self.repository.estate_analytics_page.return_value = dict(items=[record], page=dict(total=1, offset=0, limit=100))
        response = self.client.get("/v1/analytics/estates", params=dict(query="' OR 1=1 --"))
        self.assertEqual(response.status_code, 200, response.text)
        row = response.json()["items"][0]
        self.assertEqual(row["stored_price_deviation_pct"], 25)
        self.assertEqual(row["comparable_count"], 7)
        self.assertEqual(row["valuation_class"], "INSUFFICIENT_CONFIDENCE")
        self.assertEqual(row["market_heat"], 72)
        self.assertNotIn("organization_id", row)
        self.assertNotIn("created_by_user_id", row)
        self.assertEqual(self.repository.estate_analytics_page.call_args.args[0], CONTEXT)
        self.assertEqual(self.repository.estate_analytics_page.call_args.kwargs["query"], "' OR 1=1 --")

    def test_catalog_rejects_malformed_portfolio_and_excessive_limit(self):
        for params in (dict(portfolio_id="not-a-uuid"), dict(limit=1000)):
            self.assertEqual(self.client.get("/v1/analytics/estates", params=params).status_code, 422)
        self.repository.estate_analytics_page.assert_not_called()

    def test_report_summary_uses_server_tenant_context_and_typed_scope(self):
        self.analysis.report_summary.return_value = ReportSummaryResponse(
            scope=ReportScope(city="São Paulo", area="Pinheiros"),
            summary=ReportSummaryMetrics(
                active_estate_count=2, asking_price_count=2, price_per_m2_count=1,
                days_on_market_count=1, average_asking_price=800_000,
                average_price_per_m2=8_000, average_days_on_market=40,
            ),
            timing=AnalysisTiming(total_ms=1, components=[]),
        )
        response = self.client.get("/v1/analytics/report-summary", params={"city": "São Paulo", "area": "Pinheiros"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["summary"]["active_estate_count"], 2)
        self.analysis.report_summary.assert_awaited_once_with(
            CONTEXT, city="São Paulo", area="Pinheiros", featured_limit=6
        )


class CatalogRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_portfolio_history_is_bound_to_one_tenant_and_returned_chronologically(self):
        class Connection(_Connection):
            async def fetch(self, query, *args):
                self.calls.append(("fetch", query, args))
                return [
                    {"observed_on": "2026-09-15", "active_estate_count": 2, "asking_price_count": 2,
                     "estimated_count": 1, "days_on_market_count": 2, "listing_age_count": 2,
                     "portfolio_value": 1_000_000, "average_days_on_market": 20,
                     "average_listing_age_days": 30, "average_price_gap": 0.1},
                    {"observed_on": "2026-09-14", "active_estate_count": 1, "asking_price_count": 1,
                     "estimated_count": 1, "days_on_market_count": 1, "listing_age_count": 1,
                     "portfolio_value": 500_000, "average_days_on_market": 10,
                     "average_listing_age_days": 20, "average_price_gap": 0.05},
                ]

        connection = Connection()
        repository = TenantDataRepository(_ControlPlane(_Pool(connection)))
        history = await repository.portfolio_metric_history(CONTEXT, "portfolio-a", limit=366)

        self.assertEqual([row["observed_on"] for row in history], ["2026-09-14", "2026-09-15"])
        _, sql, parameters = next(call for call in connection.calls if call[0] == "fetch")
        self.assertIn("organization_id = $1 AND portfolio_id = $2", sql)
        self.assertEqual(parameters, ("org-a", "portfolio-a", 366))

    async def test_portfolio_listing_age_uses_only_dated_active_listings(self):
        class Connection(_Connection):
            async def fetchrow(self, query, *args):
                self.calls.append(("fetchrow", query, args))
                return {
                    "average_asking_price": None, "median_asking_price": None,
                    "average_price_per_m2": None, "median_price_per_m2": None,
                    "average_days_on_market": None, "listing_age_count": 0,
                    "average_listing_age_days": None,
                }

        connection = Connection()
        repository = TenantDataRepository(_ControlPlane(_Pool(connection)))
        result = await repository.portfolio_pricing_statistics(CONTEXT, "portfolio-a")

        self.assertEqual(result["listing_age_count"], 0)
        self.assertIsNone(result["average_listing_age_days"])
        _, sql, parameters = next(call for call in connection.calls if call[0] == "fetchrow")
        self.assertIn("listed_since <= CURRENT_DATE", sql)
        self.assertIn("status = 'active'", sql)
        self.assertEqual(parameters, ("org-a", "portfolio-a"))
    async def test_count_and_rows_share_explicit_tenant_and_bound_search(self):
        class Connection(_Connection):
            async def fetchval(self, query, *args):
                self.calls.append(("fetchval", query, args))
                return 0
            async def fetch(self, query, *args):
                self.calls.append(("fetch", query, args))
                return []
        connection = Connection()
        repository = TenantDataRepository(_ControlPlane(_Pool(connection)))
        for tenant in (CONTEXT, TenantContext("org-b", "user-b", "member")):
            await repository.estate_analytics_page(tenant, limit=100, offset=0, city=None, area=None,
                kind=None, portfolio_id=None, query="' OR 1=1 --")
        reads = [call for call in connection.calls if call[0] in ("fetch", "fetchval")]
        self.assertEqual([call[2][0] for call in reads], ["org-a", "org-a", "org-b", "org-b"])
        for _, sql, parameters in reads:
            self.assertIn("organization_id = $1", sql)
            self.assertNotIn("' OR 1=1 --", sql)
            self.assertEqual(parameters[5], "' OR 1=1 --")
        row_sql = next(sql for kind, sql, _ in reads if kind == "fetch")
        self.assertIn("ST_DWithin(peer.location, catalog.location, 2500)", row_sql)
        self.assertIn("peer.organization_id = catalog.organization_id", row_sql)
        self.assertIn("aggregate.scope = 'platform'", row_sql)
        self.assertIn("aggregate.h3_resolution = $9", row_sql)
        self.assertIn("ST_Covers(aggregate.boundary::geometry, catalog.location::geometry)", row_sql)
        self.assertNotIn("catalog.location IS NULL\n                                 AND aggregate.city", row_sql)
        self.assertEqual(next(parameters for kind, _, parameters in reads if kind == "fetch")[8], 9)

    async def test_estate_location_metrics_requires_coordinates(self):
        connection = _Connection()
        repository = TenantDataRepository(_ControlPlane(_Pool(connection)))

        result = await repository.estate_location_metrics(
            CONTEXT, {"city": "São Paulo", "area": "Pinheiros"}
        )

        self.assertIsNone(result)
        self.assertEqual(connection.calls, [])

    async def test_estate_location_metrics_selects_one_explicit_h3_resolution(self):
        connection = _Connection()
        repository = TenantDataRepository(_ControlPlane(_Pool(connection)))

        await repository.estate_location_metrics(
            CONTEXT,
            {"latitude": -23.56, "longitude": -46.68},
            h3_resolution=8,
        )

        _, sql, parameters = next(call for call in connection.calls if call[0] == "fetchrow")
        self.assertIn("h3_resolution = $3", sql)
        self.assertEqual(parameters, (-46.68, -23.56, 8))

    async def test_report_summary_uses_one_authorized_scope_for_aggregate_and_featured_rows(self):
        class Connection(_Connection):
            async def fetchrow(self, query, *args):
                self.calls.append(("fetchrow", query, args))
                return {
                    "active_estate_count": 0, "asking_price_count": 0,
                    "price_per_m2_count": 0, "days_on_market_count": 0,
                    "average_asking_price": None, "average_price_per_m2": None,
                    "average_days_on_market": None, "featured_estates": "[]",
                }

        connection = Connection()
        repository = TenantDataRepository(_ControlPlane(_Pool(connection)))
        for tenant in (CONTEXT, TenantContext("org-b", "user-b", "member")):
            response = await repository.report_summary(
                tenant, city="São Paulo", area="Pinheiros", featured_limit=6
            )
            self.assertEqual(response["featured_estates"], [])

        reads = [call for call in connection.calls if call[0] == "fetchrow"]
        self.assertEqual([call[2][0] for call in reads], ["org-a", "org-b"])
        for _, sql, parameters in reads:
            self.assertIn("organization_id = $1", sql)
            self.assertIn("status = 'active'", sql)
            self.assertIn("FROM scoped", sql)
            self.assertEqual(parameters[1:4], ("São Paulo", "Pinheiros", 6))


if __name__ == "__main__":
    unittest.main()
