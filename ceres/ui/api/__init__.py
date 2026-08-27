"""Reusable HTTP integration layer for the Tupan desktop frontend."""

from ui.api.agent import get_agent_traces, send_agent_message
from ui.api.client import ApiClient, get_api_client
from ui.api.forecast import request_forecast
from ui.api.market import get_market_cells, get_market_intelligence, get_market_overview, get_market_region
from ui.api.metrics import get_metric_history, get_metrics
from ui.api.portfolio import analyse_portfolio, get_portfolio_analytics
from ui.api.properties import (
    create_property,
    get_property,
    get_property_valuation,
    get_properties,
    import_properties,
    search_properties,
)

__all__ = [
    "ApiClient",
    "analyse_portfolio",
    "create_property",
    "get_agent_traces",
    "get_api_client",
    "get_market_cells",
    "get_market_intelligence",
    "get_market_overview",
    "get_market_region",
    "get_metric_history",
    "get_metrics",
    "get_portfolio_analytics",
    "get_properties",
    "get_property",
    "get_property_valuation",
    "import_properties",
    "request_forecast",
    "search_properties",
    "send_agent_message",
]
