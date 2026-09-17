"""Bounded, tenant-scoped AI tools backed only by existing application services."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import Field

from backend.api.schemas.analysis import EstateComparisonQuery, HeatmapQuery
from backend.api.schemas.common import ApiSchema
from backend.api.schemas.market import MarketIntelligenceRequest
from backend.repositories.tenant_data import TenantContext
from backend.services.ai.schemas import ToolResult
from backend.services.analysis_orchestrator import AnalysisOrchestrator
from backend.services.market import MarketService
from backend.services.errors import ServiceError
from backend.services.serialization import json_safe


class EstateToolInput(ApiSchema):
    estate_id: str = Field(min_length=1, max_length=128)
    radius_meters: int = Field(default=2_500, ge=100, le=25_000)
    limit: int = Field(default=12, ge=1, le=20)


class PortfolioToolInput(ApiSchema):
    portfolio_id: str = Field(min_length=1, max_length=128)


class ReportToolInput(ApiSchema):
    city: str | None = Field(default=None, max_length=160)
    area: str | None = Field(default=None, max_length=160)


class HeatmapToolInput(HeatmapQuery):
    max_cells: int = Field(default=250, ge=1, le=500)


Operation = Callable[[], Awaitable[Any]]


class AuthorizedAiTools:
    """Controlled tool facade for exactly one authenticated request.

    The immutable tenant context comes from the server session.  Each facade is
    request-local, so its memoized fan-out tasks cannot leak data or mutable
    state between tenants.
    """

    def __init__(
        self,
        *,
        context: TenantContext,
        analysis: AnalysisOrchestrator,
        market: MarketService | None = None,
    ) -> None:
        self._context = context
        self._analysis = analysis
        self._market = market
        self._estate_analysis_tasks: dict[tuple[str, int, int], asyncio.Task[Any]] = {}

    async def get_estate(self, raw: EstateToolInput) -> ToolResult:
        async def operation() -> dict[str, Any]:
            result = await self._estate_analysis(raw)
            return result.estate

        return await self._run("get_estate", operation)

    async def find_comparables(self, raw: EstateToolInput) -> ToolResult:
        async def operation() -> dict[str, Any]:
            result = await self._estate_analysis(raw)
            return {
                "estate_id": raw.estate_id,
                "comparables": result.comparables,
                "local_statistics": result.local_statistics,
                "component_status": [item for item in result.timing.components if item.name in {"comparables", "local_statistics"}],
            }

        return await self._run("find_comparables", operation)

    async def estimate_estate_value(self, raw: EstateToolInput) -> ToolResult:
        async def operation() -> dict[str, Any]:
            result = await self._estate_analysis(raw)
            return {
                "estate_id": raw.estate_id,
                "valuation": result.valuation,
                "data_quality": result.data_quality,
                "avm_diagnostics": result.avm_diagnostics,
                "component_status": [item for item in result.timing.components if item.name == "avm"],
            }

        return await self._run("estimate_estate_value", operation)

    async def get_market_metrics(self, raw: EstateToolInput) -> ToolResult:
        async def operation() -> dict[str, Any]:
            result = await self._estate_analysis(raw)
            return {
                "estate_id": raw.estate_id,
                "market_context": result.market_context,
                "component_status": [item for item in result.timing.components if item.name == "market_context"],
            }

        return await self._run("get_market_metrics", operation)

    async def get_location_metrics(self, raw: EstateToolInput) -> ToolResult:
        async def operation() -> dict[str, Any]:
            result = await self._estate_analysis(raw)
            return {
                "estate_id": raw.estate_id,
                "location_metrics": result.location_metrics,
                "component_status": [item for item in result.timing.components if item.name == "location_metrics"],
            }

        return await self._run("get_location_metrics", operation)

    async def get_portfolio_metrics(self, raw: PortfolioToolInput) -> ToolResult:
        return await self._run(
            "get_portfolio_metrics",
            lambda: self._analysis.portfolio_overview(self._context, raw.portfolio_id),
        )

    async def get_report_summary(self, raw: ReportToolInput) -> ToolResult:
        return await self._run(
            "get_report_summary",
            lambda: self._analysis.report_summary(
                self._context, city=raw.city, area=raw.area, featured_limit=6
            ),
        )

    async def get_market_metric(self, raw: MarketIntelligenceRequest) -> ToolResult:
        # Use the same published values as charts; no legacy global-estate read.
        async def operation():
            from backend.services.published_metrics import METRIC_UNITS
            from backend.services.errors import DomainValidationError
            if raw.metric not in METRIC_UNITS or raw.comparison_region != 'No comparison':
                raise DomainValidationError('This metric or comparison has no published market provider.')
            response = await self._analysis.published_market_metrics(self._context, city=raw.city,
                area=None if raw.region == 'All neighborhoods' else raw.region)
            metric = next(item for item in response.metrics if item.metric == raw.metric)
            return {'scope':response.scope, 'city':response.city, 'area':response.area,
                    'aggregation':response.aggregation, 'metric':metric}
        return await self._run(
            'get_market_metric',
            operation,
        )
    async def get_heatmap_metrics(self, raw: HeatmapToolInput) -> ToolResult:
        async def operation() -> dict[str, Any]:
            result = await self._analysis.heatmap(self._context, HeatmapQuery(**raw.model_dump(exclude={"max_cells"})))
            return {"cells": result.cells[: raw.max_cells], "timing": result.timing}

        return await self._run("get_heatmap_metrics", operation)

    async def _estate_analysis(self, raw: EstateToolInput):
        key = (raw.estate_id, raw.radius_meters, raw.limit)
        task = self._estate_analysis_tasks.get(key)
        if task is None:
            query = EstateComparisonQuery(radius_meters=raw.radius_meters, limit=raw.limit)
            task = asyncio.create_task(
                self._analysis.analyse_estate(self._context, raw.estate_id, query),
                name=f"ai:estate-analysis:{raw.estate_id}",
            )
            self._estate_analysis_tasks[key] = task
        return await task

    async def _run(self, name: str, operation: Operation) -> ToolResult:
        started = time.perf_counter()
        try:
            value = await operation()
            return ToolResult(
                name=name,
                status="success",
                data=json_safe(value),
                duration_ms=(time.perf_counter() - started) * 1_000,
            )
        except asyncio.CancelledError:
            raise
        except ServiceError as exc:
            return ToolResult(
                name=name,
                status="degraded",
                duration_ms=(time.perf_counter() - started) * 1_000,
                warning=f"{name} is unavailable ({exc.code}).",
            )
        except Exception as exc:
            return ToolResult(
                name=name,
                status="degraded",
                duration_ms=(time.perf_counter() - started) * 1_000,
                warning=f"{name} is unavailable ({type(exc).__name__}).",
            )
