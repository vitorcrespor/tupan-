from __future__ import annotations

from datetime import date
from typing import Any, Literal

from pydantic import Field, model_serializer

from backend.api.schemas.common import ApiSchema
from backend.api.schemas.estate import EstateResponse, PortfolioResponse, EstimateProvenance, ValuationClass


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
    liquidity_horizon_days: int | None = Field(default=None, ge=1, le=3650)


class ComparableEstate(ApiSchema):
    estimate_provenance: EstimateProvenance | None = None
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
    similarity_score: float | None = Field(default=None, ge=0, le=1)
    similarity_status: Literal[
        "available", "target_incomplete_features", "candidate_incomplete_features", "zero_vector",
    ] = "candidate_incomplete_features"
    similarity_method: Literal["cosine"] = "cosine"
    similarity_feature_version: str = "structural-area100-rooms-bathrooms-parking-v1"


class ComparableMetadata(ApiSchema):
    eligible_count: int = Field(ge=0)
    candidate_count: int = Field(ge=0)
    scored_count: int = Field(ge=0)
    returned_count: int = Field(ge=0)
    candidate_limit: int = Field(ge=1)
    truncated: bool
    similarity_method: Literal["cosine"] = "cosine"
    similarity_feature_version: str


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
    city: str | None = None
    area: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    input_version: str | None = None
    calculated_at: str | None = None
    scope: Literal["tenant", "platform"] | None = None


class EstateComparisonResponse(ApiSchema):
    estate: EstateResponse
    comparables: list[ComparableEstate] = Field(default_factory=list)
    comparable_metadata: ComparableMetadata | None = None
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
    lower_bound: float | None = Field(default=None, gt=0)
    upper_bound: float | None = Field(default=None, gt=0)
    interval_level: float | None = Field(default=None, gt=0, lt=1)
    calibration_sample_count: int | None = Field(default=None, ge=1)
    out_of_time_coverage: float | None = Field(default=None, ge=0, le=1)
    model_version: str | None = None
    uncertainty_status: Literal['calibrated', 'not_calibrated', 'unavailable'] = 'not_calibrated'
    valuation_class: ValuationClass | None = None

    @model_serializer(mode='wrap')
    def serialize_uncertainty(self, handler):
        payload = handler(self)
        if self.uncertainty_status != 'calibrated':
            for field in ('lower_bound', 'upper_bound', 'interval_level', 'calibration_sample_count',
                          'out_of_time_coverage', 'model_version'):
                payload.pop(field, None)
        return payload


class EstateDataQuality(ApiSchema):
    policy_version: str
    completeness: float = Field(ge=0, le=100)
    quality: float = Field(ge=0, le=100)
    observed_weight: float = Field(ge=0)
    missing_fields: list[str]
    critical_reasons: list[str]
    warnings: list[str]


class AvmDiagnostics(ApiSchema):
    model_type: str | None = None
    target: str | None = None
    schema_version: int | None = None
    training_rows: int | None = Field(default=None, ge=0)
    uncertainty_status: Literal['calibrated', 'not_calibrated', 'unavailable'] = 'not_calibrated'
    uncertainty_method: str | None = None
    calibration_sample_count: int | None = Field(default=None, ge=1)
    out_of_time_coverage: float | None = Field(default=None, ge=0, le=1)
    out_of_time_median_width_pct: float | None = Field(default=None, ge=0)
    model_version: str | None = None


class EstateAnalysisResponse(EstateComparisonResponse):
    valuation: EstateValuation | None = None
    data_quality: EstateDataQuality | None = None
    avm_diagnostics: AvmDiagnostics | None = None


class EstatePairMetric(ApiSchema):
    key: str
    a_value: float | None = None
    b_value: float | None = None
    difference: float | None = None
    unit: str


class EstatePairResponse(ApiSchema):
    a: EstateResponse
    b: EstateResponse
    metrics: list[EstatePairMetric]
    valuation_basis: Literal['stored_estimate'] = 'stored_estimate'
    similarity_score: float | None = Field(default=None, ge=0, le=1)
    similarity_status: Literal["available", "incomplete_features"]
    similarity_method: Literal["cosine"] = "cosine"
    similarity_feature_version: str


class PortfolioValuationSummary(ApiSchema):
    estimate_lineage_count: int = Field(default=0, ge=0)
    estimate_inputs_changed_count: int = Field(default=0, ge=0)
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
    listing_age_count: int = Field(ge=0)
    average_listing_age_days: float | None = Field(default=None, ge=0)


class PortfolioLiquiditySummary(ApiSchema):
    """Portfolio-only sale/listing survival result for the chosen horizon."""

    score: float | None = Field(default=None, ge=0, le=100)
    status: Literal[
        "available", "horizon_not_selected", "insufficient_evidence",
        "missing_listing_duration", "no_active_listings",
    ]
    horizon_days: int | None = Field(default=None, ge=1, le=3650)
    active_estate_count: int = Field(ge=0)
    eligible_estate_count: int = Field(ge=0)
    observed_estate_count: int = Field(ge=0)
    sale_event_count: int = Field(ge=0)
    model_version: str | None = None


class PortfolioMetricSnapshot(ApiSchema):
    """One persisted portfolio state; values are not inferred between dates."""

    observed_on: date
    active_estate_count: int = Field(ge=0)
    asking_price_count: int = Field(ge=0)
    estimated_count: int = Field(ge=0)
    days_on_market_count: int = Field(ge=0)
    listing_age_count: int = Field(ge=0)
    portfolio_value: float | None = Field(default=None, ge=0)
    average_days_on_market: float | None = Field(default=None, ge=0)
    average_listing_age_days: float | None = Field(default=None, ge=0)
    average_price_gap: float | None = None


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


class PortfolioPricePosition(ApiSchema):
    estimate_provenance: EstimateProvenance | None = None
    property_id: str
    title: str | None = None
    region: str | None = None
    asking_price: float | None = None
    estimated_price: float | None = None
    price_gap: float | None = None
    difference: float | None = None


class PortfolioPositions(ApiSchema):
    above_count: int = Field(ge=0)
    below_count: int = Field(ge=0)
    equal_count: int = Field(ge=0)
    missing_count: int = Field(ge=0)
    asking_count: int = Field(ge=0)
    estimated_count: int = Field(ge=0)
    rows: list[PortfolioPricePosition] = Field(default_factory=list)


class PortfolioOverviewResponse(ApiSchema):
    portfolio: PortfolioResponse
    valuation_summary: PortfolioValuationSummary | None = None
    geographic_concentration: list[PortfolioRegionConcentration] = Field(default_factory=list)
    pricing_statistics: PortfolioPricingStatistics | None = None
    liquidity_summary: PortfolioLiquiditySummary | None = None
    history: list[PortfolioMetricSnapshot] = Field(default_factory=list)
    property_distribution: list[PortfolioPropertyDistribution] = Field(default_factory=list)
    market_exposure: list[PortfolioMarketExposure] = Field(default_factory=list)
    timing: AnalysisTiming
    positions: PortfolioPositions | None = None
    top_region_share: float | None = None


class HeatmapQuery(ApiSchema):
    h3_resolution: int = Field(default=9, ge=0, le=15)
    city: str | None = Field(default=None, max_length=160)
    area: str | None = Field(default=None, max_length=160)
    period_start: date | None = None
    period_end: date | None = None
    liquidity_horizon_days: int | None = Field(default=None, ge=1, le=3650)


class HeatmapCell(ApiSchema):
    indicators: dict[str, float | None] = Field(default_factory=dict)
    liquidity_details: dict[str, Any] | None = None
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


class GeographicRegion(ApiSchema):
    city: str
    areas: list[str] = Field(default_factory=list)


class HeatmapResponse(ApiSchema):
    cells: list[HeatmapCell] = Field(default_factory=list)
    timing: AnalysisTiming


class ReportScope(ApiSchema):
    """Explicit scope for a report; it is never supplied as a tenant id."""

    city: str | None = None
    area: str | None = None
    active_only: Literal[True] = True


class ReportSummaryMetrics(ApiSchema):
    """Tenant-wide aggregates calculated over the complete authorized scope."""

    active_estate_count: int = Field(ge=0)
    asking_price_count: int = Field(ge=0)
    price_per_m2_count: int = Field(ge=0)
    days_on_market_count: int = Field(ge=0)
    average_asking_price: float | None = Field(default=None, ge=0)
    average_price_per_m2: float | None = Field(default=None, ge=0)
    average_days_on_market: float | None = Field(default=None, ge=0)


class ReportFeaturedEstate(ApiSchema):
    """A bounded, recent estate list; this deliberately does not claim a rank."""

    id: str
    title: str | None = None
    city: str | None = None
    area: str | None = None
    asking_price: float | None = Field(default=None, ge=0)
    price_per_m2: float | None = Field(default=None, ge=0)
    days_on_market: float | None = Field(default=None, ge=0)
    updated_at: str


class ReportMarketMetric(ApiSchema):
    """A separately published platform metric shown beside tenant aggregates."""

    metric: Literal["sales_velocity"]
    unit: Literal["sales/day"]
    value: float | None = Field(default=None, ge=0)
    observed_on: date | None = None
    source_name: str | None = None
    status: Literal["available", "unavailable"]
    reason: str | None = None


class ReportSummaryResponse(ApiSchema):
    scope: ReportScope
    summary: ReportSummaryMetrics | None = None
    featured_estates: list[ReportFeaturedEstate] = Field(default_factory=list)
    market_metrics: list[ReportMarketMetric] = Field(default_factory=list)
    timing: AnalysisTiming
