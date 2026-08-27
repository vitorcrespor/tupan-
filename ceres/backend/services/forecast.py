from __future__ import annotations

import math
from typing import Any

from backend.api.schemas.forecast import (
    ForecastContextResponse,
    ForecastPoint,
    ForecastRequest,
    ForecastResponse,
)
from backend.services.errors import DomainValidationError, UnavailableError
from backend.services.property import PropertyService
from backend.services.serialization import model_payload


class ForecastService:
    """Thin adapter for the existing property price quantile-forecast model."""

    def __init__(self, properties: PropertyService) -> None:
        self.properties = properties

    def forecast(self, request: ForecastRequest) -> ForecastResponse:
        if request.property_id:
            property_ = self.properties.get_domain(request.property_id)
        else:
            try:
                from radar.data_base import data_type as data

                property_ = data.real_estate.model_validate(model_payload(request.property))
            except ValueError as exc:
                raise DomainValidationError("The forecast property is invalid.", details={"reason": str(exc)}) from exc
            except Exception as exc:
                raise UnavailableError("The forecast domain model is unavailable.") from exc
        try:
            from train.analytics import ForecastArtifactMissingError, analyze_tendency

            # Directly use the existing quantile predictions. The legacy
            # ``tendency_prediction`` wrapper mixes them with an uncalibrated
            # certainty calculation, which is not a forecast confidence score
            # and must not be exposed as one.
            log_interval = [
                analyze_tendency(property_, percentile, request.time_span_days)
                for percentile in (0.1, 0.5, 0.9)
            ]
            interval = [self._finite_positive(math.expm1(self._scalar(value))) for value in log_interval]
            current_value = self.properties._current_price(property_)
            expected_growth = ((interval[1] / current_value) - 1) * 100
        except ForecastArtifactMissingError as exc:
            raise UnavailableError(
                "No persisted time-series forecast artifact is available for inference.",
                details={"reason": "forecast_model_artifact_missing"},
            ) from exc
        except ValueError as exc:
            raise DomainValidationError(
                "This property lacks the inputs required by the existing forecast.",
                details={"reason": str(exc)},
            ) from exc
        except Exception as exc:
            raise UnavailableError(
                "The existing time-series forecasting model is unavailable.",
                details={"reason": "forecast_model_unavailable"},
            ) from exc
        return ForecastResponse(
            property_id=request.property_id,
            time_span_days=request.time_span_days,
            current_value=current_value,
            expected_growth_pct=expected_growth,
            historical=[],
            forecast=[
                ForecastPoint(
                    period_days=request.time_span_days,
                    value=interval[1],
                    p10=interval[0],
                    p90=interval[2],
                )
            ],
            interval=interval,
            context=self._context_response(property_),
        )

    @staticmethod
    def _finite_positive(value: Any) -> float:
        number = float(value)
        if not math.isfinite(number) or number <= 0:
            raise ValueError("The existing forecast returned a non-positive or non-finite price.")
        return number

    @staticmethod
    def _scalar(value: Any) -> float:
        if hasattr(value, "item") and callable(value.item):
            value = value.item()
        return float(value)

    @staticmethod
    def _context_response(property_: Any) -> ForecastContextResponse | None:
        context = getattr(property_, "market_context", None)
        if context is None:
            return None
        indicator_names = (
            "selic_rate",
            "real_interest_rate",
            "mortgage_rate",
            "mortgage_credit_yoy",
            "mortgage_concessions_yoy",
            "mortgage_delinquency_rate",
            "ipca_yoy",
            "real_income",
            "unemployment_rate",
            "ibc_br_index",
            "sinapi_cost_m2",
            "fipezap_index",
        )
        indicators = {
            name: value
            for name in indicator_names
            if (value := getattr(context, name, None)) is not None and math.isfinite(float(value))
        }
        return ForecastContextResponse(
            reference_date=getattr(context, "reference_date", None),
            city=getattr(context, "city", None),
            state=getattr(context, "state", None),
            indicators=indicators,
        )
