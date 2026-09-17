from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import Field

from backend.api.schemas.common import ApiSchema, SourceInfo


MarketMetric = Literal[
    "price_m2", "asking_price", "avm_price", "avm_deviation", "market_heat",
    "dom", "active_listings", "regional_exposure", "pricing_distribution",
    "kind_distribution", "listing_age", "liquidity", "price_growth", "sales_velocity",
]


class MarketCellsQuery(ApiSchema):
    city: str | None = None
    neighborhood: str | None = None
    property_kind: str | None = None
    h3_resolution: int = Field(default=9, ge=0, le=15)
    period_days: int | None = Field(default=None, ge=1)
    price_min: float | None = Field(default=None, ge=0)
    price_max: float | None = Field(default=None, ge=0)
    price_m2_min: float | None = Field(default=None, ge=0)
    price_m2_max: float | None = Field(default=None, ge=0)
    area_min: float | None = Field(default=None, ge=0)
    area_max: float | None = Field(default=None, ge=0)
    bedrooms_min: int | None = Field(default=None, ge=0)
    bedrooms_max: int | None = Field(default=None, ge=0)
    bathrooms_min: int | None = Field(default=None, ge=0)
    bathrooms_max: int | None = Field(default=None, ge=0)
    parking_min: int | None = Field(default=None, ge=0)
    parking_max: int | None = Field(default=None, ge=0)
    dom_min: float | None = Field(default=None, ge=0)
    dom_max: float | None = Field(default=None, ge=0)
    heat_min: float | None = None
    heat_max: float | None = None
    growth_min: float | None = None
    growth_max: float | None = None
    inventory_min: int | None = Field(default=None, ge=0)
    inventory_max: int | None = Field(default=None, ge=0)


class H3CellResponse(ApiSchema):
    h3_index: str
    h3_resolution: int
    city: str | None = None
    neighborhood: str | None = None
    center: tuple[float, float] | None = None
    boundary: list[tuple[float, float]] = Field(default_factory=list)
    market_heat: float | None = None
    average_price_m2: float | None = None
    price_growth: float | None = None
    inventory: int
    average_dom_days: float | None = None
    sales_velocity: float | None = None
    calculation: Literal["EXISTING_MODEL", "UNAVAILABLE"]
    source: Literal["LIVE", "MOCK"]


class MarketCellsResponse(ApiSchema):
    source: SourceInfo
    filters: MarketCellsQuery
    cells: list[H3CellResponse]


class MarketRegionResponse(ApiSchema):
    cell: H3CellResponse
    source: SourceInfo


class MarketOverviewResponse(ApiSchema):
    source: SourceInfo
    metrics: list[dict[str, str]]
    trends: dict
    exposure: list[dict]
    signals: list[dict]
    brief: dict[str, str]


class MarketIntelligenceRequest(ApiSchema):
    metric: MarketMetric
    city: str | None = Field(default=None, max_length=160)
    region: str = "All neighborhoods"
    comparison_region: str = "No comparison"
    period: Literal["All available", "90 days", "180 days", "12 months"] = "All available"
    aggregation: Literal["Mean", "Median", "Count", "Sum"] = "Median"


class MarketIntelligenceResponse(ApiSchema):
    source: SourceInfo
    controls: dict[str, str]
    available_geographies: list[str]
    metric: dict[str, str]
    metrics: list[dict[str, str]]
    chart: dict
    summary_statistics: dict


class MetricPointResponse(ApiSchema):
    period: date | str
    value: float | None = None


class MetricSeriesResponse(ApiSchema):
    metric: str
    unit: str
    aggregation: str
    points: list[MetricPointResponse]
    source: SourceInfo


class MetricCatalogItem(ApiSchema):
    key: MarketMetric
    label: str
    group: str
    source: Literal["DATA", "MODEL"]


class MetricCatalogResponse(ApiSchema):
    metrics: list[MetricCatalogItem]
