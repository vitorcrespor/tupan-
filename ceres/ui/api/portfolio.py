from __future__ import annotations

from typing import Any, Mapping, Sequence

from ui.api.client import ApiClient, get_api_client
from ui.api.types import PortfolioAnalytics, PropertyPayload


def get_portfolio_analytics(*, client: ApiClient | None = None) -> PortfolioAnalytics:
    return PortfolioAnalytics.from_json((client or get_api_client()).get("portfolio/analytics"))


def analyse_portfolio(
    properties: Sequence[PropertyPayload],
    *,
    sold_properties: Sequence[Mapping[str, Any]] = (),
    target_commission: float | None = None,
    client: ApiClient | None = None,
) -> PortfolioAnalytics:
    response = (client or get_api_client()).post(
        "portfolio/analytics",
        body={
            "properties": [dict(property_) for property_ in properties],
            "sold_properties": [dict(property_) for property_ in sold_properties],
            "target_commission": target_commission,
        },
    )
    return PortfolioAnalytics.from_json(response)
