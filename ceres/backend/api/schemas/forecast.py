from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import Field, model_validator

from backend.api.schemas.common import ApiSchema
from backend.api.schemas.property import PropertyInput


class ForecastRequest(ApiSchema):
    """Request for the existing property-price time-series model.

    The legacy model forecasts a property's terminal price at a horizon. It
    does not support a regional market-metric series, so ``metric`` and
    ``region`` are intentionally not accepted here.
    """

    property_id: str | None = None
    property: PropertyInput | None = None
    time_span_days: int = Field(default=30, ge=1, le=3650)

    @model_validator(mode="after")
    def one_property_source(self) -> "ForecastRequest":
        if (self.property_id is None) == (self.property is None):
            raise ValueError("Provide exactly one of property_id or property.")
        return self


class ForecastHistoricalObservation(ApiSchema):
    """An observed model input series point, when supplied by the model."""

    period_days: int = Field(ge=0)
    value: float


class ForecastPoint(ApiSchema):
    """A model-predicted property price at a requested future horizon."""

    period_days: int = Field(gt=0)
    value: float = Field(gt=0, description="P50 estimated price in BRL")
    p10: float = Field(gt=0)
    p90: float = Field(gt=0)


class ForecastContextResponse(ApiSchema):
    """Contextual indicators carried by the property into the legacy model."""

    reference_date: date | None = None
    city: str | None = None
    state: str | None = None
    indicators: dict[str, float] = Field(default_factory=dict)


class ForecastResponse(ApiSchema):
    property_id: str | None = None
    metric: Literal["property_price"] = "property_price"
    unit: Literal["BRL"] = "BRL"
    time_span_days: int
    current_value: float = Field(gt=0)
    expected_growth_pct: float
    # The existing model exposes a terminal quantile forecast only; it does
    # not yield a historical series. Keeping these collections separate means
    # clients never render a prediction as an observation.
    historical: list[ForecastHistoricalObservation] = Field(default_factory=list)
    forecast: list[ForecastPoint] = Field(min_length=1, max_length=1)
    # Compatibility with the initial transport contract: [P10, P50, P90].
    interval: list[float] = Field(min_length=3, max_length=3)
    context: ForecastContextResponse | None = None
    model: Literal["existing_xgboost_quantile_time_series"] = "existing_xgboost_quantile_time_series"
