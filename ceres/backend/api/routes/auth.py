from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response, status

from backend.api.dependencies import get_control_plane_service, get_current_principal, get_settings
from backend.api.schemas.auth import AuthSessionResponse, LoginRequest, MessageResponse, RegisterRequest, UserResponse
from backend.api.schemas.common import ErrorResponse
from backend.services.control_plane import ControlPlaneService


router = APIRouter(prefix="/auth", tags=["auth"])
ERRORS = {401: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 422: {"model": ErrorResponse}, 503: {"model": ErrorResponse}}


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        httponly=True,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_same_site,
        domain=settings.auth_cookie_domain,
        max_age=settings.auth_session_seconds,
        path="/api/v1",
    )


@router.post("/register", response_model=AuthSessionResponse, status_code=status.HTTP_201_CREATED, responses=ERRORS)
async def register(request: RegisterRequest, response: Response, service: ControlPlaneService = Depends(get_control_plane_service)) -> AuthSessionResponse:
    user = await service.register(
        email=request.email,
        password=request.password,
        full_name=request.full_name,
        organization_name=request.organization_name,
    )
    # A freshly registered password has been verified by the backend. Create
    # an opaque server-side session instead of exposing a token to JavaScript.
    authenticated_user, token = await service.login(email=request.email, password=request.password)
    _set_session_cookie(response, token)
    return AuthSessionResponse(user=authenticated_user)


@router.post("/login", response_model=AuthSessionResponse, responses=ERRORS)
async def login(request: LoginRequest, response: Response, service: ControlPlaneService = Depends(get_control_plane_service)) -> AuthSessionResponse:
    user, token = await service.login(email=request.email, password=request.password)
    _set_session_cookie(response, token)
    return AuthSessionResponse(user=user)


@router.get("/session", response_model=AuthSessionResponse, responses=ERRORS)
async def session(principal: dict = Depends(get_current_principal)) -> AuthSessionResponse:
    return AuthSessionResponse(user=principal)


@router.post("/logout", response_model=MessageResponse)
async def logout(request: Request, response: Response, service: ControlPlaneService = Depends(get_control_plane_service)) -> MessageResponse:
    await service.logout(request.cookies.get(get_settings().auth_cookie_name))
    settings = get_settings()
    response.delete_cookie(key=settings.auth_cookie_name, path="/api/v1", samesite=settings.auth_cookie_same_site, domain=settings.auth_cookie_domain)
    return MessageResponse(message="Signed out.")