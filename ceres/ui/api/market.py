from __future__ import annotations

from typing import Any, Mapping

from ui.api.client import ApiClient, get_api_client
from ui.api.types import H3Cell, MarketCells, MarketIntelligence, MarketOverview, MarketRegion


def get_market_overview(*, client: ApiClient | None = None) -> MarketOverview:
    return MarketOverview.from_json((client or get_api_client()).get("market/overview"))


def get_market_cells(
    filters: Mapping[str, Any] | None = None,
    *,
    client: ApiClient | None = None,
) -> MarketCells:
    return MarketCells.from_json((client or get_api_client()).get("market/cells", query=filters))


def get_market_region(
    h3_index: str,
    filters: Mapping[str, Any] | None = None,
    *,
    client: ApiClient | None = None,
) -> MarketRegion:
    return MarketRegion.from_json((client or get_api_client()).get(f"market/regions/{h3_index}", query=filters))


def get_market_intelligence(
    controls: Mapping[str, Any],
    *,
    client: ApiClient | None = None,
) -> MarketIntelligence:
    return MarketIntelligence.from_json((client or get_api_client()).post("analytics/market-intelligence", body=controls))
