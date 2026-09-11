from __future__ import annotations

from fastapi import APIRouter, Depends, status

from backend.api.dependencies import get_control_plane_service, get_current_principal
from backend.api.schemas.common import ErrorResponse
from backend.api.schemas.workspace import (
    DistrictBoundaryResponse,
    PropertyNoteCreateRequest,
    PropertyNoteResponse,
    SavedSearchCreateRequest,
    SavedSearchResponse,
    WorkspaceMemberResponse,
    WorkspaceMemberUpdateRequest,
)
from backend.services.control_plane import ControlPlaneService


router = APIRouter(prefix="/workspace", tags=["workspace"])
ERRORS = {401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}}


@router.get("/members", response_model=list[WorkspaceMemberResponse], responses=ERRORS)
async def list_members(principal: dict = Depends(get_current_principal), service: ControlPlaneService = Depends(get_control_plane_service)) -> list[WorkspaceMemberResponse]:
    return await service.list_members(principal)


@router.patch("/members/{member_id}", response_model=WorkspaceMemberResponse, responses=ERRORS)
async def change_member_role(member_id: str, request: WorkspaceMemberUpdateRequest, principal: dict = Depends(get_current_principal), service: ControlPlaneService = Depends(get_control_plane_service)) -> WorkspaceMemberResponse:
    return await service.change_member_role(principal, member_id, request.role)


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT, responses=ERRORS)
async def remove_member(member_id: str, principal: dict = Depends(get_current_principal), service: ControlPlaneService = Depends(get_control_plane_service)) -> None:
    await service.remove_member(principal, member_id)


@router.get("/saved-searches", response_model=list[SavedSearchResponse], responses=ERRORS)
async def list_saved_searches(principal: dict = Depends(get_current_principal), service: ControlPlaneService = Depends(get_control_plane_service)) -> list[SavedSearchResponse]:
    return await service.list_saved_searches(principal)


@router.post("/saved-searches", response_model=SavedSearchResponse, status_code=status.HTTP_201_CREATED, responses=ERRORS)
async def create_saved_search(request: SavedSearchCreateRequest, principal: dict = Depends(get_current_principal), service: ControlPlaneService = Depends(get_control_plane_service)) -> SavedSearchResponse:
    return await service.create_saved_search(principal, name=request.name, filters=request.filters)


@router.delete("/saved-searches/{saved_search_id}", status_code=status.HTTP_204_NO_CONTENT, responses=ERRORS)
async def delete_saved_search(saved_search_id: str, principal: dict = Depends(get_current_principal), service: ControlPlaneService = Depends(get_control_plane_service)) -> None:
    await service.delete_saved_search(principal, saved_search_id)


@router.get("/properties/{property_id}/notes", response_model=list[PropertyNoteResponse], responses=ERRORS)
async def list_notes(property_id: str, principal: dict = Depends(get_current_principal), service: ControlPlaneService = Depends(get_control_plane_service)) -> list[PropertyNoteResponse]:
    return await service.list_notes(principal, property_id)


@router.post("/properties/{property_id}/notes", response_model=PropertyNoteResponse, status_code=status.HTTP_201_CREATED, responses=ERRORS)
async def create_note(property_id: str, request: PropertyNoteCreateRequest, principal: dict = Depends(get_current_principal), service: ControlPlaneService = Depends(get_control_plane_service)) -> PropertyNoteResponse:
    return await service.create_note(principal, property_id=property_id, note=request.note)


@router.get("/district-boundaries", response_model=list[DistrictBoundaryResponse], responses=ERRORS)
async def list_boundaries(principal: dict = Depends(get_current_principal), service: ControlPlaneService = Depends(get_control_plane_service)) -> list[DistrictBoundaryResponse]:
    return await service.list_boundaries(principal)