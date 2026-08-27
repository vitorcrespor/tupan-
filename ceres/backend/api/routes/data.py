from __future__ import annotations

from fastapi import APIRouter, Depends, status

from backend.api.dependencies import get_property_service
from backend.api.schemas.common import ErrorResponse
from backend.api.schemas.property import AreaCreateRequest, AreaResponse, CityCreateRequest, CityResponse
from backend.services.property import PropertyService


router = APIRouter(tags=["data"])
ERRORS = {409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}}


@router.post("/cities", response_model=CityResponse, status_code=status.HTTP_201_CREATED, responses=ERRORS)
def create_city(request: CityCreateRequest, service: PropertyService = Depends(get_property_service)) -> CityResponse:
    return service.create_city(request)


@router.post("/areas", response_model=AreaResponse, status_code=status.HTTP_201_CREATED, responses=ERRORS)
def create_area(request: AreaCreateRequest, service: PropertyService = Depends(get_property_service)) -> AreaResponse:
    return service.create_area(request)
