from __future__ import annotations

from collections import defaultdict
from typing import Any

from backend.api.schemas.common import SourceInfo
from backend.api.schemas.market import (
    H3CellResponse,
    MarketCellsQuery,
    MarketCellsResponse,
    MarketIntelligenceRequest,
    MarketIntelligenceResponse,
    MarketOverviewResponse,
    MarketRegionResponse,
    MetricCatalogResponse,
    MetricPointResponse,
    MetricSeriesResponse,
)
from backend.services.errors import InsufficientDataError, NotFoundError, UnavailableError
from backend.services.property import PropertyService
from backend.services.serialization import json_safe


class MarketService:
    """Coordinates existing market cell and presentation adapters without new calculations."""

    def __init__(self, properties: PropertyService, *, allow_mock_data: bool) -> None:
        self.properties = properties
        self.allow_mock_data = allow_mock_data

    def cells(self, filters: MarketCellsQuery) -> MarketCellsResponse:
        try:
            from predict.market_heat import calculate_market_cells
        except Exception as exc:
            raise UnavailableError("The H3 market-cell backend could not be initialized.") from exc

        records = self.properties._properties_with_ids()
        properties = [property_ for _, property_ in records]
        raw_filters = filters.model_dump(exclude_none=True)
        try:
            cells = calculate_market_cells(
                properties,
                resolution=filters.h3_resolution,
                filters=raw_filters,
                source="LIVE",
            )
        except Exception as exc:
            raise UnavailableError("The H3 market-cell calculation failed.") from exc
        source = SourceInfo(
            kind="LIVE",
            label="DATA · LIVE DATABASE",
            detail=f"{len(properties)} property records from the configured collection",
        )
        return MarketCellsResponse(
            source=source,
            filters=filters,
            cells=[self._cell_response(cell) for cell in cells],
        )

    def region(self, h3_index: str, filters: MarketCellsQuery) -> MarketRegionResponse:
        result = self.cells(filters)
        for cell in result.cells:
            if cell.h3_index == h3_index:
                return MarketRegionResponse(cell=cell, source=result.source)
        raise NotFoundError("Market region not found for the selected H3 cell.", details={"h3_index": h3_index})

    def overview(self) -> MarketOverviewResponse:
        snapshot = self._analytics_controller().overview_snapshot()
        source = self._source_info(snapshot.get("source") or {})
        self._reject_mock(source)
        return MarketOverviewResponse(
            source=source,
            metrics=json_safe(snapshot.get("metrics") or []),
            trends=json_safe(snapshot.get("trends") or {}),
            exposure=json_safe(snapshot.get("exposure") or []),
            signals=json_safe(snapshot.get("signals") or []),
            brief=json_safe(snapshot.get("brief") or {}),
        )

    def intelligence(self, request: MarketIntelligenceRequest) -> MarketIntelligenceResponse:
        snapshot = self._analytics_controller().market_intelligence_snapshot(request.model_dump())
        source = self._source_info(snapshot.get("source") or {})
        self._reject_mock(source)
        return MarketIntelligenceResponse(
            source=source,
            controls=json_safe(snapshot.get("controls") or {}),
            available_geographies=json_safe(snapshot.get("available_geographies") or []),
            metric=json_safe(snapshot.get("metric") or {}),
            metrics=json_safe(snapshot.get("metrics") or []),
            chart=json_safe(snapshot.get("chart") or {}),
            summary_statistics=json_safe(snapshot.get("summary_statistics") or {}),
        )

    def metric_catalog(self) -> MetricCatalogResponse:
        try:
            from ui.controllers.analytics_controller import MARKET_INTELLIGENCE_METRICS
        except Exception as exc:
            raise UnavailableError("The existing market-metric catalog is unavailable.") from exc
        return MetricCatalogResponse(
            metrics=[{"key": key, **definition} for key, definition in MARKET_INTELLIGENCE_METRICS.items()]
        )

    def metric_history(
        self,
        metric: str,
        *,
        city: str | None,
        area: str | None,
    ) -> MetricSeriesResponse:
        if metric != "price_m2":
            raise InsufficientDataError(
                "Historical data is currently available only for price_m2 from stored listing-price history.",
                details={"metric": metric},
            )
        series: dict[str, list[float]] = defaultdict(list)
        for _, property_ in self.properties._properties_with_ids():
            location = getattr(property_, "location", None)
            if city is not None and getattr(location, "city", None) != city:
                continue
            if area is not None and getattr(location, "area", None) != area:
                continue
            metrics = getattr(property_, "real_estate_metrics", None)
            square_metrage = getattr(metrics, "square_metrage", None)
            pricing = getattr(property_, "re_price_metrics", None)
            if not square_metrage or not pricing:
                continue
            for point in getattr(pricing, "listed_prices", None) or []:
                series[point.date.isoformat()].append(float(point.price) / float(square_metrage))
        points = [
            MetricPointResponse(period=period, value=sum(values) / len(values))
            for period, values in sorted(series.items())
        ]
        if not points:
            raise InsufficientDataError("No stored listing-price history matches this query.", details={"metric": metric})
        return MetricSeriesResponse(
            metric=metric,
            unit="BRL/m²",
            aggregation="mean",
            points=points,
            source=SourceInfo(kind="LIVE", label="DATA · LISTING PRICE HISTORY"),
        )

    @staticmethod
    def _cell_response(cell: Any) -> H3CellResponse:
        return H3CellResponse(
            h3_index=cell.h3_index,
            h3_resolution=cell.h3_resolution,
            city=cell.city,
            neighborhood=cell.neighborhood,
            center=cell.center,
            boundary=cell.boundary,
            market_heat=cell.market_heat,
            demand_score=cell.demand_score,
            average_price_m2=cell.average_price_m2,
            price_growth=cell.price_growth,
            inventory=cell.inventory,
            average_dom_days=cell.average_dom,
            sales_velocity=cell.sales_velocity,
            calculation=cell.calculation,
            source=cell.source,
        )

    @staticmethod
    def _analytics_controller():
        """Reuse the existing analytical adapter until it is extracted from the desktop package."""
        try:
            from ui.controllers.analytics_controller import AnalyticsController
        except Exception as exc:
            raise UnavailableError("The existing market analytics adapter is unavailable.") from exc
        return AnalyticsController()

    @staticmethod
    def _source_info(source: dict[str, Any]) -> SourceInfo:
        kind = str(source.get("kind", "UNAVAILABLE")).upper()
        normalized_kind = {"DATABASE": "LIVE", "LIVE": "LIVE", "MOCK": "MOCK"}.get(kind, "UNAVAILABLE")
        return SourceInfo(
            kind=normalized_kind,
            label=str(source.get("label", "DATA · UNAVAILABLE")),
            detail=source.get("detail"),
        )

    def _reject_mock(self, source: SourceInfo) -> None:
        if source.kind == "MOCK" and not self.allow_mock_data:
            raise InsufficientDataError(
                "Live data is unavailable and mock data is disabled for this API environment.",
                details={"source": "MOCK"},
            )
