"""Normalize existing published metrics without synthesizing market scores.

One geography, one producer per metric. Observations from different producers
or geographic scopes are not averaged. Unit ambiguity fails closed.
"""
from collections import defaultdict
from math import isfinite
from typing import Any

from backend.api.schemas.published_metrics import PublishedMetric, PublishedMetricPoint, PublishedMarketResponse

# Units are explicit API conventions, not new definitions of domain metrics.
METRIC_UNITS = {
    'price_m2': 'BRL/m²', 'asking_price': 'BRL', 'active_listings': 'count',
    'dom': 'days', 'market_heat': 'score_0_100',
    'liquidity': 'score_0_100', 'price_growth': 'percent',
    'sales_velocity': 'sales/day',
}


def normalize_metric_value(metric: str, value: Any, unit: str | None) -> tuple[float | None, str | None]:
    expected = METRIC_UNITS[metric]
    try:
        number = float(value)
    except (ValueError, TypeError):
        return None, 'missing_value'
    if isinstance(value, bool) or not isfinite(number):
        return None, 'invalid_value'
    aliases = {'BRL/m2': 'BRL/m²', 'dias': 'days', 'day': 'days', '%': 'percent'}
    unit = aliases.get(unit, unit)
    if expected == 'score_0_100' and unit == 'score_0_1':
        number *= 100
    elif expected == 'percent' and unit == 'fraction':
        number *= 100
    elif unit != expected:
        return None, 'incompatible_or_missing_unit'
    if (expected == 'score_0_100' and not 0 <= number <= 100
            or expected not in {'percent', 'score_0_100'} and number < 0
            or expected == 'count' and not number.is_integer()):
        return None, 'invalid_value'
    return number, None


def published_market_response(
    rows: list[dict[str, Any]],
    *,
    city=None,
    area=None,
    h3_index=None,
    liquidity_horizon_days: int | None = None,
) -> PublishedMarketResponse:
    grouped = defaultdict(list)
    for row in rows:
        if row['metric'] in METRIC_UNITS:
            grouped[row['metric']].append(row)
    metrics = []
    for metric, unit in METRIC_UNITS.items():
        observations = grouped[metric]
        sources = {row['source_name'] for row in observations}
        if not observations or len(sources) != 1:
            metrics.append(PublishedMetric(metric=metric, unit=unit, status='unavailable',
                horizon_days=liquidity_horizon_days if metric == 'liquidity' else None,
                reason='no_published_observations' if not observations else 'conflicting_providers'))
            continue
        # Repository supplies one revision per date, ordered oldest to newest.
        points = []
        for row in observations:
            value, reason = normalize_metric_value(metric, row['value'], row.get('unit'))
            points.append(PublishedMetricPoint(period=row['observed_on'], value=value, reason=reason))
        latest = points[-1]
        metrics.append(PublishedMetric(metric=metric, unit=unit, value=latest.value,
            observed_on=latest.period, source_name=next(iter(sources)), points=points,
            horizon_days=liquidity_horizon_days if metric == 'liquidity' else None,
            status='available' if latest.value is not None else 'unavailable', reason=latest.reason))
    return PublishedMarketResponse(
        city=city, area=area, h3_index=h3_index,
        liquidity_horizon_days=liquidity_horizon_days,
        metrics=metrics,
    )


def published_cell_indicators(
    metrics: dict[str, Any],
    *,
    liquidity_horizon_days: int | None = None,
) -> dict[str, float | None]:
    """Optional modeled cell values require their producer's declared units."""
    units = metrics.get('units') or {}
    if not isinstance(units, dict):
        units = {}
    result = {key: normalize_metric_value(key, metrics.get(key), units.get(key))[0]
              for key in ('market_heat', 'price_growth', 'sales_velocity')}
    details = published_cell_liquidity_details(metrics, liquidity_horizon_days=liquidity_horizon_days)
    result['liquidity'] = details.get('score') if details else None
    return result


def published_cell_liquidity_details(
    metrics: dict[str, Any],
    *,
    liquidity_horizon_days: int | None,
) -> dict[str, Any] | None:
    """Select one precomputed H3 survival horizon without recalculating it."""
    if liquidity_horizon_days is None:
        return None
    values = metrics.get('liquidity_by_horizon') or {}
    if not isinstance(values, dict):
        return None
    details = values.get(str(liquidity_horizon_days))
    return dict(details) if isinstance(details, dict) else None
