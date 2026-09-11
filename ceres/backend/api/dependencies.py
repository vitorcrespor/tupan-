from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from fastapi import Depends, Request
from pydantic import BaseModel, Field

from backend.repositories.tenant_data import TenantDataRepository
from backend.services.ai.orchestrator import AiOrchestrationSettings, AiOrchestrator
from backend.services.analysis_orchestrator import AnalysisOrchestrationSettings, AnalysisOrchestrator
from backend.services.control_plane import ControlPlaneService
from backend.services.errors import UnavailableError
from backend.services.forecast import ForecastService
from backend.services.market import MarketService
from backend.services.portfolio import PortfolioService
from backend.services.property import PropertyService
from backend.services.supabase_control_plane import SupabaseControlPlaneService


class ApiSettings(BaseModel):
    cors_origins: list[str] = Field(default_factory=lambda: [
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:4173", "http://127.0.0.1:4173",
        "http://localhost:4174", "http://127.0.0.1:4174",
    ])
    allow_mock_data: bool = False
    allow_legacy_global_data: bool = False
    auth_cookie_name: str = "tupan_session"
    auth_cookie_secure: bool = False
    auth_cookie_same_site: Literal["lax", "strict", "none"] = "lax"
    auth_cookie_domain: str | None = None
    auth_session_seconds: int = 604800

    @classmethod
    def from_environment(cls) -> "ApiSettings":
        configured_origins = os.getenv("API_CORS_ORIGINS", "")
        origins = [origin.strip() for origin in configured_origins.split(",") if origin.strip()]
        allow_mock_data = os.getenv("API_ALLOW_MOCK_DATA", "false").strip().lower() in {"1", "true", "yes"}
        allow_legacy_global_data = os.getenv("API_ALLOW_LEGACY_GLOBAL_DATA", "false").strip().lower() in {"1", "true", "yes"}
        cookie_secure = os.getenv("AUTH_COOKIE_SECURE", "false").strip().lower() in {"1", "true", "yes"}
        same_site = os.getenv("AUTH_COOKIE_SAME_SITE", "lax").strip().lower()
        if same_site not in {"lax", "strict", "none"}:
            same_site = "lax"
        if same_site == "none" and not cookie_secure:
            raise ValueError("AUTH_COOKIE_SAME_SITE=none requires AUTH_COOKIE_SECURE=true.")
        environment = os.getenv("TUPAN_ENV", "development").strip().lower()
        if environment in {"production", "prod"}:
            if not origins or "*" in origins:
                raise ValueError("Production requires explicit non-wildcard API_CORS_ORIGINS.")
            if not cookie_secure:
                raise ValueError("Production requires AUTH_COOKIE_SECURE=true.")
            if allow_mock_data or allow_legacy_global_data:
                raise ValueError("Production cannot enable mock or non-tenant-scoped legacy data.")
        try:
            session_seconds = int(os.getenv("AUTH_SESSION_SECONDS", "604800"))
        except ValueError:
            session_seconds = 604800
        return cls(
            cors_origins=origins or cls().cors_origins,
            allow_mock_data=allow_mock_data,
            allow_legacy_global_data=allow_legacy_global_data,
            auth_cookie_name=os.getenv("AUTH_COOKIE_NAME", "tupan_session").strip() or "tupan_session",
            auth_cookie_secure=cookie_secure,
            auth_cookie_same_site=same_site,
            auth_cookie_domain=os.getenv("AUTH_COOKIE_DOMAIN", "").strip() or None,
            auth_session_seconds=max(300, session_seconds),
        )


@lru_cache
def get_settings() -> ApiSettings:
    return ApiSettings.from_environment()


@lru_cache
def get_property_service() -> PropertyService:
    return PropertyService()


@lru_cache
def get_market_service() -> MarketService:
    return MarketService(get_property_service(), allow_mock_data=get_settings().allow_mock_data)


@lru_cache
def get_portfolio_service() -> PortfolioService:
    return PortfolioService(get_property_service())


@lru_cache
def get_forecast_service() -> ForecastService:
    return ForecastService(get_property_service())


@lru_cache
def get_control_plane_service() -> ControlPlaneService:
    return ControlPlaneService()


@lru_cache
def get_supabase_control_plane_service() -> SupabaseControlPlaneService:
    """The isolated Supabase Auth v2 implementation."""
    return SupabaseControlPlaneService()


async def get_current_principal(
    request: Request,
    service: ControlPlaneService = Depends(get_control_plane_service),
) -> dict:
    """Resolve the opaque HttpOnly session; no user/org values come from the client."""
    token = request.cookies.get(get_settings().auth_cookie_name)
    return await service.principal(token)


async def get_supabase_current_principal(
    request: Request,
    service: SupabaseControlPlaneService = Depends(get_supabase_control_plane_service),
) -> dict:
    """Resolve only the isolated v2 cookie; v1 sessions stay independent."""
    token = request.cookies.get(f"{get_settings().auth_cookie_name}_supabase_v2")
    return await service.principal(token)


async def require_legacy_domain_access(
    principal: dict = Depends(get_current_principal),
) -> dict:
    """Block non-tenant-scoped legacy records in every production deployment."""
    if not get_settings().allow_legacy_global_data:
        raise UnavailableError(
            "Legacy global property data is disabled until its tenant migration is complete.",
            details={"reason": "legacy_data_not_tenant_scoped"},
        )
    return principal


@lru_cache
def get_tenant_data_repository() -> TenantDataRepository:
    return TenantDataRepository(get_control_plane_service())


def _positive_seconds(name: str, default: float) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError:
        return default
    return value if value > 0 else default


@lru_cache
def get_analysis_orchestrator() -> AnalysisOrchestrator:
    return AnalysisOrchestrator(
        get_tenant_data_repository(),
        settings=AnalysisOrchestrationSettings(
            total_timeout_seconds=_positive_seconds("ANALYSIS_REQUEST_TIMEOUT_SECONDS", 12.0),
            branch_timeout_seconds=_positive_seconds("ANALYSIS_BRANCH_TIMEOUT_SECONDS", 5.0),
            avm_timeout_seconds=_positive_seconds("ANALYSIS_AVM_TIMEOUT_SECONDS", 3.0),
        ),
    )


@lru_cache
def get_ai_orchestrator() -> AiOrchestrator:
    """Create the backend-only AI interpreter over tenant-authorized services."""
    try:
        max_evidence_bytes = int(os.getenv("AI_MAX_EVIDENCE_BYTES", "180000"))
    except ValueError:
        max_evidence_bytes = 180_000
    return AiOrchestrator(
        get_analysis_orchestrator(),
        market=get_market_service(),
        settings=AiOrchestrationSettings(
            request_timeout_seconds=_positive_seconds("AI_REQUEST_TIMEOUT_SECONDS", 20.0),
            max_evidence_bytes=max(10_000, max_evidence_bytes),
        ),
    )