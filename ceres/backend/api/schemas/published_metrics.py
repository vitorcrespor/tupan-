"""Published global analytics, distinct from tenant listings and AI prose."""
from datetime import date
from typing import Literal

from pydantic import Field

from backend.api.schemas.common import ApiSchema


class PublishedMetricPoint(ApiSchema):
    period: date
    value: float | None = None
    reason: str | None = None


class PublishedMetric(ApiSchema):
    metric: str
    unit: str
    value: float | None = None
    observed_on: date | None = None
    source_name: str | None = None
    status: Literal['available', 'unavailable']
    reason: str | None = None
    points: list[PublishedMetricPoint] = Field(default_factory=list)
    horizon_days: int | None = Field(default=None, ge=1, le=3650)


class PublishedMarketResponse(ApiSchema):
    scope: Literal['platform'] = 'platform'
    city: str | None = None
    area: str | None = None
    h3_index: str | None = None
    aggregation: Literal['published'] = 'published'
    liquidity_horizon_days: int | None = Field(default=None, ge=1, le=3650)
    metrics: list[PublishedMetric]
