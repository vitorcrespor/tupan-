from __future__ import annotations

import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api.dependencies import get_settings
from backend.api.routes import agent, analytics, data, forecast, market, portfolio, properties
from backend.api.schemas.common import ErrorResponse, HealthResponse
from backend.services.errors import ServiceError
from backend.services.serialization import json_safe


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Tupan API",
        version="1.0.0",
        description="Thin HTTP/JSON transport layer over the existing Tupan domain services.",
        openapi_url="/api/v1/openapi.json",
        docs_url="/api/v1/docs",
        redoc_url="/api/v1/redoc",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_id(request: Request, call_next):
        request.state.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

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
    app.include_router(properties.router, prefix=version_prefix)
    app.include_router(data.router, prefix=version_prefix)
    app.include_router(market.router, prefix=version_prefix)
    app.include_router(analytics.router, prefix=version_prefix)
    app.include_router(portfolio.router, prefix=version_prefix)
    app.include_router(forecast.router, prefix=version_prefix)
    app.include_router(agent.router, prefix=version_prefix)

    @app.get(f"{version_prefix}/health", response_model=HealthResponse, tags=["health"])
    def health() -> HealthResponse:
        """Liveness check; dependencies remain lazily initialized by domain routes."""
        return HealthResponse()

    return app


app = create_app()
