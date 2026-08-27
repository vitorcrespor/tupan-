from __future__ import annotations

from ui.api.client import ApiClient, get_api_client
from ui.api.types import MetricCatalogItem, MetricSeries


def get_metrics(*, client: ApiClient | None = None) -> list[MetricCatalogItem]:
    response = (client or get_api_client()).get("metrics")
    return [MetricCatalogItem.from_json(metric) for metric in response["metrics"]]


def get_metric_history(
    metric: str,
    *,
    city: str | None = None,
    area: str | None = None,
    client: ApiClient | None = None,
) -> MetricSeries:
    response = (client or get_api_client()).get(f"metrics/{metric}/history", query={"city": city, "area": area})
    return MetricSeries.from_json(response)
