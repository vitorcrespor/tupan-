"""Deterministic structural similarity for authorized comparable estates."""

from __future__ import annotations

from math import isfinite, sqrt
from typing import Any, Iterable, Mapping


METHOD = "cosine"
FEATURE_VERSION = "structural-area100-rooms-bathrooms-parking-v1"
CANDIDATE_LIMIT = 500


def rank_comparables(
    target: Mapping[str, Any],
    candidates: Iterable[Mapping[str, Any]],
    *,
    limit: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Score and rank a bounded, already-authorized candidate collection.

    Area is expressed in units of 100 m² so that one numeric feature does not
    dominate only because it uses a larger physical unit. The other dimensions
    are counts. L2 normalization is part of cosine similarity itself.
    """
    if limit < 1:
        raise ValueError("comparable result limit must be positive")
    target_vector = _feature_vector(target)
    ranked: list[dict[str, Any]] = []
    scored_count = 0
    for source in candidates:
        item = dict(source)
        candidate_vector = _feature_vector(item)
        if target_vector is None:
            score, status = None, "target_incomplete_features"
        elif candidate_vector is None:
            score, status = None, "candidate_incomplete_features"
        else:
            score = _cosine(target_vector, candidate_vector)
            status = "available" if score is not None else "zero_vector"
        if score is not None:
            scored_count += 1
        item.update({
            "similarity_score": score,
            "similarity_status": status,
            "similarity_method": METHOD,
            "similarity_feature_version": FEATURE_VERSION,
        })
        ranked.append(item)

    ranked.sort(key=_rank_key)
    returned = ranked[:limit]
    return returned, {
        "candidate_count": len(ranked),
        "scored_count": scored_count,
        "returned_count": len(returned),
        "candidate_limit": CANDIDATE_LIMIT,
        "truncated": len(ranked) >= CANDIDATE_LIMIT,
        "similarity_method": METHOD,
        "similarity_feature_version": FEATURE_VERSION,
    }


def cosine_similarity(left: Mapping[str, Any], right: Mapping[str, Any]) -> float | None:
    """Public pair helper using the same feature contract as ranking."""
    left_vector, right_vector = _feature_vector(left), _feature_vector(right)
    return _cosine(left_vector, right_vector) if left_vector is not None and right_vector is not None else None


def _feature_vector(estate: Mapping[str, Any]) -> tuple[float, float, float, float] | None:
    values = (
        _number(estate.get("area_m2"), positive=True),
        _number(estate.get("rooms")),
        _number(estate.get("bathrooms")),
        _number(estate.get("parking_spaces")),
    )
    if any(value is None for value in values):
        return None
    area, rooms, bathrooms, parking = values
    return (area / 100.0, rooms, bathrooms, parking)


def _cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float | None:
    left_norm = sqrt(sum(value * value for value in left))
    right_norm = sqrt(sum(value * value for value in right))
    if left_norm <= 0 or right_norm <= 0:
        return None
    value = sum(a * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)
    return round(max(0.0, min(1.0, value)), 6)


def _rank_key(item: Mapping[str, Any]) -> tuple[Any, ...]:
    score = item.get("similarity_score")
    distance = item.get("distance_meters")
    return (
        score is None,
        -(float(score) if score is not None else 0.0),
        float(distance) if _number(distance) is not None else float("inf"),
        str(item.get("id") or ""),
    )


def _number(value: Any, *, positive: bool = False) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(number) or number < 0 or positive and number <= 0:
        return None
    return number
