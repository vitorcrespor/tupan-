from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import Field

from backend.api.schemas.common import ApiSchema, PageMeta


ValuationClass = Literal[
    "BELOW_ESTIMATED_RANGE",
    "WITHIN_ESTIMATED_RANGE",
    "ABOVE_ESTIMATED_RANGE",
    "INSUFFICIENT_CONFIDENCE",
]


class EstateBase(ApiSchema):
    portfolio_id: str | None = None
    external_id: str | None = Field(default=None, max_length=300)
    source_name: str | None = Field(default=None, max_length=120)
    status: Literal["active", "sold", "off_market", "archived"] = "active"
    title: str | None = Field(default=None, max_length=500)
    summary: str | None = None
    property_type: str | None = Field(default=None, max_length=120)
    exclusive: bool | None = None
    asking_price: float | None = Field(default=None, ge=0)
    last_sale_price: float | None = Field(default=None, ge=0)
    estimated_price: float | None = Field(default=None, ge=0)
    area_m2: float | None = Field(default=None, gt=0)
    price_per_m2: float | None = Field(default=None, ge=0)
    rooms: int | None = Field(default=None, ge=0)
    bathrooms: int | None = Field(default=None, ge=0)
    parking_spaces: int | None = Field(default=None, ge=0)
    age_years: int | None = Field(default=None, ge=0)
    days_on_market: float | None = Field(default=None, ge=0)
    listed_since: date | None = None
    last_sale_date: date | None = None
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=160)
    area: str | None = Field(default=None, max_length=160)
    state: str | None = Field(default=None, max_length=160)
    postal_code: str | None = Field(default=None, max_length=32)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    attributes: dict[str, Any] = Field(default_factory=dict)


class EstateCreateRequest(EstateBase):
    pass


class EstateUpdateRequest(ApiSchema):
    title: str | None = Field(default=None, max_length=500)
    summary: str | None = None
    property_type: str | None = Field(default=None, max_length=120)
    status: Literal["active", "sold", "off_market", "archived"] | None = None
    asking_price: float | None = Field(default=None, ge=0)
    estimated_price: float | None = Field(default=None, ge=0)
    area_m2: float | None = Field(default=None, gt=0)
    price_per_m2: float | None = Field(default=None, ge=0)
    rooms: int | None = Field(default=None, ge=0)
    bathrooms: int | None = Field(default=None, ge=0)
    parking_spaces: int | None = Field(default=None, ge=0)
    city: str | None = Field(default=None, max_length=160)
    area: str | None = Field(default=None, max_length=160)
    address: str | None = Field(default=None, max_length=500)
    attributes: dict[str, Any] | None = None


class EstimateProvenance(ApiSchema):
    """Server-recorded lineage; recorded_at is not a model valuation date."""

    source: str
    recorded_at: datetime
    model_version: str | None = None
    input_version: str
    status: Literal['recorded', 'inputs_changed']


class EstateResponse(EstateBase):
    estimate_provenance: EstimateProvenance | None = None
    id: str
    created_at: datetime
    updated_at: datetime
    liquidity_score: float | None = Field(default=None, ge=0, le=100)
    liquidity_horizon_days: int | None = Field(default=None, ge=1, le=3650)
    liquidity_status: Literal[
        "available", "horizon_not_selected", "model_unavailable", "insufficient_evidence",
        "missing_listing_duration", "not_active",
    ] | None = None
    liquidity_model_version: str | None = None
    market_heat: float | None = Field(default=None, ge=0, le=100)


class EstateAnalyticsItem(EstateResponse):
    stored_price_deviation_pct: float | None = None
    comparable_count: int = Field(default=0, ge=0)
    valuation_class: ValuationClass | None = None
    estimated_lower_bound: float | None = Field(default=None, gt=0)
    estimated_upper_bound: float | None = Field(default=None, gt=0)
    valuation_interval_level: float | None = Field(default=None, gt=0, lt=1)


class EstateAnalyticsPage(ApiSchema):
    items: list[EstateAnalyticsItem]
    page: PageMeta


class EstateMoveRequest(ApiSchema):
    portfolio_id: str | None = None


class JobCreateRequest(ApiSchema):
    """Queue backend work; tenant and retry limits are never client supplied."""

    job_type: str = Field(min_length=1, max_length=120)
    payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=1, max_length=200)
    input_version: str | None = Field(default=None, max_length=200)


class JobResponse(ApiSchema):
    job_id: str
    organization_id: str
    user_id: str | None = None
    job_type: str
    status: Literal["PENDING", "RUNNING", "SUCCEEDED", "FAILED"]
    progress: int = Field(ge=0, le=100)
    input_version: str | None = None
    attempt_count: int = Field(ge=0)
    max_attempts: int = Field(ge=1, le=10)
    result_reference: str | None = None
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None

class PortfolioCreateRequest(ApiSchema):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    target_commission: float | None = Field(default=None, ge=0, le=1)


class PortfolioResponse(ApiSchema):
    id: str
    name: str
    description: str | None = None
    target_commission: float | None = None
    created_by_user_id: str | None = None
    created_at: datetime
    updated_at: datetime
