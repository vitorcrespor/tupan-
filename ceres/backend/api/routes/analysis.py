from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query

from backend.api.dependencies import get_analysis_orchestrator, get_current_principal
from backend.api.schemas.analysis import (
    EstateAnalysisResponse,
    EstateComparisonQuery,
    EstateComparisonResponse,
    HeatmapQuery,
    HeatmapResponse,
    PortfolioOverviewResponse,
)
from backend.api.schemas.common import ErrorResponse
from backend.repositories.tenant_data import TenantContext
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
) -> EstateComparisonQuery:
    return EstateComparisonQuery(radius_meters=radius_meters, limit=limit)


def heatmap_query(
    h3_resolution: int = Query(default=9, ge=0, le=15),
    city: str | None = None,
    area: str | None = None,
    period_start: date | None = None,
    period_end: date | None = None,
) -> HeatmapQuery:
    return HeatmapQuery(
        h3_resolution=h3_resolution,
        city=city,
        area=area,
        period_start=period_start,
        period_end=period_end,
    )


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
    context: TenantContext = Depends(tenant_context),
    service: AnalysisOrchestrator = Depends(get_analysis_orchestrator),
) -> PortfolioOverviewResponse:
    return await service.portfolio_overview(context, portfolio_id)


@router.get("/market/heatmap", response_model=HeatmapResponse, responses=ERRORS)
async def heatmap(
    query: HeatmapQuery = Depends(heatmap_query),
    context: TenantContext = Depends(tenant_context),
    service: AnalysisOrchestrator = Depends(get_analysis_orchestrator),
) -> HeatmapResponse:
    return await service.heatmap(context, query)
