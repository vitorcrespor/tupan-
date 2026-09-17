"""Project published H3 aggregates into typed, dated market observations.

This module runs only in the platform publisher. It deliberately consumes
already-calculated H3 cells and never reads tenant estates or recomputes
market heat in an HTTP request. The resulting rows give city/global cards
and H3 history one authoritative, unit-labelled source.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from math import isfinite
from typing import Any, Iterable, Mapping


SOURCE_NAME = "platform_h3_market_snapshot_v1"


def market_snapshot_observations(
    aggregates: Iterable[Mapping[str, Any]],
    *,
    observed_on: date,
    source_reference: str,
) -> list[dict[str, Any]]:
    """Return global, city/area and H3 observations for one publication.

    Prices and DOM are inventory-weighted means of their published H3 cell
    means. Heat is an inventory-weighted mean over cells with observed sale
    support. Price growth is weighted by recent observed sale count. Sales
    velocity is additive because each H3 cell represents a disjoint count of
    observed sales per day. Missing cell metrics are omitted, never coerced
    to zero.
    """
    cells = [dict(row) for row in aggregates]
    scopes: dict[tuple[str | None, str | None, str | None], list[dict[str, Any]]] = defaultdict(list)
    for cell in cells:
        scopes[(None, None, None)].append(cell)
        city = _label(cell.get("city"))
        area = _label(cell.get("area"))
        if city is not None:
            scopes[(city, None, None)].append(cell)
        if city is not None and area is not None:
            scopes[(city, area, None)].append(cell)
        h3_index = _label(cell.get("h3_index"))
        if h3_index is not None:
            # H3 history is queried directly by its index. Do not mix its
            # city/area label into that exact API scope.
            scopes[(None, None, h3_index)].append(cell)

    observations: list[dict[str, Any]] = []
    for (city, area, h3_index), scoped_cells in scopes.items():
        observations.extend(_scope_observations(
            scoped_cells, city=city, area=area, h3_index=h3_index, observed_on=observed_on,
            source_reference=source_reference,
        ))
    return observations


def _scope_observations(
    cells: list[dict[str, Any]],
    *,
    city: str | None,
    area: str | None,
    h3_index: str | None,
    observed_on: date,
    source_reference: str,
) -> list[dict[str, Any]]:
    inventory = [_number((cell.get("metrics") or {}).get("inventory")) for cell in cells]
    inventory = [value for value in inventory if value is not None]
    metrics = {
        "active_listings": _sum(inventory),
        "price_m2": _weighted_cell_mean(cells, "average_price_m2", "inventory"),
        "asking_price": _weighted_cell_mean(cells, "average_asking_price", "inventory"),
        "dom": _weighted_cell_mean(cells, "average_dom_days", "inventory"),
        "market_heat": _weighted_cell_mean(cells, "market_heat", "inventory"),
        "price_growth": _weighted_cell_mean(
            cells,
            "price_growth",
            "heat_recent_sales",
            allow_negative=True,
        ),
        "sales_velocity": _sum_cell_metric(cells, "sales_velocity"),
    }
    units = {
        "active_listings": "count", "price_m2": "BRL/m²", "asking_price": "BRL",
        "dom": "days", "market_heat": "score_0_100", "price_growth": "percent",
        "sales_velocity": "sales/day",
    }
    observations = [
        {
            "metric": metric, "value": value, "unit": units[metric],
            "observed_on": observed_on,
            "city": city, "area": area, "h3_index": h3_index,
            "source_name": SOURCE_NAME, "source_reference": source_reference,
        }
        for metric, value in metrics.items()
        if value is not None
    ]
    # A survival curve is a property of one exact H3 population. Do not take
    # means of cell probabilities to invent city/global liquidity. Each
    # horizon remains a separate historical dimension.
    if h3_index is not None and len(cells) == 1:
        liquidity = (cells[0].get("metrics") or {}).get("liquidity_by_horizon") or {}
        if isinstance(liquidity, Mapping):
            for raw_horizon, raw_details in liquidity.items():
                details = raw_details if isinstance(raw_details, Mapping) else {}
                score = _number(details.get("score"))
                try:
                    horizon = int(raw_horizon)
                except (TypeError, ValueError):
                    continue
                if score is None or horizon < 1:
                    continue
                observations.append({
                    "metric": "liquidity", "value": score, "unit": "score_0_100",
                    "observed_on": observed_on,
                    "city": None, "area": None, "h3_index": h3_index,
                    "source_name": SOURCE_NAME, "source_reference": source_reference,
                    "dimensions": {"liquidity_horizon_days": horizon},
                })
    return observations


def _weighted_cell_mean(
    cells: Iterable[Mapping[str, Any]],
    metric: str,
    weight_key: str,
    *,
    allow_negative: bool = False,
) -> float | None:
    weighted_total = 0.0
    weight_total = 0.0
    for cell in cells:
        values = cell.get("metrics") or {}
        value = _number(values.get(metric), allow_negative=allow_negative)
        weight = _number(values.get(weight_key))
        if value is None or weight is None or weight <= 0:
            continue
        weighted_total += value * weight
        weight_total += weight
    return round(weighted_total / weight_total, 6) if weight_total else None


def _sum_cell_metric(cells: Iterable[Mapping[str, Any]], metric: str) -> float | None:
    values = [_number((cell.get("metrics") or {}).get(metric)) for cell in cells]
    present = [value for value in values if value is not None]
    return round(sum(present), 6) if present else None


def _sum(values: Iterable[float]) -> float | None:
    values = list(values)
    return round(sum(values), 6) if values else None


def _number(value: Any, *, allow_negative: bool = False) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(number):
        return None
    if number < 0 and not allow_negative:
        return None
    return number


def _label(value: Any) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None
