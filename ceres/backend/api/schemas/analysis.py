from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import Field

from backend.api.schemas.common import ApiSchema
from backend.api.schemas.estate import EstateResponse, PortfolioResponse


ComponentState = Literal["success", "degraded", "skipped"]


class AnalysisComponentStatus(ApiSchema):
    """Status for one bounded branch of a fan-out request."""

    name: str
    state: ComponentState
    duration_ms: float = Field(ge=0)
    code: str | None = None
    message: str | None = None


class AnalysisTiming(ApiSchema):
    total_ms: float = Field(ge=0)
    components: list[AnalysisComponentStatus] = Field(default_factory=list)


class EstateComparisonQuery(ApiSchema):
    radius_meters: int = Field(default=2_500, ge=100, le=25_000)
    limit: int = Field(default=12, ge=1, le=50)


class ComparableEstate(ApiSchema):
    id: str
    title: str | None = None
    property_type: str | None = None
    asking_price: float | None = Field(default=None, ge=0)
    estimated_price: float | None = Field(default=None, ge=0)
    area_m2: float | None = Field(default=None, gt=0)
    price_per_m2: float | None = Field(default=None, ge=0)
    rooms: int | None = Field(default=None, ge=0)
    bathrooms: int | None = Field(default=None, ge=0)
    parking_spaces: int | None = Field(default=None, ge=0)
    days_on_market: float | None = Field(default=None, ge=0)
    city: str | None = None
    area: str | None = None
    distance_meters: float | None = Field(default=None, ge=0)


class LocalStatistics(ApiSchema):
    comparable_count: int = Field(ge=0)
    average_asking_price: float | None = Field(default=None, ge=0)
    median_asking_price: float | None = Field(default=None, ge=0)
    average_price_per_m2: float | None = Field(default=None, ge=0)
    median_price_per_m2: float | None = Field(default=None, ge=0)
    average_days_on_market: float | None = Field(default=None, ge=0)


class MarketContextValue(ApiSchema):
    metric: str
    value: float
    unit: str | None = None
    observed_on: date
    source_name: str
    scope: Literal["tenant", "platform"]


class LocationMetrics(ApiSchema):
    h3_index: str | None = None
    h3_resolution: int | None = Field(default=None, ge=0, le=15)
    period_start: date | None = None
    period_end: date | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    calculated_at: str | None = None


class EstateComparisonResponse(ApiSchema):
    estate: EstateResponse
    comparables: list[ComparableEstate] = Field(default_factory=list)
    local_statistics: LocalStatistics | None = None
    market_context: list[MarketContextValue] = Field(default_factory=list)
    location_metrics: LocationMetrics | None = None
    timing: AnalysisTiming


class EstateValuation(ApiSchema):
    listed_price: float | None = Field(default=None, gt=0)
    estimated_price: float = Field(gt=0)
    difference: float | None = None
    difference_percent: float | None = None
    price_per_m2: float | None = Field(default=None, gt=0)
    estimated_price_per_m2: float | None = Field(default=None, gt=0)
    inference_ms: float = Field(ge=0)


class EstateAnalysisResponse(EstateComparisonResponse):
    valuation: EstateValuation | None = None


class PortfolioValuationSummary(ApiSchema):
    active_estate_count: int = Field(ge=0)
    portfolio_value: float = Field(ge=0)
    estimated_value: float = Field(ge=0)
    average_price_gap: float | None = None


class PortfolioRegionConcentration(ApiSchema):
    city: str | None = None
    area: str | None = None
    estate_count: int = Field(ge=0)
    portfolio_value: float = Field(ge=0)
    share: float = Field(ge=0, le=1)


class PortfolioPricingStatistics(ApiSchema):
    average_asking_price: float | None = Field(default=None, ge=0)
    median_asking_price: float | None = Field(default=None, ge=0)
    average_price_per_m2: float | None = Field(default=None, ge=0)
    median_price_per_m2: float | None = Field(default=None, ge=0)
    average_days_on_market: float | None = Field(default=None, ge=0)


class PortfolioPropertyDistribution(ApiSchema):
    property_type: str | None = None
    estate_count: int = Field(ge=0)
    share: float = Field(ge=0, le=1)


class PortfolioMarketExposure(ApiSchema):
    city: str | None = None
    area: str | None = None
    estate_count: int = Field(ge=0)
    average_price_m2: float | None = Field(default=None, ge=0)
    market_heat: float | None = None
    latest_observed_on: date | None = None


class PortfolioOverviewResponse(ApiSchema):
    portfolio: PortfolioResponse
    valuation_summary: PortfolioValuationSummary | None = None
    geographic_concentration: list[PortfolioRegionConcentration] = Field(default_factory=list)
    pricing_statistics: PortfolioPricingStatistics | None = None
    property_distribution: list[PortfolioPropertyDistribution] = Field(default_factory=list)
    market_exposure: list[PortfolioMarketExposure] = Field(default_factory=list)
    timing: AnalysisTiming


class HeatmapQuery(ApiSchema):
    h3_resolution: int = Field(default=9, ge=0, le=15)
    city: str | None = Field(default=None, max_length=160)
    area: str | None = Field(default=None, max_length=160)
    period_start: date | None = None
    period_end: date | None = None


class HeatmapCell(ApiSchema):
    h3_index: str
    h3_resolution: int = Field(ge=0, le=15)
    city: str | None = None
    area: str | None = None
    period_start: date
    period_end: date
    boundary: dict[str, Any] | None = None
    center: dict[str, Any] | None = None
    metrics: dict[str, Any]
    input_version: str
    calculated_at: str
    scope: Literal["tenant", "platform"]


class HeatmapResponse(ApiSchema):
    cells: list[HeatmapCell] = Field(default_factory=list)
    timing: AnalysisTiming
