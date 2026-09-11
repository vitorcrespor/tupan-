from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status

from backend.api.dependencies import (
    get_settings,
    get_supabase_control_plane_service,
    get_supabase_current_principal,
)
from backend.api.schemas.auth import AuthSessionResponse, LoginRequest, MessageResponse, RegisterRequest
from backend.api.schemas.common import ErrorResponse
from backend.services.supabase_control_plane import SupabaseControlPlaneService


router = APIRouter(prefix="/auth", tags=["auth-v2"])
ERRORS = {
    401: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    422: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}


def _cookie_name() -> str:
    return f"{get_settings().auth_cookie_name}_supabase_v2"


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=_cookie_name(),
        value=token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_same_site,
        domain=settings.auth_cookie_domain,
        max_age=settings.auth_session_seconds,
        path="/api/v2",
    )


@router.post("/register", response_model=AuthSessionResponse, status_code=status.HTTP_201_CREATED, responses=ERRORS)
async def register(
    request: RegisterRequest,
    response: Response,
    service: SupabaseControlPlaneService = Depends(get_supabase_control_plane_service),
) -> AuthSessionResponse:
    user, token = await service.register_and_login(
        email=request.email,
        password=request.password,
        full_name=request.full_name,
        organization_name=request.organization_name,
    )
    _set_session_cookie(response, token)
    return AuthSessionResponse(user=user)


@router.post("/login", response_model=AuthSessionResponse, responses=ERRORS)
async def login(
    request: LoginRequest,
    response: Response,
    service: SupabaseControlPlaneService = Depends(get_supabase_control_plane_service),
) -> AuthSessionResponse:
    user, token = await service.login(email=request.email, password=request.password)
    _set_session_cookie(response, token)
    return AuthSessionResponse(user=user)


@router.get("/session", response_model=AuthSessionResponse, responses=ERRORS)
async def session(principal: dict = Depends(get_supabase_current_principal)) -> AuthSessionResponse:
    return AuthSessionResponse(user=principal)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: Request,
    response: Response,
    service: SupabaseControlPlaneService = Depends(get_supabase_control_plane_service),
) -> MessageResponse:
    await service.logout(request.cookies.get(_cookie_name()))
    settings = get_settings()
    response.delete_cookie(
        key=_cookie_name(),
        path="/api/v2",
        samesite=settings.auth_cookie_same_site,
        domain=settings.auth_cookie_domain,
    )
    return MessageResponse(message="Signed out.")
