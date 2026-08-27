from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_portfolio_service
from backend.api.schemas.common import ErrorResponse
from backend.api.schemas.portfolio import PortfolioAnalysisRequest, PortfolioAnalyticsResponse
from backend.services.portfolio import PortfolioService


router = APIRouter(prefix="/portfolio", tags=["portfolio"])
ERRORS = {422: {"model": ErrorResponse}, 424: {"model": ErrorResponse}, 503: {"model": ErrorResponse}}


@router.get("/analytics", response_model=PortfolioAnalyticsResponse, responses=ERRORS)
def collection_portfolio_analytics(service: PortfolioService = Depends(get_portfolio_service)) -> PortfolioAnalyticsResponse:
    return service.current_collection()


@router.post("/analytics", response_model=PortfolioAnalyticsResponse, responses=ERRORS)
def supplied_portfolio_analytics(
    request: PortfolioAnalysisRequest,
    service: PortfolioService = Depends(get_portfolio_service),
) -> PortfolioAnalyticsResponse:
    return service.analyse_request(request)
