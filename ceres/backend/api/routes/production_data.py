from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from backend.api.dependencies import get_current_principal, get_tenant_data_repository
from backend.api.schemas.common import ErrorResponse
from backend.api.schemas.estate import EstateCreateRequest, EstateMoveRequest, EstateResponse, EstateUpdateRequest, JobCreateRequest, JobResponse, PortfolioCreateRequest, PortfolioResponse
from backend.repositories.tenant_data import TenantContext, TenantDataRepository


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
    context: TenantContext = Depends(tenant_context),
    repository: TenantDataRepository = Depends(get_tenant_data_repository),
) -> EstateResponse:
    return await repository.get_estate(context, estate_id)


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