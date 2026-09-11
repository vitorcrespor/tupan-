from __future__ import annotations

from datetime import datetime

from pydantic import Field

from backend.api.schemas.common import ApiSchema


class UserResponse(ApiSchema):
    id: str
    email: str
    full_name: str | None = None
    organization_id: str
    role: str
    created_at: datetime


class RegisterRequest(ApiSchema):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=10, max_length=512)
    full_name: str | None = Field(default=None, max_length=160)
    organization_name: str | None = Field(default=None, max_length=160)


class LoginRequest(ApiSchema):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=512)


class AuthSessionResponse(ApiSchema):
    user: UserResponse


class MessageResponse(ApiSchema):
    message: str