from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from backend.api.dependencies import get_analysis_orchestrator, get_current_principal, get_tenant_data_repository
from backend.api.schemas.common import ErrorResponse
from backend.api.schemas.estate import EstateCreateRequest, EstateMoveRequest, EstateResponse, EstateUpdateRequest, JobCreateRequest, JobResponse, PortfolioCreateRequest, PortfolioResponse
from backend.api.schemas.analysis import ReportSummaryResponse
from backend.repositories.tenant_data import TenantContext, TenantDataRepository
from backend.services.analysis_orchestrator import AnalysisOrchestrator
from backend.api.schemas.estate import EstateAnalyticsItem, EstateAnalyticsPage
from backend.services.valuation_metrics import valuation_metrics
from backend.services.valuation_classification import classify_asking_price
from backend.services.errors import DomainValidationError
from backend.services.liquidity_survival import score_listing_liquidity
import json


router = APIRouter(tags=["production-data"])
ERRORS = {401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}}


def tenant_context(principal: dict = Depends(get_current_principal)) -> TenantContext:
    return TenantContext.from_principal(principal)


@router.get("/portfolios", response_model=list[PortfolioResponse], responses=ERRORS)
async def list_portfolios(
    context: TenantContext = Depends(tenant_context),
    repository: TenantDataRepository = Depends(get_tenant_data_repository),
) -> list[PortfolioResponse]:
    return await repository.list_portfolios(context)


@router.post("/portfolios", response_model=PortfolioResponse, status_code=status.HTTP_201_CREATED, responses=ERRORS)
async def create_portfolio(
    request: PortfolioCreateRequest,
    context: TenantContext = Depends(tenant_context),
    repository: TenantDataRepository = Depends(get_tenant_data_repository),
) -> PortfolioResponse:
    return await repository.create_portfolio(
        context, name=request.name, description=request.description, target_commission=request.target_commission
    )


@router.get("/portfolios/{portfolio_id}", response_model=PortfolioResponse, responses=ERRORS)
async def get_portfolio(
    portfolio_id: str,
    context: TenantContext = Depends(tenant_context),
    repository: TenantDataRepository = Depends(get_tenant_data_repository),
) -> PortfolioResponse:
    return await repository.get_portfolio(context, portfolio_id)

@router.get("/estates", response_model=list[EstateResponse], responses=ERRORS)
async def list_estates(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    context: TenantContext = Depends(tenant_context),
    repository: TenantDataRepository = Depends(get_tenant_data_repository),
) -> list[EstateResponse]:
    return await repository.list_estates(context, limit=limit, offset=offset)


@router.get("/analytics/estates", response_model=EstateAnalyticsPage, responses=ERRORS)
async def estate_catalog(
    limit: int = Query(default=100, ge=1, le=100), offset: int = Query(default=0, ge=0),
    city: str | None = Query(default=None, max_length=160),
    area: str | None = Query(default=None, max_length=160),
    kind: str | None = Query(default=None, max_length=120),
    portfolio_id: UUID | None = None,
    query: str | None = Query(default=None, max_length=500),
    liquidity_horizon_days: int | None = Query(default=None, ge=1, le=3650),
    context: TenantContext = Depends(tenant_context),
    repository: TenantDataRepository = Depends(get_tenant_data_repository),
) -> EstateAnalyticsPage:
    result = await repository.estate_analytics_page(context, limit=limit, offset=offset,
        city=city, area=area, kind=kind, portfolio_id=str(portfolio_id) if portfolio_id else None, query=query)
    artifact = await _liquidity_artifact(repository, context) if liquidity_horizon_days is not None else None
    items = []
    for row in result['items']:
        payload = {key: value for key, value in row.items() if key in EstateAnalyticsItem.model_fields}
        if isinstance(payload.get('attributes'), str):
            payload['attributes'] = json.loads(payload['attributes'])
        estimated = payload.get('estimated_price')
        listed = payload.get('asking_price')
        payload['stored_price_deviation_pct'] = (
            valuation_metrics(float(listed) if listed is not None else None, float(estimated), None)['difference_percent']
            if estimated is not None and estimated > 0 else None
        )
        payload['valuation_class'] = classify_asking_price(
            float(listed) if listed is not None else None,
            float(estimated) if estimated is not None else None,
            payload.get('estimated_lower_bound'),
            payload.get('estimated_upper_bound'),
            uncertainty_status='not_calibrated',
        )
        _attach_liquidity(payload, artifact, liquidity_horizon_days)
        items.append(EstateAnalyticsItem.model_validate(payload))
    return EstateAnalyticsPage(items=items, page=result['page'])


@router.get("/analytics/report-summary", response_model=ReportSummaryResponse, responses=ERRORS)
async def report_summary(
    city: str | None = Query(default=None, max_length=160),
    area: str | None = Query(default=None, max_length=160),
    featured_limit: int = Query(default=6, ge=1, le=12),
    context: TenantContext = Depends(tenant_context),
    service: AnalysisOrchestrator = Depends(get_analysis_orchestrator),
) -> ReportSummaryResponse:
    if area is not None and city is None:
        raise DomainValidationError("A report area requires an explicit city.")
    return await service.report_summary(
        context,
        city=city,
        area=area,
        featured_limit=featured_limit,
    )


@router.post("/estates", response_model=EstateResponse, status_code=status.HTTP_201_CREATED, responses=ERRORS)
async def create_estate(
    request: EstateCreateRequest,
    context: TenantContext = Depends(tenant_context),
    repository: TenantDataRepository = Depends(get_tenant_data_repository),
) -> EstateResponse:
    return await repository.create_estate(context, request.model_dump(mode="json"))


@router.get("/estates/{estate_id}", response_model=EstateResponse, responses=ERRORS)
async def get_estate(
    estate_id: str,
    liquidity_horizon_days: int | None = Query(default=None, ge=1, le=3650),
    context: TenantContext = Depends(tenant_context),
    repository: TenantDataRepository = Depends(get_tenant_data_repository),
) -> EstateResponse:
    estate = await repository.get_estate(context, estate_id)
    artifact = await _liquidity_artifact(repository, context) if liquidity_horizon_days is not None else None
    _attach_liquidity(estate, artifact, liquidity_horizon_days)
    return EstateResponse.model_validate(estate)


async def _liquidity_artifact(repository: TenantDataRepository, context: TenantContext) -> dict | None:
    """Read the aggregate model only after the request has established tenant context."""
    return await repository.latest_liquidity_survival_model(context)


def _attach_liquidity(payload: dict, artifact: dict | None, horizon_days: int | None) -> None:
    result = score_listing_liquidity(artifact, payload, horizon_days=horizon_days)
    payload.update({
        "liquidity_score": result.score,
        "liquidity_horizon_days": result.horizon_days,
        "liquidity_status": result.status,
        "liquidity_model_version": result.model_version,
    })


@router.patch("/estates/{estate_id}", response_model=EstateResponse, responses=ERRORS)
async def update_estate(
    estate_id: str,
    request: EstateUpdateRequest,
    context: TenantContext = Depends(tenant_context),
    repository: TenantDataRepository = Depends(get_tenant_data_repository),
) -> EstateResponse:
    return await repository.update_estate(context, estate_id, request.model_dump(exclude_unset=True, mode="json"))


@router.patch("/estates/{estate_id}/portfolio", response_model=EstateResponse, responses=ERRORS)
async def move_estate_to_portfolio(
    estate_id: str,
    request: EstateMoveRequest,
    context: TenantContext = Depends(tenant_context),
    repository: TenantDataRepository = Depends(get_tenant_data_repository),
) -> EstateResponse:
    return await repository.move_estate_to_portfolio(context, estate_id, request.portfolio_id)


@router.delete("/estates/{estate_id}", status_code=status.HTTP_204_NO_CONTENT, responses=ERRORS)
async def delete_estate(
    estate_id: str,
    context: TenantContext = Depends(tenant_context),
    repository: TenantDataRepository = Depends(get_tenant_data_repository),
) -> None:
    await repository.delete_estate(context, estate_id)


@router.post("/jobs", response_model=JobResponse, status_code=status.HTTP_202_ACCEPTED, responses=ERRORS)
async def queue_job(
    request: JobCreateRequest,
    context: TenantContext = Depends(tenant_context),
    repository: TenantDataRepository = Depends(get_tenant_data_repository),
) -> JobResponse:
    return await repository.create_job(
        context,
        job_type=request.job_type,
        payload=request.payload,
        idempotency_key=request.idempotency_key,
        input_version=request.input_version,
    )


@router.get("/jobs/{job_id}", response_model=JobResponse, responses=ERRORS)
async def get_job(
    job_id: str,
    context: TenantContext = Depends(tenant_context),
    repository: TenantDataRepository = Depends(get_tenant_data_repository),
) -> JobResponse:
    return await repository.get_job(context, job_id)
