"""Leakage-aware validation and scorecard helpers for Ceres AVMs."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from math import ceil, isfinite
from statistics import median
from typing import Iterable, Sequence

from .valuation_data import ValuationDataError, ValuationRecord


def _finite_pairs(actual: Iterable[float], predicted: Iterable[float]) -> list[tuple[float, float]]:
    pairs = []
    for observed, estimate in zip(actual, predicted):
        try:
            observed, estimate = float(observed), float(estimate)
        except (TypeError, ValueError):
            continue
        if isfinite(observed) and isfinite(estimate) and observed > 0 and estimate > 0:
            pairs.append((observed, estimate))
    if not pairs:
        raise ValueError("at least one finite positive actual/predicted pair is required")
    return pairs


def regression_metrics(actual: Iterable[float], predicted: Iterable[float]) -> dict[str, float | int]:
    """Return robust AVM metrics in original currency units and percentages.

    ``mdape``, ``p90_ape`` and ``cod`` are percentages; within-band fields are
    fractions in [0, 1].  This convention is stored in model reports to avoid
    presenting a fraction as a percentage in the product.
    """
    pairs = _finite_pairs(actual, predicted)
    errors = [abs(estimate - observed) for observed, estimate in pairs]
    ape = [error / observed for error, (observed, _) in zip(errors, pairs)]
    ratios = [estimate / observed for observed, estimate in pairs]
    median_ratio = median(ratios)
    mean_ratio = sum(ratios) / len(ratios)
    cod = (sum(abs(ratio - median_ratio) for ratio in ratios) / len(ratios) / median_ratio * 100) if median_ratio else float("inf")
    weighted_mean = sum(estimate for _, estimate in pairs) / sum(observed for observed, _ in pairs)
    prd = mean_ratio / weighted_mean if weighted_mean else float("nan")
    ordered_ape = sorted(ape)
    p90_index = min(len(ordered_ape) - 1, max(0, ceil(len(ordered_ape) * 0.90) - 1))
    return {
        "sample_count": len(pairs),
        "mae_brl": sum(errors) / len(errors),
        "mdape": median(ape) * 100,
        "p90_ape": ordered_ape[p90_index] * 100,
        "within_5": sum(value <= 0.05 for value in ape) / len(ape),
        "within_10": sum(value <= 0.10 for value in ape) / len(ape),
        "within_20": sum(value <= 0.20 for value in ape) / len(ape),
        "median_ratio": median_ratio,
        "cod": cod,
        "prd": prd,
    }


def _entity_key(record: ValuationRecord) -> tuple[str, None]:
    """Keep every observation for one property in the same split.

    Listing clusters remain available to the comparable-support policy, but a
    property must not cross a temporal or spatial boundary merely because a
    source assigned it a different cluster identifier.
    """
    return (record.property_id, None)


def _groups(records: Sequence[ValuationRecord]) -> list[list[ValuationRecord]]:
    grouped: dict[tuple[str, str | None], list[ValuationRecord]] = defaultdict(list)
    for record in records:
        grouped[_entity_key(record)].append(record)
    return list(grouped.values())


def _date_boundaries(records: Sequence[ValuationRecord], count: int) -> list[datetime]:
    dates = sorted({record.valuation_time for record in records})
    if len(dates) < count:
        raise ValuationDataError(f"at least {count} distinct valuation times are required")
    return dates


def temporal_partitions(
    records: Sequence[ValuationRecord],
    *,
    calibration_fraction: float = 0.2,
    test_fraction: float = 0.2,
) -> dict[str, list[ValuationRecord]]:
    """Split chronologically while keeping properties/listing clusters intact."""
    if not records:
        raise ValuationDataError("at least one valuation record is required")
    if not 0 < calibration_fraction < 1 or not 0 < test_fraction < 1 or calibration_fraction + test_fraction >= 1:
        raise ValueError("calibration and test fractions must be positive and leave a training set")
    partitions = {"train": [], "calibration": [], "test": []}
    groups = sorted(_groups(records), key=lambda group: max(record.valuation_time for record in group))
    if len(groups) < 3:
        raise ValuationDataError("at least three entity groups are required for temporal partitions")
    train_end = max(1, min(len(groups) - 2, int(len(groups) * (1 - calibration_fraction - test_fraction))))
    calibration_end = max(train_end + 1, min(len(groups) - 1, int(len(groups) * (1 - test_fraction))))
    for index, group in enumerate(groups):
        bucket = "train" if index < train_end else "calibration" if index < calibration_end else "test"
        partitions[bucket].extend(group)
    if not partitions["train"] or not partitions["calibration"] or not partitions["test"]:
        raise ValuationDataError("temporal partition produced an empty split; add more dates or reduce holdout fractions")
    for name, rows in partitions.items():
        if any(record.feature_as_of > record.valuation_time for record in rows):
            raise ValuationDataError(f"{name} contains a future feature snapshot")
    return {name: sorted(rows, key=lambda row: row.valuation_time) for name, rows in partitions.items()}


def rolling_folds(records: Sequence[ValuationRecord], *, n_folds: int = 3) -> list[tuple[list[ValuationRecord], list[ValuationRecord]]]:
    """Create expanding temporal folds with entity/listing group isolation."""
    if n_folds < 2:
        raise ValueError("n_folds must be at least two")
    dates = _date_boundaries(records, n_folds + 1)
    folds: list[tuple[list[ValuationRecord], list[ValuationRecord]]] = []
    for index in range(1, n_folds + 1):
        validation_start = dates[index]
        validation_end = dates[index + 1] if index + 1 < len(dates) else None
        train = [record for record in records if record.valuation_time < validation_start]
        validation = [record for record in records if record.valuation_time >= validation_start and (validation_end is None or record.valuation_time < validation_end)]
        train_keys = {_entity_key(record) for record in train}
        validation = [record for record in validation if _entity_key(record) not in train_keys]
        if not train or not validation:
            continue
        cutoff = max(record.valuation_time for record in train)
        if any(record.feature_as_of > record.valuation_time or record.feature_as_of > cutoff for record in train):
            raise ValuationDataError("rolling fold contains a feature snapshot newer than its training cutoff")
        folds.append((sorted(train, key=lambda row: row.valuation_time), sorted(validation, key=lambda row: row.valuation_time)))
    if len(folds) < 2:
        raise ValuationDataError("at least two non-empty rolling folds are required")
    return folds


def spatial_holdout(records: Sequence[ValuationRecord], held_out_blocks: set[str]) -> tuple[list[ValuationRecord], list[ValuationRecord]]:
    """Hold out H3 blocks without splitting a property/listing group."""
    if not held_out_blocks:
        raise ValueError("held_out_blocks must not be empty")
    def block(record: ValuationRecord) -> str | None:
        return next((record.features.get(name) for name in ("h3_r8", "h3_r9", "h3_r7") if record.features.get(name)), None)
    test = [record for record in records if block(record) in held_out_blocks]
    train = [record for record in records if block(record) not in held_out_blocks]
    overlap = {_entity_key(record) for record in train} & {_entity_key(record) for record in test}
    if overlap:
        raise ValuationDataError("spatial holdout splits a property or listing cluster")
    if not train or not test:
        raise ValuationDataError("spatial holdout produced an empty split")
    return train, test
