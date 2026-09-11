from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from backend.api.schemas.common import ApiSchema


class WorkspaceMemberResponse(ApiSchema):
    id: str
    email: str
    full_name: str | None = None
    role: str
    created_at: datetime


class WorkspaceMemberUpdateRequest(ApiSchema):
    role: str = Field(pattern="^(admin|user)$")


class SavedSearchCreateRequest(ApiSchema):
    name: str = Field(min_length=1, max_length=160)
    filters: dict[str, Any] = Field(default_factory=dict)


class SavedSearchResponse(ApiSchema):
    id: str
    name: str
    filters: dict[str, Any]
    created_at: datetime


class PropertyNoteCreateRequest(ApiSchema):
    note: str = Field(min_length=1, max_length=10_000)


class PropertyNoteResponse(ApiSchema):
    id: str
    property_id: str
    user_id: str
    note: str
    created_at: datetime


class DistrictBoundaryResponse(ApiSchema):
    id: str
    name: str
    geojson: dict[str, Any]
    created_at: datetime