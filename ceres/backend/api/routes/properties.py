from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from backend.api.dependencies import get_property_service
from backend.api.schemas.common import ErrorResponse, PageMeta, PaginatedResponse
from backend.api.schemas.property import (
    PropertyCreateRequest,
    PropertyCreateResponse,
    PropertyImportResponse,
    PropertyResponse,
    PropertySearchRequest,
    PropertySearchResult,
    PropertyValuationResponse,
)
from backend.services.property import PropertyService


router = APIRouter(prefix="/properties", tags=["properties"])
ERRORS = {422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}}


@router.get("", response_model=PaginatedResponse[PropertyResponse], responses=ERRORS)
def list_properties(
    city: str | None = None,
    area: str | None = None,
    kind: str | None = None,
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    service: PropertyService = Depends(get_property_service),
) -> PaginatedResponse[PropertyResponse]:
    items, total = service.list(city=city, area=area, kind=kind, limit=limit, offset=offset)
    return PaginatedResponse(items=items, page=PageMeta(limit=limit, offset=offset, total=total))


@router.post("/search", response_model=PaginatedResponse[PropertySearchResult], responses=ERRORS)
def search_properties(
    request: PropertySearchRequest,
    service: PropertyService = Depends(get_property_service),
) -> PaginatedResponse[PropertySearchResult]:
    items = service.search(request)
    return PaginatedResponse(items=items, page=PageMeta(limit=request.limit, offset=0, total=len(items)))


@router.post("", response_model=PropertyCreateResponse, status_code=status.HTTP_201_CREATED, responses={409: {"model": ErrorResponse}, **ERRORS})
def create_property(
    request: PropertyCreateRequest,
    service: PropertyService = Depends(get_property_service),
) -> PropertyCreateResponse:
    return service.create(request)


@router.post("/import", response_model=PropertyImportResponse, responses=ERRORS)
async def import_properties(
    file: UploadFile = File(...),
    normalize_addresses: bool = True,
    service: PropertyService = Depends(get_property_service),
) -> PropertyImportResponse:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".xlsx", ".xls"}:
        from backend.services.errors import DomainValidationError

        raise DomainValidationError("Only .xlsx and .xls workbooks are supported.")
    temporary_path: str | None = None
    try:
        with NamedTemporaryFile(suffix=suffix, delete=False) as temporary_file:
            temporary_path = temporary_file.name
            while chunk := await file.read(1024 * 1024):
                temporary_file.write(chunk)
        return service.import_workbook(temporary_path, normalize_addresses=normalize_addresses)
    finally:
        await file.close()
        if temporary_path:
            Path(temporary_path).unlink(missing_ok=True)


@router.get("/{property_id}", response_model=PropertyResponse, responses={404: {"model": ErrorResponse}, **ERRORS})
def get_property(property_id: str, service: PropertyService = Depends(get_property_service)) -> PropertyResponse:
    return service.get(property_id)


@router.post("/{property_id}/valuation", response_model=PropertyValuationResponse, responses={404: {"model": ErrorResponse}, **ERRORS})
def value_property(property_id: str, service: PropertyService = Depends(get_property_service)) -> PropertyValuationResponse:
    return service.valuation(property_id)
