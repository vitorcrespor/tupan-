from __future__ import annotations

from pydantic import Field

from backend.api.schemas.common import ApiSchema, SourceInfo
from backend.api.schemas.property import PropertyInput


class SoldPropertyInput(PropertyInput):
    sold_price: float | None = Field(default=None, ge=0)
    sale_date: str | None = None
    practiced_comission: float | None = Field(default=None, ge=0)


class PortfolioAnalysisRequest(ApiSchema):
    properties: list[PropertyInput] = Field(default_factory=list)
    sold_properties: list[SoldPropertyInput] = Field(default_factory=list)
    target_commission: float | None = Field(default=None, ge=0)


class PortfolioConcentrationItem(ApiSchema):
    region: str
    property_count: int = Field(ge=0)
    portfolio_value: float = Field(ge=0)
    share: float = Field(ge=0, le=1)


class PortfolioTypeMixItem(ApiSchema):
    kind: str
    property_count: int = Field(ge=0)
    portfolio_value: float = Field(ge=0)
    share: float = Field(ge=0, le=1)


class PortfolioRegionalPerformanceItem(ApiSchema):
    region: str
    property_count: int = Field(ge=0)
    average_expected_growth: float | None = None
    average_price_per_m2: float | None = Field(default=None, ge=0)
    average_dom_days: float | None = Field(default=None, ge=0)


class PortfolioValuationItem(ApiSchema):
    property_id: str
    title: str
    region: str | None = None
    kind: str | None = None
    asking_price: float | None = Field(default=None, ge=0)
    estimated_price: float | None = Field(default=None, ge=0)
    price_gap: float | None = None
    dom_days: float | None = Field(default=None, ge=0)
    expected_growth: float | None = None


class PortfolioAnalyticsResponse(ApiSchema):
    active_listing_count: int = Field(default=0, ge=0)
    sold_listing_count: int = Field(default=0, ge=0)
    portfolio_value: float = Field(default=0, ge=0)
    average_asking_price: float | None = Field(default=None, ge=0)
    median_asking_price: float | None = Field(default=None, ge=0)
    average_price_per_m2: float | None = Field(default=None, ge=0)
    average_price_gap: float | None = None
    average_expected_growth: float | None = None
    average_listing_age_days: float | None = Field(default=None, ge=0)
    lsp: float | None = None
    active_listing_months: float | None = None
    average_dom_days: float | None = None
    stagnation_rate: float | None = None
    exclusive_retention: float | None = None
    commission_retention: float | None = None
    gci_per_sqm: float | None = None
    hhi: float | None = None
    clustering_coefficient: float | None = None
    regional_concentration: list[PortfolioConcentrationItem] = Field(default_factory=list)
    property_type_mix: list[PortfolioTypeMixItem] = Field(default_factory=list)
    regional_performance: list[PortfolioRegionalPerformanceItem] = Field(default_factory=list)
    above_estimate: list[PortfolioValuationItem] = Field(default_factory=list)
    below_estimate: list[PortfolioValuationItem] = Field(default_factory=list)
    source: SourceInfo
