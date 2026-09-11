"""Bounded fan-out/fan-in orchestration for tenant-authorized analyses.

Domain services and SQL repositories retain their own algorithms. This module
only owns dependency ordering, timeout/cancellation policy, partial-failure
representation, and request-time telemetry.
"""

from __future__ import annotations

import asyncio
import logging
import json
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any, TypeVar

from backend.observability import log_event
from backend.api.schemas.analysis import (
    AnalysisComponentStatus,
    AnalysisTiming,
    ComparableEstate,
    EstateAnalysisResponse,
    EstateComparisonQuery,
    EstateComparisonResponse,
    EstateValuation,
    HeatmapCell,
    HeatmapQuery,
    HeatmapResponse,
    LocalStatistics,
    LocationMetrics,
    MarketContextValue,
    PortfolioMarketExposure,
    PortfolioOverviewResponse,
    PortfolioPricingStatistics,
    PortfolioPropertyDistribution,
    PortfolioRegionConcentration,
    PortfolioValuationSummary,
)
from backend.api.schemas.estate import EstateResponse, PortfolioResponse
from backend.repositories.tenant_data import TenantContext, TenantDataRepository
from backend.services.avm_runtime import AvmPrediction, AvmRuntime
from backend.services.errors import RequestTimeoutError, ServiceError
from backend.services.serialization import json_safe


logger = logging.getLogger(__name__)

ValueT = TypeVar("ValueT")
Operation = Callable[[], Awaitable[ValueT]]


@dataclass(frozen=True)
class AnalysisOrchestrationSettings:
    total_timeout_seconds: float = 12.0
    branch_timeout_seconds: float = 5.0
    avm_timeout_seconds: float = 3.0


@dataclass(frozen=True)
class ComponentOutcome:
    name: str
    value: Any | None
    status: AnalysisComponentStatus


class AnalysisOrchestrator:
    """Coordinates only operations independent after the required entity read."""

    def __init__(
        self,
        repository: TenantDataRepository,
        *,
        avm: AvmRuntime | None = None,
        settings: AnalysisOrchestrationSettings | None = None,
    ) -> None:
        self._repository = repository
        self._avm = avm or AvmRuntime()
        self._settings = settings or AnalysisOrchestrationSettings()

    async def compare_estate(
        self,
        context: TenantContext,
        estate_id: str,
        query: EstateComparisonQuery,
    ) -> EstateComparisonResponse:
        started = time.perf_counter()
        try:
            async with asyncio.timeout(self._settings.total_timeout_seconds):
                estate = await self._repository.get_estate(context, estate_id)
                outcomes = await self._estate_context_fan_out(context, estate, query, include_avm=False)
        except TimeoutError as exc:
            raise RequestTimeoutError("Estate comparison exceeded its request-time deadline.") from exc
        return EstateComparisonResponse(
            estate=EstateResponse.model_validate(estate),
            comparables=self._comparables(outcomes),
            local_statistics=self._local_statistics(outcomes),
            market_context=self._market_context(outcomes),
            location_metrics=self._location_metrics(outcomes),
            timing=self._timing(started, outcomes),
        )

    async def analyse_estate(
        self,
        context: TenantContext,
        estate_id: str,
        query: EstateComparisonQuery,
    ) -> EstateAnalysisResponse:
        started = time.perf_counter()
        try:
            async with asyncio.timeout(self._settings.total_timeout_seconds):
                estate = await self._repository.get_estate(context, estate_id)
                outcomes = await self._estate_context_fan_out(context, estate, query, include_avm=True)
        except TimeoutError as exc:
            raise RequestTimeoutError("Estate analysis exceeded its request-time deadline.") from exc
        valuation = self._valuation(outcomes, estate)
        return EstateAnalysisResponse(
            estate=EstateResponse.model_validate(estate),
            comparables=self._comparables(outcomes),
            local_statistics=self._local_statistics(outcomes),
            market_context=self._market_context(outcomes),
            location_metrics=self._location_metrics(outcomes),
            valuation=valuation,
            timing=self._timing(started, outcomes),
        )

    async def portfolio_overview(
        self,
        context: TenantContext,
        portfolio_id: str,
    ) -> PortfolioOverviewResponse:
        started = time.perf_counter()
        try:
            async with asyncio.timeout(self._settings.total_timeout_seconds):
                portfolio = await self._repository.get_portfolio(context, portfolio_id)
                outcomes = await self._fan_out(
                    {
                        "valuation_summary": lambda: self._repository.portfolio_valuation_summary(context, portfolio_id),
                        "geographic_concentration": lambda: self._repository.portfolio_geographic_concentration(context, portfolio_id),
                        "pricing_statistics": lambda: self._repository.portfolio_pricing_statistics(context, portfolio_id),
                        "property_distribution": lambda: self._repository.portfolio_property_distribution(context, portfolio_id),
                        "market_exposure": lambda: self._repository.portfolio_market_exposure(context, portfolio_id),
                    }
                )
        except TimeoutError as exc:
            raise RequestTimeoutError("Portfolio overview exceeded its request-time deadline.") from exc
        return PortfolioOverviewResponse(
            portfolio=PortfolioResponse.model_validate(portfolio),
            valuation_summary=self._model_or_none(PortfolioValuationSummary, outcomes.get("valuation_summary")),
            geographic_concentration=self._models(PortfolioRegionConcentration, outcomes.get("geographic_concentration")),
            pricing_statistics=self._model_or_none(PortfolioPricingStatistics, outcomes.get("pricing_statistics")),
            property_distribution=self._models(PortfolioPropertyDistribution, outcomes.get("property_distribution")),
            market_exposure=self._models(PortfolioMarketExposure, outcomes.get("market_exposure")),
            timing=self._timing(started, outcomes),
        )

    async def heatmap(self, context: TenantContext, query: HeatmapQuery) -> HeatmapResponse:
        """A fast read over precomputed aggregates, deliberately not a fan-out."""
        started = time.perf_counter()
        try:
            async with asyncio.timeout(self._settings.total_timeout_seconds):
                cells = await self._repository.list_heatmap_aggregates(
                    context,
                    h3_resolution=query.h3_resolution,
                    city=query.city,
                    area=query.area,
                    period_start=query.period_start,
                    period_end=query.period_end,
                )
        except TimeoutError as exc:
            raise RequestTimeoutError("Heatmap retrieval exceeded its request-time deadline.") from exc
        elapsed = (time.perf_counter() - started) * 1_000
        status = AnalysisComponentStatus(name="heatmap_read", state="success", duration_ms=elapsed)
        log_event(logger, "analysis_branch_completed", operation="analysis.heatmap_read", component="heatmap_read", latency_ms=round(elapsed, 2), status="success", cell_count=len(cells))
        return HeatmapResponse(
            cells=[self._heatmap_cell(row) for row in cells],
            timing=AnalysisTiming(total_ms=elapsed, components=[status]),
        )

    async def _estate_context_fan_out(
        self,
        context: TenantContext,
        estate: dict[str, Any],
        query: EstateComparisonQuery,
        *,
        include_avm: bool,
    ) -> dict[str, ComponentOutcome]:
        operations: dict[str, Operation[Any]] = {
            "comparables": lambda: self._repository.list_estate_comparables(
                context, estate, radius_meters=query.radius_meters, limit=query.limit
            ),
            "local_statistics": lambda: self._repository.estate_local_statistics(
                context, estate, radius_meters=query.radius_meters
            ),
            "market_context": lambda: self._repository.estate_market_context(context, estate),
            "location_metrics": lambda: self._repository.estate_location_metrics(context, estate),
        }
        if include_avm:
            operations = {"avm": lambda: self._avm.predict(estate), **operations}
        return await self._fan_out(operations)

    async def _fan_out(self, operations: Mapping[str, Operation[Any]]) -> dict[str, ComponentOutcome]:
        """Run independent branches concurrently and propagate cancellation to all."""
        tasks = {
            name: asyncio.create_task(self._bounded_component(name, operation), name=f"analysis:{name}")
            for name, operation in operations.items()
        }
        try:
            completed = await asyncio.gather(*tasks.values())
        except BaseException:
            for task in tasks.values():
                task.cancel()
            await asyncio.gather(*tasks.values(), return_exceptions=True)
            raise
        for outcome in completed:
            log_event(
                logger,
                "analysis_branch_completed",
                operation=f"analysis.{outcome.name}",
                component=outcome.name,
                latency_ms=round(outcome.status.duration_ms, 2),
                status=outcome.status.state,
                code=outcome.status.code,
            )
        return dict(zip(tasks, completed, strict=True))

    async def _bounded_component(self, name: str, operation: Operation[Any]) -> ComponentOutcome:
        started = time.perf_counter()
        timeout = self._settings.avm_timeout_seconds if name == "avm" else self._settings.branch_timeout_seconds
        try:
            async with asyncio.timeout(timeout):
                value = await operation()
            status = AnalysisComponentStatus(name=name, state="success", duration_ms=(time.perf_counter() - started) * 1_000)
            return ComponentOutcome(name=name, value=value, status=status)
        except asyncio.CancelledError:
            raise
        except TimeoutError:
            return ComponentOutcome(
                name=name,
                value=None,
                status=AnalysisComponentStatus(
                    name=name,
                    state="degraded",
                    duration_ms=(time.perf_counter() - started) * 1_000,
                    code="branch_timeout",
                    message=f"{name.replace('_', ' ').title()} did not finish before its deadline.",
                ),
            )
        except ServiceError as exc:
            return ComponentOutcome(
                name=name,
                value=None,
                status=AnalysisComponentStatus(
                    name=name,
                    state="degraded",
                    duration_ms=(time.perf_counter() - started) * 1_000,
                    code=exc.code,
                    message=str(exc),
                ),
            )
        except Exception as exc:
            return ComponentOutcome(
                name=name,
                value=None,
                status=AnalysisComponentStatus(
                    name=name,
                    state="degraded",
                    duration_ms=(time.perf_counter() - started) * 1_000,
                    code="branch_failed",
                    message=f"{name.replace('_', ' ').title()} is unavailable ({type(exc).__name__}).",
                ),
            )

    @staticmethod
    def _comparables(outcomes: Mapping[str, ComponentOutcome]) -> list[ComparableEstate]:
        outcome = outcomes.get("comparables")
        return [AnalysisOrchestrator._model(ComparableEstate, row) for row in (outcome.value if outcome and outcome.value else [])]

    @staticmethod
    def _local_statistics(outcomes: Mapping[str, ComponentOutcome]) -> LocalStatistics | None:
        outcome = outcomes.get("local_statistics")
        return AnalysisOrchestrator._model(LocalStatistics, outcome.value) if outcome and outcome.value is not None else None

    @staticmethod
    def _market_context(outcomes: Mapping[str, ComponentOutcome]) -> list[MarketContextValue]:
        outcome = outcomes.get("market_context")
        return [AnalysisOrchestrator._model(MarketContextValue, row) for row in (outcome.value if outcome and outcome.value else [])]

    @staticmethod
    def _location_metrics(outcomes: Mapping[str, ComponentOutcome]) -> LocationMetrics | None:
        outcome = outcomes.get("location_metrics")
        if not outcome or outcome.value is None:
            return None
        return AnalysisOrchestrator._model(LocationMetrics, _decode_geojson(outcome.value))

    @staticmethod
    def _valuation(outcomes: Mapping[str, ComponentOutcome], estate: Mapping[str, Any]) -> EstateValuation | None:
        outcome = outcomes.get("avm")
        prediction = outcome.value if outcome else None
        if not isinstance(prediction, AvmPrediction):
            return None
        listed = _as_positive_float(estate.get("asking_price"))
        area_m2 = _as_positive_float(estate.get("area_m2"))
        difference = listed - prediction.estimated_price if listed is not None else None
        return EstateValuation(
            listed_price=listed,
            estimated_price=prediction.estimated_price,
            difference=difference,
            difference_percent=(difference / prediction.estimated_price * 100) if difference is not None else None,
            price_per_m2=(listed / area_m2) if listed is not None and area_m2 else None,
            estimated_price_per_m2=(prediction.estimated_price / area_m2) if area_m2 else None,
            inference_ms=prediction.inference_ms,
        )

    @staticmethod
    def _model_or_none(model: type[ValueT], outcome: ComponentOutcome | None) -> ValueT | None:
        return AnalysisOrchestrator._model(model, outcome.value) if outcome and outcome.value is not None else None

    @staticmethod
    def _models(model: type[ValueT], outcome: ComponentOutcome | None) -> list[ValueT]:
        return [AnalysisOrchestrator._model(model, row) for row in (outcome.value if outcome and outcome.value else [])]

    @staticmethod
    def _model(model: type[ValueT], value: Mapping[str, Any]) -> ValueT:
        """Make a transport model strict without leaking unselected DB fields."""
        payload = {key: item for key, item in dict(value).items() if key in model.model_fields}
        return model.model_validate(payload)

    @staticmethod
    def _heatmap_cell(row: Mapping[str, Any]) -> HeatmapCell:
        return AnalysisOrchestrator._model(HeatmapCell, _decode_geojson(row))

    @staticmethod
    def _timing(started: float, outcomes: Mapping[str, ComponentOutcome]) -> AnalysisTiming:
        return AnalysisTiming(
            total_ms=(time.perf_counter() - started) * 1_000,
            components=[outcome.status for outcome in outcomes.values()],
        )


def _decode_geojson(row: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(json_safe(row))
    for key in ("boundary", "center"):
        value = result.get(key)
        if isinstance(value, str):
            result[key] = json.loads(value)
    return result


def _as_positive_float(value: Any) -> float | None:
    try:
        candidate = float(value)
    except (TypeError, ValueError):
        return None
    return candidate if candidate > 0 else None
