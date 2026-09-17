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
from datetime import date
from typing import Any, TypeVar

from backend.observability import log_event
from backend.api.schemas.analysis import (
    AnalysisComponentStatus,
    AnalysisTiming,
    ComparableEstate,
    ComparableMetadata,
    EstateAnalysisResponse,
    EstateComparisonQuery,
    EstateComparisonResponse,
    EstatePairResponse,
    EstateValuation,
    HeatmapCell,
    HeatmapQuery,
    HeatmapResponse,
    LocalStatistics,
    LocationMetrics,
    MarketContextValue,
    PortfolioMarketExposure,
    PortfolioLiquiditySummary,
    PortfolioMetricSnapshot,
    PortfolioOverviewResponse,
    PortfolioPositions,
    PortfolioPricingStatistics,
    PortfolioPropertyDistribution,
    PortfolioRegionConcentration,
    PortfolioValuationSummary,
    ReportFeaturedEstate,
    ReportMarketMetric,
    ReportScope,
    ReportSummaryMetrics,
    ReportSummaryResponse,
)
from backend.api.schemas.estate import EstateResponse, PortfolioResponse
from backend.api.schemas.published_metrics import PublishedMarketResponse
from backend.repositories.tenant_data import TenantContext, TenantDataRepository
from backend.services.published_metrics import (
    published_cell_indicators,
    published_cell_liquidity_details,
    published_market_response,
)
from backend.services.market_snapshot import market_snapshot_observations
from backend.services.estate_quality import estate_data_quality
from backend.api.schemas.analysis import AvmDiagnostics
from backend.services.avm_runtime import AvmPrediction, AvmRuntime
from backend.services.errors import RequestTimeoutError, ServiceError
from backend.services.serialization import json_safe
from backend.services.valuation_metrics import valuation_metrics
from backend.services.valuation_classification import classify_asking_price
from backend.services.estate_comparison import comparison_metrics
from backend.services.comparable_similarity import (
    CANDIDATE_LIMIT,
    FEATURE_VERSION as COMPARABLE_FEATURE_VERSION,
    METHOD as COMPARABLE_METHOD,
    cosine_similarity,
    rank_comparables,
)
from backend.services.liquidity_survival import score_listing_liquidity, summarize_portfolio_liquidity


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
                comparables, comparable_metadata = self._comparables(outcomes, estate, query.limit)
                location_metrics = self._location_metrics(outcomes)
                enriched_estate = await self._estate_with_liquidity(
                    context, estate, query.liquidity_horizon_days
                )
                self._attach_market_heat(enriched_estate, location_metrics)
                return EstateComparisonResponse(
                    estate=enriched_estate,
                    comparables=comparables,
                    comparable_metadata=comparable_metadata,
                    local_statistics=self._local_statistics(outcomes),
                    market_context=self._market_context(outcomes),
                    location_metrics=location_metrics,
                    timing=self._timing(started, outcomes),
                )
        except TimeoutError as exc:
            raise RequestTimeoutError("Estate comparison exceeded its request-time deadline.") from exc

    async def compare_pair(
        self,
        context: TenantContext,
        a_id: str,
        b_id: str,
        *,
        liquidity_horizon_days: int | None = None,
    ) -> EstatePairResponse:
        # Both entity reads are mandatory: never turn a forbidden/missing ID into partial data.
        tasks = [asyncio.create_task(self._repository.get_estate(context, estate_id)) for estate_id in (a_id, b_id)]
        try:
            async with asyncio.timeout(self._settings.total_timeout_seconds):
                a, b = await asyncio.gather(*tasks)
                artifact = await self._liquidity_artifact(context) if liquidity_horizon_days is not None else None
                a = self._with_liquidity_artifact(a, artifact, liquidity_horizon_days)
                b = self._with_liquidity_artifact(b, artifact, liquidity_horizon_days)
                a, b = await asyncio.gather(
                    self._estate_with_published_heat(context, a),
                    self._estate_with_published_heat(context, b),
                )
                similarity = cosine_similarity(a, b)
                return EstatePairResponse(
                    a=self._model(EstateResponse, a), b=self._model(EstateResponse, b),
                    metrics=comparison_metrics(a, b),
                    similarity_score=similarity,
                    similarity_status="available" if similarity is not None else "incomplete_features",
                    similarity_method=COMPARABLE_METHOD,
                    similarity_feature_version=COMPARABLE_FEATURE_VERSION,
                )
        except TimeoutError as exc:
            raise RequestTimeoutError('Estate pair comparison exceeded its deadline.') from exc
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

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
                valuation = self._valuation(outcomes, estate)
                comparables, comparable_metadata = self._comparables(outcomes, estate, query.limit)
                location_metrics = self._location_metrics(outcomes)
                enriched_estate = await self._estate_with_liquidity(
                    context, estate, query.liquidity_horizon_days
                )
                self._attach_market_heat(enriched_estate, location_metrics)
                return EstateAnalysisResponse(
                    estate=enriched_estate,
                    comparables=comparables,
                    comparable_metadata=comparable_metadata,
                    local_statistics=self._local_statistics(outcomes),
                    market_context=self._market_context(outcomes),
                    location_metrics=location_metrics,
                    valuation=valuation,
                    data_quality=estate_data_quality(estate),
                    avm_diagnostics=(AvmDiagnostics.model_validate(dict(outcomes['avm'].value.diagnostics))
                        if valuation is not None and outcomes['avm'].value.diagnostics else None),
                    timing=self._timing(started, outcomes),
                )
        except TimeoutError as exc:
            raise RequestTimeoutError("Estate analysis exceeded its request-time deadline.") from exc

    async def portfolio_overview(
        self,
        context: TenantContext,
        portfolio_id: str,
        *,
        liquidity_horizon_days: int | None = None,
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
                        "liquidity_summary": lambda: self._portfolio_liquidity(
                            context, portfolio_id, liquidity_horizon_days
                        ),
                        "history": lambda: self._repository.portfolio_metric_history(context, portfolio_id),
                        "property_distribution": lambda: self._repository.portfolio_property_distribution(context, portfolio_id),
                        "market_exposure": lambda: self._repository.portfolio_market_exposure(context, portfolio_id),
                        "positions": lambda: self._repository.portfolio_positions(context, portfolio_id),
                    }
                )
        except TimeoutError as exc:
            raise RequestTimeoutError("Portfolio overview exceeded its request-time deadline.") from exc
        return PortfolioOverviewResponse(
            portfolio=PortfolioResponse.model_validate(portfolio),
            valuation_summary=self._model_or_none(PortfolioValuationSummary, outcomes.get("valuation_summary")),
            geographic_concentration=self._models(PortfolioRegionConcentration, outcomes.get("geographic_concentration")),
            pricing_statistics=self._model_or_none(PortfolioPricingStatistics, outcomes.get("pricing_statistics")),
            liquidity_summary=self._model_or_none(PortfolioLiquiditySummary, outcomes.get("liquidity_summary")),
            history=self._models(PortfolioMetricSnapshot, outcomes.get("history")),
            property_distribution=self._models(PortfolioPropertyDistribution, outcomes.get("property_distribution")),
            market_exposure=self._models(PortfolioMarketExposure, outcomes.get("market_exposure")),
            timing=self._timing(started, outcomes),
            positions=self._model_or_none(PortfolioPositions, outcomes.get("positions")),
            top_region_share=(
                sum(row["share"] for row in outcomes["geographic_concentration"].value[:2])
                if outcomes["geographic_concentration"].value else None
            ),
        )

    async def _portfolio_liquidity(
        self,
        context: TenantContext,
        portfolio_id: str,
        horizon_days: int | None,
    ) -> dict[str, Any]:
        if horizon_days is None:
            return summarize_portfolio_liquidity((), horizon_days=None)
        rows = await self._repository.portfolio_liquidity_sources(context, portfolio_id)
        return await asyncio.to_thread(
            summarize_portfolio_liquidity,
            rows,
            horizon_days=horizon_days,
        )

    async def published_market_metrics(
        self,
        context: TenantContext,
        *,
        city=None,
        area=None,
        h3_index=None,
        liquidity_horizon_days: int | None = None,
    ):
        try:
            async with asyncio.timeout(self._settings.total_timeout_seconds):
                rows = await self._repository.published_market_observations(
                    context,
                    city=city,
                    area=area,
                    h3_index=h3_index,
                    liquidity_horizon_days=liquidity_horizon_days,
                )
                if rows:
                    return published_market_response(
                        rows,
                        city=city,
                        area=area,
                        h3_index=h3_index,
                        liquidity_horizon_days=liquidity_horizon_days,
                    )
                cells = await self._repository.published_heatmap_snapshot(
                    context, city=city, area=area, h3_index=h3_index,
                )
        except TimeoutError as exc:
            raise RequestTimeoutError('Published market retrieval exceeded its deadline.') from exc
        # asyncpg deployments may return JSONB columns as serialized strings.
        # Normalize the stored aggregate before projecting it into the common
        # published-metrics contract.
        cells = [_decode_geojson(cell) for cell in cells]
        if not cells:
            return published_market_response([], city=city, area=area, h3_index=h3_index,
                                             liquidity_horizon_days=liquidity_horizon_days)
        observed_on = _latest_snapshot_date(cells)
        if observed_on is None:
            return published_market_response([], city=city, area=area, h3_index=h3_index,
                                             liquidity_horizon_days=liquidity_horizon_days)
        input_versions = {str(cell.get("input_version")) for cell in cells if cell.get("input_version")}
        projected = market_snapshot_observations(
            cells,
            observed_on=observed_on,
            source_reference=f"heatmap:{next(iter(input_versions)) if len(input_versions) == 1 else 'mixed'}",
        )
        scoped = [
            row for row in projected
            if row["city"] == city and row["area"] == area and row["h3_index"] == h3_index
            and (
                row["metric"] != "liquidity"
                or (row.get("dimensions") or {}).get("liquidity_horizon_days") == liquidity_horizon_days
            )
        ]
        return published_market_response(
            scoped,
            city=city,
            area=area,
            h3_index=h3_index,
            liquidity_horizon_days=liquidity_horizon_days,
        )

    async def report_summary(
        self,
        context: TenantContext,
        *,
        city: str | None,
        area: str | None,
        featured_limit: int,
    ) -> ReportSummaryResponse:
        """Fan out independent tenant and published-market reads for ReportBuilder."""
        started = time.perf_counter()
        try:
            async with asyncio.timeout(self._settings.total_timeout_seconds):
                outcomes = await self._fan_out({
                    "report_tenant_summary": lambda: self._repository.report_summary(
                        context, city=city, area=area, featured_limit=featured_limit
                    ),
                    "report_market_metrics": lambda: self.published_market_metrics(context, city=city, area=area),
                })
        except TimeoutError as exc:
            raise RequestTimeoutError("Report summary exceeded its request-time deadline.") from exc

        tenant = outcomes.get("report_tenant_summary")
        tenant_value = tenant.value if tenant and tenant.value is not None else {}
        published = outcomes.get("report_market_metrics")
        market_metrics: list[ReportMarketMetric] = []
        if published and isinstance(published.value, PublishedMarketResponse):
            normalized = published.value
            for metric in normalized.metrics:
                if metric.metric == "sales_velocity":
                    market_metrics.append(self._model(ReportMarketMetric, metric.model_dump()))

        return ReportSummaryResponse(
            scope=ReportScope(city=city, area=area),
            summary=self._model_or_none(ReportSummaryMetrics, tenant),
            featured_estates=[self._model(ReportFeaturedEstate, item) for item in tenant_value.get("featured_estates", [])],
            market_metrics=market_metrics,
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
            cells=[self._heatmap_cell(row, query.liquidity_horizon_days) for row in cells],
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
                context, estate, radius_meters=query.radius_meters, limit=CANDIDATE_LIMIT
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
    def _comparables(
        outcomes: Mapping[str, ComponentOutcome],
        estate: Mapping[str, Any],
        limit: int,
    ) -> tuple[list[ComparableEstate], ComparableMetadata | None]:
        outcome = outcomes.get("comparables")
        if not outcome or outcome.value is None:
            return [], None
        ranked, metadata = rank_comparables(estate, outcome.value, limit=limit)
        local = outcomes.get("local_statistics")
        local_value = local.value if local and isinstance(local.value, Mapping) else {}
        eligible_count = int(local_value.get("comparable_count") or 0)
        metadata.update({
            "eligible_count": eligible_count,
            "truncated": eligible_count > metadata["candidate_count"],
        })
        return (
            [AnalysisOrchestrator._model(ComparableEstate, row) for row in ranked],
            AnalysisOrchestrator._model(ComparableMetadata, metadata),
        )

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
        return EstateValuation(
            listed_price=listed,
            estimated_price=prediction.estimated_price,
            **valuation_metrics(listed, prediction.estimated_price, area_m2),
            inference_ms=prediction.inference_ms,
            lower_bound=prediction.lower_bound,
            upper_bound=prediction.upper_bound,
            interval_level=prediction.interval_level,
            calibration_sample_count=prediction.calibration_sample_count,
            out_of_time_coverage=prediction.out_of_time_coverage,
            model_version=prediction.model_version,
            uncertainty_status=prediction.uncertainty_status,
            valuation_class=classify_asking_price(
                listed,
                prediction.estimated_price,
                prediction.lower_bound,
                prediction.upper_bound,
                uncertainty_status=prediction.uncertainty_status,
            ),
        )

    @staticmethod
    def _model_or_none(model: type[ValueT], outcome: ComponentOutcome | None) -> ValueT | None:
        return AnalysisOrchestrator._model(model, outcome.value) if outcome and outcome.value is not None else None

    @staticmethod
    def _attach_market_heat(estate: dict[str, Any], location: LocationMetrics | None) -> None:
        metrics = location.metrics if location is not None else {}
        estate["market_heat"] = published_cell_indicators(metrics).get("market_heat")

    async def _estate_with_published_heat(
        self,
        context: TenantContext,
        estate: dict[str, Any],
    ) -> dict[str, Any]:
        getter = getattr(self._repository, "estate_location_metrics", None)
        if getter is None:
            estate["market_heat"] = None
            return estate
        try:
            async with asyncio.timeout(self._settings.branch_timeout_seconds):
                location = await getter(context, estate)
        except (TimeoutError, ServiceError) as exc:
            logger.warning("Published heat unavailable for estate pair: %s", type(exc).__name__)
            estate["market_heat"] = None
            return estate
        metrics = location.get("metrics", {}) if isinstance(location, Mapping) else {}
        estate["market_heat"] = published_cell_indicators(metrics).get("market_heat")
        return estate

    @staticmethod
    def _models(model: type[ValueT], outcome: ComponentOutcome | None) -> list[ValueT]:
        return [AnalysisOrchestrator._model(model, row) for row in (outcome.value if outcome and outcome.value else [])]

    @staticmethod
    def _model(model: type[ValueT], value: Mapping[str, Any]) -> ValueT:
        """Make a transport model strict without leaking unselected DB fields."""
        payload = {key: item for key, item in dict(value).items() if key in model.model_fields}
        return model.model_validate(payload)

    async def _estate_with_liquidity(
        self,
        context: TenantContext,
        estate: Mapping[str, Any],
        horizon_days: int | None,
    ) -> dict[str, Any]:
        """Decorate an already-authorized estate with the aggregate model result."""
        artifact = await self._liquidity_artifact(context) if horizon_days is not None else None
        return self._with_liquidity_artifact(estate, artifact, horizon_days)

    @staticmethod
    def _with_liquidity_artifact(
        estate: Mapping[str, Any],
        artifact: Mapping[str, Any] | None,
        horizon_days: int | None,
    ) -> dict[str, Any]:
        result = score_listing_liquidity(artifact, estate, horizon_days=horizon_days)
        payload = dict(estate)
        payload.update({
            "liquidity_score": result.score,
            "liquidity_horizon_days": result.horizon_days,
            "liquidity_status": result.status,
            "liquidity_model_version": result.model_version,
        })
        return payload

    async def _liquidity_artifact(self, context: TenantContext) -> Mapping[str, Any] | None:
        """Remain compatible with focused test repositories that predate this model."""
        getter = getattr(self._repository, "latest_liquidity_survival_model", None)
        return await getter(context) if callable(getter) else None

    @staticmethod
    def _heatmap_cell(row: Mapping[str, Any], liquidity_horizon_days: int | None = None) -> HeatmapCell:
        payload = _decode_geojson(row)
        payload['indicators'] = published_cell_indicators(
            payload['metrics'], liquidity_horizon_days=liquidity_horizon_days,
        )
        payload['liquidity_details'] = published_cell_liquidity_details(
            payload['metrics'], liquidity_horizon_days=liquidity_horizon_days,
        )
        return AnalysisOrchestrator._model(HeatmapCell, payload)

    @staticmethod
    def _timing(started: float, outcomes: Mapping[str, ComponentOutcome]) -> AnalysisTiming:
        return AnalysisTiming(
            total_ms=(time.perf_counter() - started) * 1_000,
            components=[outcome.status for outcome in outcomes.values()],
        )


def _decode_geojson(row: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(json_safe(row))
    for key in ("boundary", "center", "metrics"):
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


def _latest_snapshot_date(cells: list[Mapping[str, Any]]) -> date | None:
    dates: list[date] = []
    for cell in cells:
        value = cell.get("period_end")
        if isinstance(value, date):
            dates.append(value)
            continue
        try:
            dates.append(date.fromisoformat(str(value)[:10]))
        except (TypeError, ValueError):
            continue
    return max(dates) if dates else None
