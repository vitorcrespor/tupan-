from __future__ import annotations

import os
from functools import lru_cache

from pydantic import BaseModel, Field

from backend.services.agent import AgentService
from backend.services.forecast import ForecastService
from backend.services.market import MarketService
from backend.services.portfolio import PortfolioService
from backend.services.property import PropertyService


class ApiSettings(BaseModel):
    cors_origins: list[str] = Field(default_factory=lambda: [
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:4173", "http://127.0.0.1:4173",
    ])
    allow_mock_data: bool = False

    @classmethod
    def from_environment(cls) -> "ApiSettings":
        configured_origins = os.getenv("API_CORS_ORIGINS", "")
        origins = [origin.strip() for origin in configured_origins.split(",") if origin.strip()]
        allow_mock_data = os.getenv("API_ALLOW_MOCK_DATA", "false").strip().lower() in {"1", "true", "yes"}
        return cls(cors_origins=origins or cls().cors_origins, allow_mock_data=allow_mock_data)


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
def get_agent_service() -> AgentService:
    return AgentService()
