"""Deterministic, offline-trained listing-liquidity survival model.

``liquidity_score`` is the conditional probability that an active listing
leaves the market during the caller's selected horizon.  It is deliberately
not a demand proxy and it is not inferred by an LLM:

    100 * (1 - S(age + T | X, M) / S(age | X, M))

``X`` is the property type and ``M`` is the geographic market segment.  The
model uses a Kaplan-Meier curve with right-censoring for active listings.  It
falls back from neighbourhood/type to city/type, city, and finally the global
market only when the more specific stratum lacks support.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from math import isfinite
from typing import Any, Iterable, Mapping, Sequence


MODEL_VERSION = "kaplan-meier-listing-liquidity-v1"
H3_MODEL_VERSION = "kaplan-meier-h3-liquidity-v1"
SCHEMA_VERSION = 1
DEFAULT_MIN_OBSERVATIONS = 20
DEFAULT_MIN_EVENTS = 3
PUBLISHED_HORIZONS_DAYS = (30, 60, 90, 180, 365)


@dataclass(frozen=True)
class LiquidityScore:
    score: float | None
    status: str
    horizon_days: int | None
    model_version: str | None
    support_observations: int | None = None
    support_events: int | None = None
    stratum: str | None = None


def attach_h3_liquidity(
    aggregates: Iterable[Mapping[str, Any]],
    rows: Iterable[Mapping[str, Any]],
    *,
    h3_resolution: int,
    as_of: date,
    horizons_days: Sequence[int] = PUBLISHED_HORIZONS_DAYS,
    min_observations: int = DEFAULT_MIN_OBSERVATIONS,
    min_events: int = DEFAULT_MIN_EVENTS,
) -> list[dict[str, Any]]:
    """Attach exact-cell survival estimates to already-built H3 aggregates.

    Sold listings are events and active listings are right-censored. A cell
    never borrows another cell's curve; choosing a coarser H3 resolution is
    the explicit way to request a broader population. The returned payload is
    aggregate-only and is safe for the platform publisher to persist.
    """
    if not 0 <= h3_resolution <= 15:
        raise ValueError("h3_resolution must be between 0 and 15")
    horizons = tuple(dict.fromkeys(int(value) for value in horizons_days))
    if not horizons or any(value < 1 or value > 3_650 for value in horizons):
        raise ValueError("published liquidity horizons must be between 1 and 3650 days")
    if min_observations < 1 or min_events < 1:
        raise ValueError("minimum survival support must be positive")
    try:
        import h3
    except ImportError as exc:  # pragma: no cover - deployment dependency
        raise RuntimeError("The H3 dependency is unavailable to calculate liquidity") from exc

    grouped: dict[str, list[tuple[int, bool]]] = {}
    for row in rows:
        latitude = _coordinate(row.get("latitude"), minimum=-90, maximum=90)
        longitude = _coordinate(row.get("longitude"), minimum=-180, maximum=180)
        observation = _observation(row, as_of)
        if latitude is None or longitude is None or observation is None:
            continue
        cell = _h3_cell(h3, latitude, longitude, h3_resolution)
        duration, event, *_ = observation
        grouped.setdefault(cell, []).append((duration, event))

    result: list[dict[str, Any]] = []
    for source in aggregates:
        row = dict(source)
        metrics = dict(row.get("metrics") or {})
        units = dict(metrics.get("units") or {})
        units["liquidity"] = "score_0_100"
        values = grouped.get(str(row.get("h3_index")), [])
        event_count = sum(event for _, event in values)
        supported = len(values) >= min_observations and event_count >= min_events
        curve = _kaplan_meier_curve(values) if supported else []
        by_horizon: dict[str, dict[str, Any]] = {}
        for horizon in horizons:
            score = round((1.0 - _survival_at(curve, horizon)) * 100.0, 1) if supported else None
            by_horizon[str(horizon)] = {
                "score": score,
                "status": "available" if supported else "insufficient_evidence",
                "horizon_days": horizon,
                "observation_count": len(values) if supported else None,
                "sale_event_count": event_count if supported else None,
                "model_version": H3_MODEL_VERSION,
                "as_of": as_of.isoformat(),
            }
        metrics.update({
            "liquidity_by_horizon": by_horizon,
            "liquidity_model_version": H3_MODEL_VERSION,
            "units": units,
        })
        row["metrics"] = metrics
        result.append(row)
    return result


def train_liquidity_survival_model(
    rows: Iterable[Mapping[str, Any]],
    *,
    as_of: date | None = None,
    min_observations: int = DEFAULT_MIN_OBSERVATIONS,
    min_events: int = DEFAULT_MIN_EVENTS,
) -> dict[str, Any]:
    """Build a JSON-serializable Kaplan-Meier artifact from trusted listings.

    Sold listings are events; active listings are right-censored at their
    observed age.  No tenant identifier, address, or raw listing is retained
    in the artifact.
    """
    if min_observations < 1 or min_events < 1:
        raise ValueError("minimum survival support must be positive")
    trained_as_of = as_of or date.today()
    observations = [_observation(row, trained_as_of) for row in rows]
    observations = [item for item in observations if item is not None]
    grouped: dict[tuple[str, ...], list[tuple[int, bool]]] = {}
    for observation in observations:
        duration, event, city, area, property_type = observation
        for key in _strata(city, area, property_type):
            grouped.setdefault(key, []).append((duration, event))

    strata = []
    for key, values in grouped.items():
        event_count = sum(event for _, event in values)
        if len(values) < min_observations or event_count < min_events:
            continue
        strata.append({
            "key": list(key),
            "observation_count": len(values),
            "event_count": event_count,
            "curve": _kaplan_meier_curve(values),
        })

    return {
        "schema_version": SCHEMA_VERSION,
        "model_version": MODEL_VERSION,
        "trained_as_of": trained_as_of.isoformat(),
        "source_observation_count": len(observations),
        "event_count": sum(event for _, event, *_ in observations),
        "min_observations": min_observations,
        "min_events": min_events,
        "strata": strata,
    }


def score_listing_liquidity(
    artifact: Mapping[str, Any] | None,
    estate: Mapping[str, Any],
    *,
    horizon_days: int | None,
    as_of: date | None = None,
) -> LiquidityScore:
    """Score an authorized active estate for the explicitly selected horizon."""
    if horizon_days is None:
        return LiquidityScore(None, "horizon_not_selected", None, _model_version(artifact))
    if not 1 <= horizon_days <= 3_650:
        raise ValueError("liquidity horizon must be between 1 and 3650 days")
    if estate.get("status") != "active":
        return LiquidityScore(None, "not_active", horizon_days, _model_version(artifact))
    age = _listing_age(estate, as_of or date.today())
    if age is None:
        return LiquidityScore(None, "missing_listing_duration", horizon_days, _model_version(artifact))
    if not _valid_artifact(artifact):
        return LiquidityScore(None, "model_unavailable", horizon_days, None)

    stratum = _find_supported_stratum(artifact, estate)
    if stratum is None:
        return LiquidityScore(None, "insufficient_evidence", horizon_days, _model_version(artifact))
    survival_at_age = _survival_at(stratum["curve"], age)
    survival_at_horizon = _survival_at(stratum["curve"], age + horizon_days)
    if survival_at_age <= 0:
        return LiquidityScore(None, "insufficient_evidence", horizon_days, _model_version(artifact))

    probability = 1 - (survival_at_horizon / survival_at_age)
    score = round(max(0.0, min(1.0, probability)) * 100, 1)
    return LiquidityScore(
        score,
        "available",
        horizon_days,
        _model_version(artifact),
        _int_or_none(stratum.get("observation_count")),
        _int_or_none(stratum.get("event_count")),
        _stratum_label(stratum.get("key")),
    )


def summarize_portfolio_liquidity(
    rows: Iterable[Mapping[str, Any]],
    *,
    horizon_days: int | None,
    as_of: date | None = None,
    min_observations: int = DEFAULT_MIN_OBSERVATIONS,
    min_events: int = DEFAULT_MIN_EVENTS,
) -> dict[str, Any]:
    """Score a portfolio from its *own* listing and sale history.

    This intentionally does not borrow events from similar properties, other
    portfolios, or the platform-wide liquidity artifact.  Sold portfolio
    records are events and active portfolio records are right-censored.  The
    returned score is the mean conditional probability that the currently
    active, duration-known listings leave the market within ``horizon_days``.
    """
    snapshot_date = as_of or date.today()
    records = [dict(row) for row in rows if row.get("status") in {"active", "sold"}]
    observations = [
        row for row in records
        if _observation(row, snapshot_date) is not None
    ]
    active = [row for row in records if row.get("status") == "active"]
    event_count = sum(
        1 for row in observations
        if row.get("status") == "sold"
    )
    base = {
        "score": None,
        "horizon_days": horizon_days,
        "active_estate_count": len(active),
        "eligible_estate_count": 0,
        "observed_estate_count": len(observations),
        "sale_event_count": event_count,
        "model_version": MODEL_VERSION,
    }
    if horizon_days is None:
        return {**base, "status": "horizon_not_selected"}
    if not 1 <= horizon_days <= 3_650:
        raise ValueError("liquidity horizon must be between 1 and 3650 days")
    if not active:
        return {**base, "status": "no_active_listings"}

    # Blank strata force the model to use the portfolio-wide curve only.  It
    # prevents the per-estate scorer from looking for a similar-property stratum.
    portfolio_rows = (
        {**row, "city": None, "area": None, "property_type": None}
        for row in records
    )
    artifact = train_liquidity_survival_model(
        portfolio_rows,
        as_of=snapshot_date,
        min_observations=min_observations,
        min_events=min_events,
    )
    scores = [
        score_listing_liquidity(
            artifact,
            {**estate, "city": None, "area": None, "property_type": None},
            horizon_days=horizon_days,
            as_of=snapshot_date,
        )
        for estate in active
    ]
    eligible = [item for item in scores if item.status == "available" and item.score is not None]
    if eligible:
        return {
            **base,
            "score": round(sum(item.score for item in eligible) / len(eligible), 1),
            "status": "available",
            "eligible_estate_count": len(eligible),
        }
    status = next(
        (item.status for item in scores if item.status != "missing_listing_duration"),
        "missing_listing_duration",
    )
    return {**base, "status": status}


def _observation(row: Mapping[str, Any], as_of: date) -> tuple[int, bool, str, str, str] | None:
    status = row.get("status")
    if status not in {"active", "sold"}:
        return None
    duration = _listing_age(row, as_of, sold=status == "sold")
    if duration is None:
        return None
    return duration, status == "sold", _label(row.get("city")), _label(row.get("area")), _label(row.get("property_type"))


def _listing_age(row: Mapping[str, Any], as_of: date, *, sold: bool = False) -> int | None:
    days_on_market = _number(row.get("days_on_market"))
    if days_on_market is not None:
        return max(0, round(days_on_market))
    listed_since = _as_date(row.get("listed_since"))
    if listed_since is None:
        return None
    end_date = _as_date(row.get("last_sale_date")) if sold else as_of
    if end_date is None:
        return None
    return max(0, (end_date - listed_since).days)


def _strata(city: str, area: str, property_type: str) -> tuple[tuple[str, ...], ...]:
    keys: list[tuple[str, ...]] = []
    if city and area and property_type:
        keys.append(("city_area_type", city, area, property_type))
    if city and property_type:
        keys.append(("city_type", city, property_type))
    if city:
        keys.append(("city", city))
    keys.append(("global",))
    return tuple(keys)


def _kaplan_meier_curve(values: list[tuple[int, bool]]) -> list[list[float]]:
    """Return event-time survival probabilities, treating active rows as censored."""
    curve: list[list[float]] = []
    survival = 1.0
    for time in sorted({duration for duration, event in values if event}):
        at_risk = sum(duration >= time for duration, _ in values)
        events = sum(duration == time and event for duration, event in values)
        if at_risk <= 0 or events <= 0:
            continue
        survival *= 1 - (events / at_risk)
        curve.append([float(time), round(max(0.0, survival), 12)])
    return curve


def _find_supported_stratum(artifact: Mapping[str, Any], estate: Mapping[str, Any]) -> Mapping[str, Any] | None:
    available = {
        tuple(item.get("key") or ()): item
        for item in artifact.get("strata", [])
        if isinstance(item, Mapping) and isinstance(item.get("curve"), list)
    }
    for key in _strata(_label(estate.get("city")), _label(estate.get("area")), _label(estate.get("property_type"))):
        item = available.get(key)
        if item is not None:
            return item
    return None


def _survival_at(curve: Any, time: int) -> float:
    survival = 1.0
    if not isinstance(curve, list):
        return survival
    for point in curve:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            continue
        event_time, value = _number(point[0]), _number(point[1])
        if event_time is None or value is None or event_time > time:
            continue
        survival = value
    return max(0.0, min(1.0, survival))


def _valid_artifact(artifact: Mapping[str, Any] | None) -> bool:
    return bool(
        isinstance(artifact, Mapping)
        and artifact.get("schema_version") == SCHEMA_VERSION
        and artifact.get("model_version") == MODEL_VERSION
        and isinstance(artifact.get("strata"), list)
    )


def _model_version(artifact: Mapping[str, Any] | None) -> str | None:
    return artifact.get("model_version") if isinstance(artifact, Mapping) and isinstance(artifact.get("model_version"), str) else None


def _label(value: Any) -> str:
    return str(value).strip().casefold() if value is not None and str(value).strip() else ""


def _stratum_label(key: Any) -> str | None:
    return "/".join(str(part) for part in key) if isinstance(key, list) else None


def _number(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if isfinite(parsed) and parsed >= 0 else None


def _int_or_none(value: Any) -> int | None:
    number = _number(value)
    return int(number) if number is not None else None


def _as_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            return None
    return None


def _coordinate(value: Any, *, minimum: float, maximum: float) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if isfinite(parsed) and minimum <= parsed <= maximum else None


def _h3_cell(h3: Any, latitude: float, longitude: float, resolution: int) -> str:
    if hasattr(h3, "latlng_to_cell"):
        return str(h3.latlng_to_cell(latitude, longitude, resolution))
    return str(h3.geo_to_h3(latitude, longitude, resolution))
