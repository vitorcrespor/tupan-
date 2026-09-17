"""Pure, global H3 market-heat calculation for offline publication.

This is the serving-safe successor to the legacy object-mutating
``radar.data_base.metrics.calculate_market_heat`` helper.  It preserves its
spatial-intensity × market-momentum structure while using only aggregated
platform inputs.  It never receives a tenant context, estate identifier or
portfolio object and never mutates its inputs.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from math import exp, isfinite, log1p, tanh
from statistics import median
from typing import Any, Mapping, Sequence


INPUT_VERSION = "platform-global-market-heat-v1"
RECENT_SALES_DAYS = 60
REFERENCE_WINDOW_START_DAYS = 365
REFERENCE_WINDOW_END_DAYS = 425
MIN_SALES_PER_WINDOW = 3


def calculate_market_heat(
    aggregates: Sequence[Mapping[str, Any]],
    sales: Sequence[Mapping[str, Any]],
    *,
    h3_resolution: int,
    as_of: date,
) -> list[dict[str, Any]]:
    """Attach observed, resolution-specific heat indicators to H3 aggregates.

    ``spatial_heat_L`` is the legacy local-neighborhood intensity motif:
    inventory in the cell plus decayed first/second H3 rings. ``market_momentum``
    is derived from global, aggregate-only observed sale acceleration and price
    change for the same cell. A heat score is published only when both sale
    windows meet the minimum evidence requirement; a missing score is never
    represented as zero.
    """
    if not 0 <= h3_resolution <= 15:
        raise ValueError("h3_resolution must be between 0 and 15")
    try:
        import h3
    except ImportError as exc:  # pragma: no cover - deployment dependency
        raise RuntimeError("The H3 dependency is unavailable to calculate market heat") from exc

    inventory = {
        str(row["h3_index"]): _nonnegative((row.get("metrics") or {}).get("inventory")) or 0.0
        for row in aggregates
    }
    sales_by_cell = _sales_by_cell(h3, sales, h3_resolution)
    result: list[dict[str, Any]] = []
    for source in aggregates:
        row = dict(source)
        cell = str(row["h3_index"])
        metrics = dict(row.get("metrics") or {})
        spatial = _spatial_intensity(h3, cell, inventory)
        momentum = _observed_momentum(sales_by_cell.get(cell, []), as_of=as_of)
        units = dict(metrics.get("units") or {})
        units.update({
            "spatial_heat_L": "score_0_1",
            "market_momentum": "score_0_1",
            "market_heat": "score_0_100",
            "sales_velocity": "sales/day",
            "price_growth": "percent",
            "heat_recent_sales": "count",
            "heat_reference_sales": "count",
        })
        metrics.update({
            "source_name": "platform_global_observed_market_v1",
            "heat_resolution": h3_resolution,
            "spatial_heat_L": spatial,
            "market_momentum": momentum["score"],
            "market_heat": None if momentum["score"] is None else round(spatial * momentum["score"] * 100, 4),
            "sales_velocity": momentum["sales_velocity"],
            "price_growth": momentum["price_growth"],
            "heat_recent_sales": momentum["recent_count"],
            "heat_reference_sales": momentum["reference_count"],
            "market_heat_status": momentum["status"],
            "units": units,
        })
        row["metrics"] = metrics
        result.append(row)
    return result


def _sales_by_cell(h3: Any, sales: Sequence[Mapping[str, Any]], resolution: int) -> dict[str, list[tuple[date, float]]]:
    result: dict[str, list[tuple[date, float]]] = defaultdict(list)
    for sale in sales:
        latitude, longitude = _finite(sale.get("latitude")), _finite(sale.get("longitude"))
        observed_on, price = _date(sale.get("last_sale_date")), _finite(sale.get("last_sale_price"))
        if latitude is None or longitude is None or observed_on is None or price is None or price <= 0:
            continue
        result[_cell(h3, latitude, longitude, resolution)].append((observed_on, price))
    return result


def _observed_momentum(sales: Sequence[tuple[date, float]], *, as_of: date) -> dict[str, Any]:
    recent_start = as_of - timedelta(days=RECENT_SALES_DAYS - 1)
    reference_start = as_of - timedelta(days=REFERENCE_WINDOW_END_DAYS)
    reference_end = as_of - timedelta(days=REFERENCE_WINDOW_START_DAYS)
    recent = [price for observed_on, price in sales if recent_start <= observed_on <= as_of]
    reference = [price for observed_on, price in sales if reference_start <= observed_on <= reference_end]
    base = {
        "recent_count": len(recent), "reference_count": len(reference),
        "sales_velocity": len(recent) / RECENT_SALES_DAYS if recent else None,
        "price_growth": None, "score": None,
    }
    if len(recent) < MIN_SALES_PER_WINDOW or len(reference) < MIN_SALES_PER_WINDOW:
        return {**base, "status": "insufficient_observed_sale_support"}
    reference_price = median(reference)
    if reference_price <= 0:
        return {**base, "status": "invalid_reference_sale_price"}
    price_growth = ((median(recent) / reference_price) - 1.0) * 100.0
    acceleration = tanh((len(recent) - len(reference)) / max(len(reference), 1))
    growth_signal = tanh(price_growth / 20.0)
    # Both terms are bounded in [-1, 1], preserving the legacy momentum role
    # without substituting an unavailable property-level forecast.
    score = max(0.0, min(1.0, (1.0 + 0.6 * acceleration + 0.4 * growth_signal) / 2.0))
    return {**base, "price_growth": round(price_growth, 6), "score": score, "status": "available"}


def _spatial_intensity(h3: Any, cell: str, inventory: Mapping[str, float]) -> float:
    weighted = inventory.get(cell, 0.0)
    for distance in (1, 2):
        decay = exp(-0.5 * distance)
        weighted += decay * sum(inventory.get(neighbor, 0.0) for neighbor in _ring(h3, cell, distance))
    # Equivalent to the legacy sigmoid(log1p(local influence)) but returns a
    # scalar per cell rather than mutating estate records.
    value = log1p(max(weighted, 0.0))
    return 1.0 / (1.0 + exp(-value))


def _ring(h3: Any, cell: str, distance: int) -> set[str]:
    if hasattr(h3, "grid_ring"):
        return {str(item) for item in h3.grid_ring(cell, distance)}
    return {str(item) for item in h3.k_ring(cell, distance)} - {cell}


def _cell(h3: Any, latitude: float, longitude: float, resolution: int) -> str:
    if hasattr(h3, "latlng_to_cell"):
        return str(h3.latlng_to_cell(latitude, longitude, resolution))
    return str(h3.geo_to_h3(latitude, longitude, resolution))


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _nonnegative(value: Any) -> float | None:
    number = _finite(value)
    return number if number is not None and number >= 0 else None


def _date(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None
