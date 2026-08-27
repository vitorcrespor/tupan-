from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_market_service
from backend.api.schemas.common import ErrorResponse
from backend.api.schemas.market import (
    MarketIntelligenceRequest,
    MarketIntelligenceResponse,
    MetricCatalogResponse,
    MetricSeriesResponse,
)
from backend.services.market import MarketService


router = APIRouter(tags=["analytics", "metrics"])
ERRORS = {404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 424: {"model": ErrorResponse}, 503: {"model": ErrorResponse}}


@router.post("/analytics/market-intelligence", response_model=MarketIntelligenceResponse, responses=ERRORS)
def market_intelligence(
    request: MarketIntelligenceRequest,
    service: MarketService = Depends(get_market_service),
) -> MarketIntelligenceResponse:
    return service.intelligence(request)


@router.get("/metrics", response_model=MetricCatalogResponse, responses=ERRORS)
def metric_catalog(service: MarketService = Depends(get_market_service)) -> MetricCatalogResponse:
    return service.metric_catalog()


@router.get("/metrics/{metric}/history", response_model=MetricSeriesResponse, responses=ERRORS)
def metric_history(
    metric: str,
    city: str | None = None,
    area: str | None = None,
    service: MarketService = Depends(get_market_service),
) -> MetricSeriesResponse:
    return service.metric_history(metric, city=city, area=area)
