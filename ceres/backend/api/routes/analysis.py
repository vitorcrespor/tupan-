from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_analysis_orchestrator, get_current_principal, get_tenant_data_repository
from backend.api.schemas.analysis import (
    EstateAnalysisResponse,
    EstateComparisonQuery,
    EstateComparisonResponse,
    EstatePairResponse,
    HeatmapQuery,
    HeatmapResponse,
    GeographicRegion,
    PortfolioOverviewResponse,
)
from backend.api.schemas.common import ErrorResponse
from backend.api.schemas.published_metrics import PublishedMarketResponse
from backend.repositories.tenant_data import TenantContext, TenantDataRepository
from backend.services.analysis_orchestrator import AnalysisOrchestrator


router = APIRouter(tags=["production-analysis"])
ERRORS = {
    401: {"model": ErrorResponse},
    404: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
    504: {"model": ErrorResponse},
}


def tenant_context(principal: dict = Depends(get_current_principal)) -> TenantContext:
    """Create immutable request context exclusively from the server session."""
    return TenantContext.from_principal(principal)


def comparison_query(
    radius_meters: int = Query(default=2_500, ge=100, le=25_000),
    limit: int = Query(default=12, ge=1, le=50),
    liquidity_horizon_days: int | None = Query(default=None, ge=1, le=3650),
) -> EstateComparisonQuery:
    return EstateComparisonQuery(
        radius_meters=radius_meters,
        limit=limit,
        liquidity_horizon_days=liquidity_horizon_days,
    )


def heatmap_query(
    h3_resolution: int = Query(default=9, ge=0, le=15),
    city: str | None = None,
    area: str | None = None,
    period_start: date | None = None,
    period_end: date | None = None,
    liquidity_horizon_days: int | None = Query(default=None, ge=1, le=3650),
) -> HeatmapQuery:
    return HeatmapQuery(
        h3_resolution=h3_resolution,
        city=city,
        area=area,
        period_start=period_start,
        period_end=period_end,
        liquidity_horizon_days=liquidity_horizon_days,
    )


@router.get('/market/regions', response_model=list[GeographicRegion], responses=ERRORS)
async def geographic_regions(
    published_only: bool = True,
    context: TenantContext = Depends(tenant_context),
    repository: TenantDataRepository = Depends(get_tenant_data_repository),
) -> list[GeographicRegion]:
    rows = await repository.list_geographic_regions(context, published_only=published_only)
    return [GeographicRegion(**row) for row in rows]


@router.get('/analytics/estate-pair', response_model=EstatePairResponse, responses=ERRORS)
async def compare_pair(
    a_id: UUID, b_id: UUID,
    liquidity_horizon_days: int | None = Query(default=None, ge=1, le=3650),
    context: TenantContext = Depends(tenant_context),
    service: AnalysisOrchestrator = Depends(get_analysis_orchestrator),
) -> EstatePairResponse:
    return await service.compare_pair(context, str(a_id), str(b_id), liquidity_horizon_days=liquidity_horizon_days)


@router.get("/estates/{estate_id}/comparison", response_model=EstateComparisonResponse, responses=ERRORS)
async def compare_estate(
    estate_id: str,
    query: EstateComparisonQuery = Depends(comparison_query),
    context: TenantContext = Depends(tenant_context),
    service: AnalysisOrchestrator = Depends(get_analysis_orchestrator),
) -> EstateComparisonResponse:
    return await service.compare_estate(context, estate_id, query)


@router.get("/estates/{estate_id}/analysis", response_model=EstateAnalysisResponse, responses=ERRORS)
async def analyse_estate(
    estate_id: str,
    query: EstateComparisonQuery = Depends(comparison_query),
    context: TenantContext = Depends(tenant_context),
    service: AnalysisOrchestrator = Depends(get_analysis_orchestrator),
) -> EstateAnalysisResponse:
    return await service.analyse_estate(context, estate_id, query)


@router.get("/portfolios/{portfolio_id}/overview", response_model=PortfolioOverviewResponse, responses=ERRORS)
async def portfolio_overview(
    portfolio_id: str,
    liquidity_horizon_days: int | None = Query(default=None, ge=1, le=3650),
    context: TenantContext = Depends(tenant_context),
    service: AnalysisOrchestrator = Depends(get_analysis_orchestrator),
) -> PortfolioOverviewResponse:
    return await service.portfolio_overview(
        context,
        portfolio_id,
        liquidity_horizon_days=liquidity_horizon_days,
    )


@router.get('/market/published-metrics', response_model=PublishedMarketResponse, responses=ERRORS)
async def published_metrics(
    city: str | None = Query(default=None, max_length=160),
    area: str | None = Query(default=None, max_length=160),
    h3_index: str | None = Query(default=None, pattern=r'^[0-9a-f]{15}$'),
    liquidity_horizon_days: int | None = Query(default=None, ge=1, le=3650),
    context: TenantContext = Depends(tenant_context),
    service: AnalysisOrchestrator = Depends(get_analysis_orchestrator),
) -> PublishedMarketResponse:
    return await service.published_market_metrics(
        context,
        city=city,
        area=area,
        h3_index=h3_index,
        liquidity_horizon_days=liquidity_horizon_days,
    )


@router.get("/market/heatmap", response_model=HeatmapResponse, responses=ERRORS)
async def heatmap(
    query: HeatmapQuery = Depends(heatmap_query),
    context: TenantContext = Depends(tenant_context),
    service: AnalysisOrchestrator = Depends(get_analysis_orchestrator),
) -> HeatmapResponse:
    return await service.heatmap(context, query)
