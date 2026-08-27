from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_market_service
from backend.api.schemas.common import ErrorResponse
from backend.api.schemas.market import (
    MarketCellsQuery,
    MarketCellsResponse,
    MarketOverviewResponse,
    MarketRegionResponse,
)
from backend.services.market import MarketService


router = APIRouter(prefix="/market", tags=["market"])
ERRORS = {422: {"model": ErrorResponse}, 424: {"model": ErrorResponse}, 503: {"model": ErrorResponse}}


def market_cells_query(
    city: str | None = None,
    neighborhood: str | None = None,
    property_kind: str | None = None,
    h3_resolution: int = Query(default=9, ge=0, le=15),
    period_days: int | None = Query(default=None, ge=1),
    price_min: float | None = Query(default=None, ge=0),
    price_max: float | None = Query(default=None, ge=0),
    price_m2_min: float | None = Query(default=None, ge=0),
    price_m2_max: float | None = Query(default=None, ge=0),
    area_min: float | None = Query(default=None, ge=0),
    area_max: float | None = Query(default=None, ge=0),
    bedrooms_min: int | None = Query(default=None, ge=0),
    bedrooms_max: int | None = Query(default=None, ge=0),
    bathrooms_min: int | None = Query(default=None, ge=0),
    bathrooms_max: int | None = Query(default=None, ge=0),
    parking_min: int | None = Query(default=None, ge=0),
    parking_max: int | None = Query(default=None, ge=0),
    dom_min: float | None = Query(default=None, ge=0),
    dom_max: float | None = Query(default=None, ge=0),
    heat_min: float | None = None,
    heat_max: float | None = None,
    growth_min: float | None = None,
    growth_max: float | None = None,
    inventory_min: int | None = Query(default=None, ge=0),
    inventory_max: int | None = Query(default=None, ge=0),
) -> MarketCellsQuery:
    return MarketCellsQuery(**locals())


@router.get("/overview", response_model=MarketOverviewResponse, responses=ERRORS)
def market_overview(service: MarketService = Depends(get_market_service)) -> MarketOverviewResponse:
    return service.overview()


@router.get("/cells", response_model=MarketCellsResponse, responses=ERRORS)
def market_cells(
    filters: MarketCellsQuery = Depends(market_cells_query),
    service: MarketService = Depends(get_market_service),
) -> MarketCellsResponse:
    return service.cells(filters)


@router.get("/regions/{h3_index}", response_model=MarketRegionResponse, responses={404: {"model": ErrorResponse}, **ERRORS})
def market_region(
    h3_index: str,
    filters: MarketCellsQuery = Depends(market_cells_query),
    service: MarketService = Depends(get_market_service),
) -> MarketRegionResponse:
    return service.region(h3_index, filters)
