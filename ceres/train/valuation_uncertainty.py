"""Quality, interval and comparable-support calculations for AVM output.

These functions never turn a quality score into a fake probability.  They
produce evidence that a separately calibrated product confidence policy can
consume.
"""

from __future__ import annotations

from datetime import datetime, timezone
from math import ceil, exp, isfinite, log, sqrt
from statistics import median
from typing import Any, Iterable, Mapping, Sequence


QUALITY_POLICY_VERSION = "quality-v1"


def _finite(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def assess_data_quality(
    features: Mapping[str, Any],
    lineage: Mapping[str, Mapping[str, Any]],
    valuation_time: datetime,
) -> dict[str, Any]:
    """Score observed, valid, fresh fields with critical reasons and warnings.

    ``quality`` and ``completeness`` are operational scores (0–100), not
    calibrated probabilities. Missing fields and inferred values remain
    visible in the returned evidence.
    """
    if valuation_time.tzinfo is None:
        raise ValueError("valuation_time must include a timezone")
    valuation_time = valuation_time.astimezone(timezone.utc)
    weights = {
        "usable_area_m2": 22, "property_type": 18, "city": 12,
        "latitude": 12, "longitude": 12, "rooms": 8, "bathrooms": 8,
        "parking_spaces": 4, "condition": 4,
    }
    observed = 0.0
    quality_points = 0.0
    missing: list[str] = []
    warnings: list[str] = []
    critical: list[str] = []
    for field, weight in weights.items():
        value = features.get(field)
        is_present = value is not None and value != ""
        if not is_present:
            missing.append(field)
            if field in {"usable_area_m2", "property_type", "city"}:
                critical.append(f"missing_{field}")
            continue
        observed += weight
        field_score = 1.0
        number = _finite(value) if field not in {"property_type", "city", "condition"} else None
        if field not in {"property_type", "city", "condition"} and number is None:
            field_score = 0.0
            warnings.append(f"invalid_{field}")
        if field in {"usable_area_m2"} and number is not None and number <= 0:
            field_score = 0.0
            critical.append("invalid_usable_area_m2")
        source = lineage.get(field)
        if not isinstance(source, Mapping):
            field_score *= 0.5
            warnings.append(f"missing_lineage_{field}")
        else:
            available = source.get("available_at")
            try:
                if isinstance(available, str):
                    available = datetime.fromisoformat(available.replace("Z", "+00:00"))
                if not isinstance(available, datetime) or available.tzinfo is None or available.astimezone(timezone.utc) > valuation_time:
                    field_score = 0.0
                    critical.append(f"future_{field}")
                else:
                    age_days = max(0.0, (valuation_time - available.astimezone(timezone.utc)).total_seconds() / 86_400)
                    field_score *= max(0.4, 1.0 - min(age_days, 730.0) / 2_000.0)
                    if age_days > 365:
                        warnings.append(f"stale_{field}")
            except (TypeError, ValueError):
                field_score = 0.0
                critical.append(f"invalid_lineage_{field}")
        quality_points += weight * field_score
    total = sum(weights.values())
    completeness = observed / total * 100
    quality = quality_points / total * 100
    if "latitude" in missing or "longitude" in missing:
        critical.append("geocode_unresolved")
    return {
        "policy_version": QUALITY_POLICY_VERSION,
        "completeness": round(completeness, 2),
        "quality": round(quality, 2),
        "observed_weight": round(observed, 2),
        "missing_fields": sorted(set(missing)),
        "critical_reasons": sorted(set(critical)),
        "warnings": sorted(set(warnings)),
    }


def _scores(actual_log: Iterable[float], lower_log: Iterable[float], upper_log: Iterable[float]) -> list[float]:
    scores: list[float] = []
    for actual, lower, upper in zip(actual_log, lower_log, upper_log):
        actual, lower, upper = _finite(actual), _finite(lower), _finite(upper)
        if actual is None or lower is None or upper is None:
            continue
        lower, upper = sorted((lower, upper))
        scores.append(max(lower - actual, actual - upper, 0.0))
    if not scores:
        raise ValueError("at least one finite calibration triplet is required")
    return scores


def fit_conformal(
    actual_log: Iterable[float],
    lower_log: Iterable[float],
    upper_log: Iterable[float],
    *,
    level: float = 0.8,
) -> dict[str, float | int]:
    """Fit a finite-sample conformal expansion on an untouched calibration set."""
    if not 0 < level < 1:
        raise ValueError("level must be between zero and one")
    scores = sorted(_scores(actual_log, lower_log, upper_log))
    index = min(len(scores) - 1, max(0, ceil((len(scores) + 1) * level) - 1))
    return {"level": level, "sample_count": len(scores), "nonconformity_quantile": scores[index]}


def conformal_interval(lower_log: float, upper_log: float, calibration: Mapping[str, Any]) -> tuple[float, float]:
    lower, upper = sorted((float(lower_log), float(upper_log)))
    expansion = _finite(calibration.get("nonconformity_quantile"))
    if expansion is None or expansion < 0:
        raise ValueError("calibration has no valid nonconformity quantile")
    return lower - expansion, upper + expansion


def _weighted_median(values: Sequence[float], weights: Sequence[float]) -> float:
    order = sorted(zip(values, weights), key=lambda pair: pair[0])
    cutoff = sum(weights) / 2
    running = 0.0
    for value, weight in order:
        running += weight
        if running >= cutoff:
            return value
    return order[-1][0]


def local_residual_correction(
    subject: Mapping[str, Any],
    comparable_records: Sequence[Mapping[str, Any]],
    *,
    valuation_time: datetime,
) -> dict[str, Any]:
    """Estimate a conservative local residual without using the subject target."""
    if valuation_time.tzinfo is None:
        raise ValueError("valuation_time must include a timezone")
    now = valuation_time.astimezone(timezone.utc)
    subject_id = subject.get("property_id")
    subject_lat, subject_lon, subject_area = map(
        _finite,
        (
            subject.get("latitude"),
            subject.get("longitude"),
            subject.get("usable_area_m2", subject.get("area_m2")),
        ),
    )
    if subject_lat is None or subject_lon is None or subject_area is None or subject_area <= 0:
        return {"correction_log": 0.0, "lambda": 0.0, "effective_n": 0.0, "max_age_days": None, "residual_dispersion": None, "warnings": ["subject_location_or_area_missing"]}
    values: list[float] = []
    weights: list[float] = []
    ages: list[float] = []
    for comparable in comparable_records:
        if comparable.get("oof") is not True or comparable.get("property_id") == subject_id:
            continue
        if comparable.get("listing_cluster_id") and comparable.get("listing_cluster_id") == subject.get("listing_cluster_id"):
            continue
        if comparable.get("kind", comparable.get("property_type")) != subject.get("kind", subject.get("property_type")):
            continue
        if comparable.get("city") != subject.get("city"):
            continue
        comp_time = comparable.get("valuation_time")
        if isinstance(comp_time, str):
            try:
                comp_time = datetime.fromisoformat(comp_time.replace("Z", "+00:00"))
            except ValueError:
                continue
        if not isinstance(comp_time, datetime) or comp_time.tzinfo is None:
            continue
        comp_time = comp_time.astimezone(timezone.utc)
        if comp_time > now:
            continue
        cutoff = comparable.get("prediction_cutoff")
        if isinstance(cutoff, str):
            try:
                cutoff = datetime.fromisoformat(cutoff.replace("Z", "+00:00"))
            except ValueError:
                continue
        if not isinstance(cutoff, datetime) or cutoff.tzinfo is None or cutoff.astimezone(timezone.utc) > comp_time:
            continue
        lat, lon, area, residual = map(
            _finite,
            (
                comparable.get("latitude"),
                comparable.get("longitude"),
                comparable.get("usable_area_m2", comparable.get("area_m2")),
                comparable.get("residual_log"),
            ),
        )
        if lat is None or lon is None or area is None or area <= 0 or residual is None:
            continue
        distance = sqrt(((lat - subject_lat) * 111) ** 2 + ((lon - subject_lon) * 111 * 0.85) ** 2)
        age_days = max(0.0, (now - comp_time).total_seconds() / 86_400)
        area_gap = abs(log(area / subject_area))
        quality = max(0.1, min(1.0, float(comparable.get("quality", 1.0))))
        weight = exp(-distance / 3.0) * exp(-age_days / 365.0) * exp(-area_gap / 0.35) * quality
        if weight <= 1e-5:
            continue
        values.append(residual)
        weights.append(weight)
        ages.append(age_days)
    if not values:
        return {"correction_log": 0.0, "lambda": 0.0, "effective_n": 0.0, "max_age_days": None, "residual_dispersion": None, "warnings": ["no_eligible_comparable_support"]}
    correction = _weighted_median(values, weights)
    effective_n = (sum(weights) ** 2) / sum(weight * weight for weight in weights)
    dispersion = median([abs(value - correction) for value in values])
    support = min(1.0, effective_n / 8.0)
    stability = max(0.0, 1.0 - min(1.0, dispersion / 0.25))
    shrink = support * stability
    warnings = []
    if effective_n < 3:
        warnings.append("thin_comparable_support")
    if dispersion > 0.25:
        warnings.append("contradictory_comparable_residuals")
    return {"correction_log": correction * shrink, "lambda": shrink, "effective_n": effective_n, "max_age_days": max(ages), "residual_dispersion": dispersion, "warnings": warnings}
