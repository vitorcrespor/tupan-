from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field


class ApiSchema(BaseModel):
    """Base schema with a consistent JSON contract."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ErrorResponse(ApiSchema):
    code: str
    message: str
    details: dict[str, Any] | None = None
    request_id: str | None = None


class SourceInfo(ApiSchema):
    kind: Literal["LIVE", "MOCK", "UNAVAILABLE"]
    label: str
    detail: str | None = None
    calculated_at: datetime | None = None


class PageMeta(ApiSchema):
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
    total: int = Field(ge=0)


ItemT = TypeVar("ItemT")


class PaginatedResponse(ApiSchema, Generic[ItemT]):
    items: list[ItemT]
    page: PageMeta


class HealthResponse(ApiSchema):
    status: Literal["ok"] = "ok"
