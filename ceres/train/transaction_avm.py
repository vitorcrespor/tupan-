"""Research-aligned transaction-price AVM candidate.

This module is deliberately separate from the legacy training module and
writes a versioned candidate artifact. The existing serving artifact is never
overwritten; promotion requires scorecard and untouched holdout gates.
"""

from __future__ import annotations

import json
import math
import os
from functools import lru_cache
from statistics import median
import uuid
from pathlib import Path
from typing import Any, Sequence

import pandas as pd
from xgboost import XGBRegressor

from .valuation_data import CATEGORICAL_FEATURES, FEATURE_COLUMNS, ValuationRecord, feature_values
from .valuation_data import _derived_h3
from .valuation_uncertainty import conformal_interval, fit_conformal
from .valuation_validation import regression_metrics, temporal_partitions


MODEL_SCHEMA_VERSION = 2


def candidate_artifact_paths(
    model_path: str | Path | None = None,
    metadata_path: str | Path | None = None,
) -> tuple[Path, Path]:
    model = Path(
        model_path
        or os.getenv("AVM_TRANSACTION_MODEL_PATH")
        or Path(__file__).with_name("artifacts") / "avm_transaction_v2.json"
    ).expanduser()
    metadata = Path(
        metadata_path
        or os.getenv("AVM_TRANSACTION_METADATA_PATH")
        or model.with_suffix(".metadata.json")
    ).expanduser()
    return model, metadata


def _frame(records: Sequence[ValuationRecord], categories: dict[str, list[str]]) -> pd.DataFrame:
    return _feature_frame([feature_values(record) for record in records], categories)


def _feature_frame(rows: Sequence[dict[str, Any]], categories: dict[str, list[str]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows, columns=FEATURE_COLUMNS)
    for name in CATEGORICAL_FEATURES:
        frame[name] = pd.Categorical(
            frame[name].fillna("__MISSING__").astype(str),
            categories=categories[name],
        )
    for name in FEATURE_COLUMNS:
        if name in CATEGORICAL_FEATURES:
            continue
        # Missing numeric facts are valid under the contract. Keep them as
        # floating NaN so XGBoost can route them through its missing-value
        # path instead of receiving an ``object`` column from pandas.
        frame[name] = pd.to_numeric(frame[name], errors="coerce").astype("float64")
    return frame


def predict_transaction_price(
    features: dict[str, Any],
    *,
    model_path: str | Path | None = None,
    metadata_path: str | Path | None = None,
) -> dict[str, Any]:
    """Score a promoted transaction AVM and return its calibrated interval.

    Candidate artifacts are deliberately refused until an explicit promotion
    review changes ``promotion_status`` to ``production`` or ``promoted``.
    """
    model_file, metadata_file = candidate_artifact_paths(model_path, metadata_path)
    if not model_file.is_file() or not metadata_file.is_file():
        raise FileNotFoundError("A promoted transaction AVM artifact is not available.")
    metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
    if not isinstance(metadata, dict):
        raise RuntimeError("The transaction AVM metadata is not an object.")
    if metadata.get("promotion_status") not in {"production", "promoted"}:
        raise RuntimeError("The transaction AVM artifact is still a candidate.")
    if tuple(metadata.get("feature_columns", ())) != FEATURE_COLUMNS:
        raise RuntimeError("The transaction AVM feature schema is incompatible.")
    categories = metadata.get("categories") or {}
    normalized = {name: features.get(name) for name in FEATURE_COLUMNS}
    _derived_h3(normalized)
    for name in CATEGORICAL_FEATURES:
        value = str(normalized.get(name) or "__MISSING__")
        if value not in categories.get(name, []):
            raise RuntimeError(f"The transaction AVM does not support {name}={value!r}.")
        normalized[name] = value
    frame = _feature_frame([normalized], categories)
    model, cached_metadata = _load_transaction_model(str(model_file), str(metadata_file))
    # Keep the request contract tied to the same metadata used to load the
    # cached model. A replacement requires a worker restart, just like the
    # legacy artifact cache.
    metadata = cached_metadata
    log_prediction = float(model.predict(frame)[0])
    if not math.isfinite(log_prediction):
        raise RuntimeError("The transaction AVM returned a non-finite estimate.")
    estimate = math.exp(log_prediction)
    uncertainty = metadata.get("uncertainty") or {}
    calibration = uncertainty.get("calibration") or {}
    lower_log, upper_log = conformal_interval(log_prediction, log_prediction, calibration)
    return {
        "estimated_price": estimate,
        "lower_bound": math.exp(lower_log),
        "upper_bound": math.exp(upper_log),
        "interval_level": float(calibration["level"]),
        "calibration_sample_count": int(calibration["sample_count"]),
        "out_of_time_coverage": float(uncertainty["out_of_time_coverage"]),
        "model_version": str(metadata.get("model_version") or f"transaction-avm-v{metadata['schema_version']}"),
        "metadata": metadata,
    }


@lru_cache(maxsize=4)
def _load_transaction_model(model_path: str, metadata_path: str) -> tuple[XGBRegressor, dict[str, Any]]:
    """Load a promoted transaction model once per worker process."""
    try:
        metadata = json.loads(Path(metadata_path).read_text(encoding="utf-8"))
        if not isinstance(metadata, dict):
            raise ValueError("metadata must be an object")
        model = XGBRegressor(enable_categorical=True)
        model.load_model(model_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError("The transaction AVM artifact could not be loaded.") from exc
    return model, metadata


def _categories(records: Sequence[ValuationRecord]) -> dict[str, list[str]]:
    return {
        name: sorted(
            {str(record.features.get(name) or "__MISSING__") for record in records}
            | {"__MISSING__"}
        )
        for name in CATEGORICAL_FEATURES
    }


def _regressor(seed: int, n_estimators: int) -> XGBRegressor:
    return XGBRegressor(
        objective="reg:squarederror",
        eval_metric="mae",
        tree_method="hist",
        enable_categorical=True,
        random_state=seed,
        n_jobs=max(1, min(8, os.cpu_count() or 1)),
        learning_rate=0.05,
        n_estimators=n_estimators,
        max_depth=5,
        min_child_weight=8,
        subsample=0.8,
        colsample_bytree=0.8,
        gamma=0.0,
        reg_lambda=10.0,
        reg_alpha=0.0,
        max_bin=256,
    )


def _save(model: XGBRegressor, metadata: dict[str, Any], model_path: Path, metadata_path: Path) -> None:
    model_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    model_tmp = model_path.with_name(
        f".{model_path.stem}.{uuid.uuid4().hex}.tmp{model_path.suffix or '.json'}"
    )
    metadata_tmp = metadata_path.with_name(f".{metadata_path.stem}.{uuid.uuid4().hex}.tmp.json")
    try:
        model.save_model(str(model_tmp))
        metadata_tmp.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
        model_tmp.replace(model_path)
        metadata_tmp.replace(metadata_path)
    finally:
        model_tmp.unlink(missing_ok=True)
        metadata_tmp.unlink(missing_ok=True)


def train_transaction_avm(
    records: Sequence[ValuationRecord],
    *,
    seed: int = 42,
    n_estimators: int = 1800,
    model_path: str | Path | None = None,
    metadata_path: str | Path | None = None,
) -> dict[str, Any]:
    """Train a point-in-time log-price candidate and return its scorecard."""
    if n_estimators < 1:
        raise ValueError("n_estimators must be positive")
    partitions = temporal_partitions(records)
    train, calibration, test = (partitions[name] for name in ("train", "calibration", "test"))
    if len(train) < 8 or len(calibration) < 2 or len(test) < 2:
        raise ValueError("transaction AVM needs at least 8 train, 2 calibration and 2 test observations")
    # Learn category vocabularies from the training window only.  Pulling
    # categories from calibration/test would leak future distribution
    # information even though it does not use their target values.
    categories = _categories(train)
    X_train = _frame(train, categories)
    X_calibration = _frame(calibration, categories)
    X_test = _frame(test, categories)
    y_train = [math.log(record.price_brl) for record in train]
    y_calibration = [math.log(record.price_brl) for record in calibration]
    model = _regressor(seed, n_estimators)
    model.fit(X_train, y_train, eval_set=[(X_calibration, y_calibration)], verbose=False)
    calibration_log_predictions = [float(value) for value in model.predict(X_calibration)]
    test_log_predictions = [float(value) for value in model.predict(X_test)]
    calibration_predictions = [math.exp(value) for value in calibration_log_predictions]
    test_predictions = [math.exp(value) for value in test_log_predictions]
    conformal = fit_conformal(
        y_calibration,
        calibration_log_predictions,
        calibration_log_predictions,
        level=0.8,
    )
    test_intervals = [conformal_interval(value, value, conformal) for value in test_log_predictions]
    interval_coverage = sum(
        lower <= actual <= upper
        for actual, (lower, upper) in zip((math.log(record.price_brl) for record in test), test_intervals)
    ) / len(test_intervals)
    interval_width_pct = median(
        (math.exp(upper) - math.exp(lower)) / prediction * 100
        for prediction, (lower, upper) in zip(test_predictions, test_intervals)
    )
    model_path, metadata_path = candidate_artifact_paths(model_path, metadata_path)
    metadata = {
        "schema_version": MODEL_SCHEMA_VERSION,
        "model_type": "xgboost.XGBRegressor",
        "target": "sale_price_brl",
        "target_transform": "log",
        "feature_columns": list(FEATURE_COLUMNS),
        "categorical_features": list(CATEGORICAL_FEATURES),
        "categories": categories,
        "training_rows": len(train),
        "calibration_rows": len(calibration),
        "test_rows": len(test),
        "random_state": seed,
        "parameters": model.get_params(),
        "validation_metrics": regression_metrics(
            [record.price_brl for record in calibration],
            calibration_predictions,
        ),
        "out_of_time_metrics": regression_metrics(
            [record.price_brl for record in test],
            test_predictions,
        ),
        "uncertainty": {
            "method": "split_conformal_point_residual",
            "calibration": conformal,
            "out_of_time_coverage": interval_coverage,
            "out_of_time_median_width_pct": interval_width_pct,
        },
        "model_version": f"transaction-avm-v{MODEL_SCHEMA_VERSION}",
        "promotion_status": "candidate",
    }
    _save(model, metadata, model_path, metadata_path)
    return {"model_path": str(model_path), "metadata_path": str(metadata_path), **metadata}
