from __future__ import annotations

from typing import Any

from ui.api.client import ApiClient, get_api_client
from ui.api.types import Forecast, PropertyPayload


def request_forecast(
    *,
    property_id: str | None = None,
    property_payload: PropertyPayload | None = None,
    time_span_days: int = 30,
    client: ApiClient | None = None,
) -> Forecast:
    response = (client or get_api_client()).post(
        "forecast",
        body={"property_id": property_id, "property": dict(property_payload) if property_payload else None, "time_span_days": time_span_days},
    )
    return Forecast.from_json(response)
