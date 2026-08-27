from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_forecast_service
from backend.api.schemas.common import ErrorResponse
from backend.api.schemas.forecast import ForecastRequest, ForecastResponse
from backend.services.forecast import ForecastService


router = APIRouter(prefix="/forecast", tags=["forecast"])
ERRORS = {404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}}


@router.post("", response_model=ForecastResponse, responses=ERRORS)
def forecast(request: ForecastRequest, service: ForecastService = Depends(get_forecast_service)) -> ForecastResponse:
    return service.forecast(request)
