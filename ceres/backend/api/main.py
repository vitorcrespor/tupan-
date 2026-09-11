from __future__ import annotations

import logging
import os
import time
import uuid
from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.dependencies import (
    get_control_plane_service,
    get_settings,
    get_supabase_control_plane_service,
    require_legacy_domain_access,
)
from backend.api.routes import agent, analysis, analytics, auth, auth_v2, data, forecast, market, portfolio, production_data, properties, workspace
from backend.api.schemas.common import ErrorResponse, HealthResponse, ReadinessResponse
from backend.observability import configure_logging, log_event, request_id_context
from backend.security.rate_limit import SlidingWindowRateLimiter
from backend.services.errors import ServiceError
from backend.services.serialization import json_safe


load_dotenv(Path(__file__).resolve().parents[2] / ".env", override=False)

logger = logging.getLogger(__name__)
API_VERSION = os.getenv("TUPAN_API_VERSION", "1.0.0").strip() or "1.0.0"
MINIMUM_CLIENT_VERSION = os.getenv("TUPAN_MINIMUM_CLIENT_VERSION", "").strip()
TRUST_PROXY_HEADERS = os.getenv("API_TRUST_PROXY_HEADERS", "false").strip().lower() in {"1", "true", "yes"}


def _nonnegative_int(name: str, default: int) -> int:
    try:
        return max(0, int(os.getenv(name, str(default))))
    except ValueError:
        return default


AUTH_RATE_LIMIT_PER_MINUTE = _nonnegative_int("AUTH_RATE_LIMIT_PER_MINUTE", 10)
AI_RATE_LIMIT_PER_MINUTE = _nonnegative_int("AI_RATE_LIMIT_PER_MINUTE", 30)


def _version_tuple(value: str) -> tuple[int, int, int] | None:
    parts = value.strip().split(".")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        return None
    return int(parts[0]), int(parts[1]), int(parts[2])


def _client_is_supported(value: str | None) -> bool:
    if not MINIMUM_CLIENT_VERSION:
        return True
    minimum, candidate = _version_tuple(MINIMUM_CLIENT_VERSION), _version_tuple(value or "")
    return minimum is not None and candidate is not None and candidate >= minimum


def _request_identifier(request: Request) -> str:
    if TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            return forwarded.split(",", 1)[0].strip() or "unknown"
    return request.client.host if request.client else "unknown"


def _sensitive_limit(request: Request) -> tuple[str, int] | None:
    route = request.method, request.url.path
    if route in {
        ("POST", "/api/v1/auth/login"),
        ("POST", "/api/v1/auth/register"),
        ("POST", "/api/v2/auth/login"),
        ("POST", "/api/v2/auth/register"),
    }:
        return "auth", AUTH_RATE_LIMIT_PER_MINUTE
    if route == ("POST", "/api/v1/agent/chat"):
        return "ai", AI_RATE_LIMIT_PER_MINUTE
    return None


@asynccontextmanager
async def _lifespan(_: FastAPI):
    try:
        yield
    finally:
        await get_control_plane_service().close()
        await get_supabase_control_plane_service().close()


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    rate_limiter = SlidingWindowRateLimiter()
    app = FastAPI(
        title="Tupan API",
        version=API_VERSION,
        description="Thin HTTP/JSON transport layer over the existing Tupan domain services.",
        lifespan=_lifespan,
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_observability(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = request_id
        request_token = request_id_context.set(request_id)
        started = time.perf_counter()
        operation = f"{request.method} {request.url.path}"
        try:
            response: JSONResponse | None = None
            sensitive_limit = _sensitive_limit(request)
            if sensitive_limit:
                scope, limit = sensitive_limit
                allowed, retry_after = await rate_limiter.allow(scope=scope, identifier=_request_identifier(request), limit=limit)
                if not allowed:
                    response = JSONResponse(
                        status_code=429,
                        content=ErrorResponse(
                            code="rate_limit_exceeded",
                            message="Too many requests. Please retry shortly.",
                            request_id=request_id,
                        ).model_dump(mode="json", exclude_none=True),
                    )
                    response.headers["Retry-After"] = str(retry_after)
            if response is None and request.url.path not in {"/health", "/ready", "/api/v1/health", "/api/v1/ready"} and not _client_is_supported(request.headers.get("X-Tupan-Client-Version")):
                response = JSONResponse(
                    status_code=426,
                    content=ErrorResponse(
                        code="client_upgrade_required",
                        message="This desktop client version is no longer compatible with the API.",
                        details={"minimum_client_version": MINIMUM_CLIENT_VERSION, "api_version": API_VERSION},
                        request_id=request_id,
                    ).model_dump(mode="json", exclude_none=True),
                )
            if response is None:
                response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Tupan-API-Version"] = API_VERSION
            if MINIMUM_CLIENT_VERSION:
                response.headers["X-Tupan-Minimum-Client-Version"] = MINIMUM_CLIENT_VERSION
            log_event(
                logger,
                "api_request_completed",
                operation=operation,
                latency_ms=round((time.perf_counter() - started) * 1_000, 2),
                status=response.status_code,
            )
            return response
        except Exception as exc:
            log_event(
                logger,
                "api_request_failed",
                level=logging.ERROR,
                operation=operation,
                latency_ms=round((time.perf_counter() - started) * 1_000, 2),
                status=500,
                error_type=type(exc).__name__,
            )
            raise
        finally:
            request_id_context.reset(request_token)

    @app.exception_handler(ServiceError)
    async def service_error_handler(request: Request, exc: ServiceError) -> JSONResponse:
        error = ErrorResponse(
            code=exc.code,
            message=str(exc),
            details=json_safe(exc.details) if exc.details else None,
            request_id=getattr(request.state, "request_id", None),
        )
        return JSONResponse(status_code=exc.status_code, content=error.model_dump(mode="json", exclude_none=True))

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        error = ErrorResponse(
            code="request_validation_error",
            message="The request does not match the API contract.",
            details={"errors": json_safe(exc.errors())},
            request_id=getattr(request.state, "request_id", None),
        )
        return JSONResponse(status_code=422, content=error.model_dump(mode="json", exclude_none=True))


    version_prefix = "/api/v1"
    v2_prefix = "/api/v2"
    app.include_router(auth.router, prefix=version_prefix)
    app.include_router(auth_v2.router, prefix=v2_prefix)
    app.include_router(workspace.router, prefix=version_prefix)
    app.include_router(production_data.router, prefix=version_prefix)
    app.include_router(analysis.router, prefix=version_prefix)
    app.include_router(agent.router, prefix=version_prefix)
    app.include_router(properties.router, prefix=version_prefix, dependencies=[Depends(require_legacy_domain_access)])
    app.include_router(data.router, prefix=version_prefix, dependencies=[Depends(require_legacy_domain_access)])
    app.include_router(market.router, prefix=version_prefix, dependencies=[Depends(require_legacy_domain_access)])
    app.include_router(analytics.router, prefix=version_prefix, dependencies=[Depends(require_legacy_domain_access)])
    app.include_router(portfolio.router, prefix=version_prefix, dependencies=[Depends(require_legacy_domain_access)])
    app.include_router(forecast.router, prefix=version_prefix, dependencies=[Depends(require_legacy_domain_access)])

    def health() -> HealthResponse:
        """Liveness only: no database, model, provider, or file dependency."""
        return HealthResponse()

    async def ready() -> ReadinessResponse:
        """Readiness: the production source-of-truth database accepts a query."""
        await get_control_plane_service().readiness()
        return ReadinessResponse(checks={"database": "ok"})

    async def supabase_ready(
        service = Depends(get_supabase_control_plane_service),
    ) -> ReadinessResponse:
        """Readiness for the isolated Supabase Auth v2 implementation."""
        await service.readiness()
        return ReadinessResponse(checks={"database": "ok", "supabase_auth": "ok"})

    app.add_api_route("/health", health, methods=["GET"], response_model=HealthResponse, tags=["health"])
    app.add_api_route("/ready", ready, methods=["GET"], response_model=ReadinessResponse, tags=["health"])
    app.add_api_route(f"{version_prefix}/health", health, methods=["GET"], response_model=HealthResponse, tags=["health"])
    app.add_api_route(f"{version_prefix}/ready", ready, methods=["GET"], response_model=ReadinessResponse, tags=["health"])
    app.add_api_route(f"{v2_prefix}/ready", supabase_ready, methods=["GET"], response_model=ReadinessResponse, tags=["health"])
    return app


app = create_app()