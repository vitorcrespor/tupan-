"""Persisted XGBoost AVM training and inference.

Training is explicit through :func:`train_price_model` (or
``python -m train.train_avm``). Runtime callers use :func:`predict_price`,
which only loads a saved artifact and calls ``model.predict``.
"""

from __future__ import annotations

import json
import math
import os
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
from xgboost import XGBRegressor
from xgboost.core import XGBoostError


ARTIFACT_SCHEMA_VERSION = 1
FEATURE_COLUMNS = (
    "kind",
    "city",
    "area",
    "rooms",
    "bathrooms",
    "parking_spaces",
    "area_m2",
    "age",
    "dom_days",
    "exclusive",
    "luxury",
    "leisure",
    "location_score",
    "leverage",
)
CATEGORICAL_FEATURES = ("kind", "city", "area")
MISSING_CATEGORY = "__MISSING__"


class AvmError(RuntimeError):
    """Base error for AVM training and inference."""


class ModelArtifactMissingError(AvmError):
    """Raised when no trained model artifact is available for inference."""


class ModelArtifactIncompatibleError(AvmError):
    """Raised when model metadata cannot safely drive the loaded model."""


class FeaturePreparationError(AvmError):
    """Raised when a property cannot be represented by the trained feature schema."""


def artifact_paths(
    model_path: str | Path | None = None,
    metadata_path: str | Path | None = None,
) -> tuple[Path, Path]:
    """Return explicit model and metadata locations without touching the filesystem."""
    default_model = Path(__file__).resolve().parent / "artifacts" / "avm_price.json"
    resolved_model = Path(model_path or os.getenv("AVM_MODEL_PATH") or default_model).expanduser()
    resolved_metadata = Path(
        metadata_path
        or os.getenv("AVM_MODEL_METADATA_PATH")
        or resolved_model.with_suffix(".metadata.json")
    ).expanduser()
    return resolved_model, resolved_metadata


def predict_price(real_estate: Any) -> float:
    """Load/reuse the trained AVM and predict an estimated price in BRL.

    This function intentionally never calls ``fit``, Optuna, or a training
    helper. It is safe to invoke from an HTTP valuation request.
    """
    model_path, metadata_path = artifact_paths()
    model, metadata = _load_model(str(model_path), str(metadata_path))
    features = prepare_feature_frame(real_estate, metadata)
    try:
        prediction = float(model.predict(features)[0])
    except (ValueError, XGBoostError) as exc:
        raise ModelArtifactIncompatibleError("The saved AVM cannot score the prepared feature frame.") from exc
    if not math.isfinite(prediction) or prediction <= 0:
        raise ModelArtifactIncompatibleError("The saved AVM returned an invalid estimated price.")
    return prediction


def load_price_model() -> tuple[XGBRegressor, dict[str, Any]]:
    """Load the configured trained AVM from the process-level artifact cache."""
    model_path, metadata_path = artifact_paths()
    return _load_model(str(model_path), str(metadata_path))


def train_price_model(
    train_dataset: Iterable[Any],
    *,
    seed: int | None = None,
    n_trials: int = 100,
    model_path: str | Path | None = None,
    metadata_path: str | Path | None = None,
) -> dict[str, Any]:
    """Explicitly optimize, fit, and persist the price AVM.

    Targets remain the existing ``predictions.suggested_price`` domain field
    (with legacy ``preictions`` compatibility). Current asking price and text
    summary stay excluded from the feature schema, matching the original
    training intent.
    """
    rows, target = _training_rows(train_dataset)
    if len(rows) < 5:
        raise FeaturePreparationError("AVM training requires at least five properties with suggested_price targets.")
    if n_trials < 1:
        raise ValueError("n_trials must be at least one.")

    # Kept inside the explicit training path so serving an existing artifact
    # does not require or initialize the training toolchain.
    from sklearn.metrics import root_mean_squared_error
    from sklearn.model_selection import train_test_split

    resolved_seed = seed if seed is not None else int(os.getenv("SEED", "42"))
    frame, categories = _frame_from_rows(rows)
    X_train, X_valid, y_train, y_valid = train_test_split(
        frame,
        target,
        test_size=0.4,
        random_state=resolved_seed,
    )
    best_params = _optimize_parameters(X_train, X_valid, y_train, y_valid, seed=resolved_seed, n_trials=n_trials)
    model = _make_regressor(best_params, seed=resolved_seed)
    model.fit(frame, target)
    validation_model = _make_regressor(best_params, seed=resolved_seed)
    validation_model.fit(X_train, y_train)
    validation_rmse = float(root_mean_squared_error(y_valid, validation_model.predict(X_valid)))

    target_model_path, target_metadata_path = artifact_paths(model_path, metadata_path)
    metadata = {
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "model_type": "xgboost.XGBRegressor",
        "target": "predictions.suggested_price",
        "target_transform": "none",
        "feature_columns": list(FEATURE_COLUMNS),
        "categorical_features": list(CATEGORICAL_FEATURES),
        "categories": categories,
        "training_rows": len(rows),
        "validation_rmse": validation_rmse,
        "best_params": best_params,
        "random_state": resolved_seed,
    }
    _save_artifact(model, metadata, target_model_path, target_metadata_path)
    _load_model.cache_clear()
    return {
        "model_path": str(target_model_path),
        "metadata_path": str(target_metadata_path),
        "training_rows": len(rows),
        "validation_rmse": validation_rmse,
        "best_params": best_params,
    }


def prepare_feature_frame(real_estate: Any, metadata: dict[str, Any]) -> pd.DataFrame:
    """Use the artifact's recorded feature contract to prepare one property."""
    _validate_metadata(metadata)
    row = _feature_row(real_estate)
    required_columns = metadata["feature_columns"]
    if tuple(required_columns) != FEATURE_COLUMNS:
        raise ModelArtifactIncompatibleError("The model artifact was trained with an unsupported AVM feature schema.")
    if not math.isfinite(row["area_m2"]) or row["area_m2"] <= 0:
        raise FeaturePreparationError("Property square_metrage is required for AVM inference.")
    for column in CATEGORICAL_FEATURES:
        category = row[column]
        known_categories = metadata["categories"].get(column, [])
        if category not in known_categories:
            raise FeaturePreparationError(
                f"Property {column} value {category!r} is incompatible with the trained AVM artifact."
            )
    return _frame_from_rows([row], categories=metadata["categories"])[0]


def _training_rows(train_dataset: Iterable[Any]) -> tuple[list[dict[str, Any]], list[float]]:
    rows: list[dict[str, Any]] = []
    target: list[float] = []
    for property_ in train_dataset:
        value = _target_price(property_)
        if value is None:
            continue
        row = _feature_row(property_)
        if not math.isfinite(row["area_m2"]) or row["area_m2"] <= 0:
            continue
        rows.append(row)
        target.append(value)
    return rows, target


def _target_price(property_: Any) -> float | None:
    predictions = getattr(property_, "predictions", None) or getattr(property_, "preictions", None)
    value = _number_or_none(getattr(predictions, "suggested_price", None))
    return value if value is not None and value > 0 else None


def _feature_row(property_: Any) -> dict[str, Any]:
    location = getattr(property_, "location", None)
    metrics = getattr(property_, "real_estate_metrics", None)
    profile = getattr(property_, "four_metric", None)
    kind = getattr(property_, "kind", None)
    return {
        "kind": _category(getattr(kind, "value", kind)),
        "city": _category(getattr(location, "city", None)),
        "area": _category(getattr(location, "area", None)),
        "rooms": _number_or_nan(getattr(metrics, "number_of_rooms", None)),
        "bathrooms": _number_or_nan(getattr(metrics, "number_of_bathrooms", None)),
        "parking_spaces": _number_or_nan(getattr(metrics, "number_of_parking_spaces", None)),
        "area_m2": _number_or_nan(getattr(metrics, "square_metrage", None)),
        "age": _number_or_nan(getattr(property_, "age", None)),
        "dom_days": _number_or_nan(getattr(property_, "dom", None)),
        "exclusive": _bool_or_nan(getattr(property_, "exclusive", None)),
        "luxury": _number_or_nan(getattr(profile, "luxury", None)),
        "leisure": _number_or_nan(getattr(profile, "leisure", None)),
        "location_score": _number_or_nan(getattr(profile, "location_", None)),
        "leverage": _number_or_nan(getattr(profile, "leverage", None)),
    }


def _frame_from_rows(
    rows: list[dict[str, Any]],
    *,
    categories: dict[str, list[str]] | None = None,
) -> tuple[pd.DataFrame, dict[str, list[str]]]:
    frame = pd.DataFrame(rows, columns=FEATURE_COLUMNS)
    resolved_categories: dict[str, list[str]] = {}
    for column in CATEGORICAL_FEATURES:
        values = categories[column] if categories is not None else sorted(set(frame[column].astype(str)))
        if MISSING_CATEGORY not in values:
            values = [*values, MISSING_CATEGORY]
        resolved_categories[column] = list(values)
        frame[column] = pd.Categorical(frame[column].astype(str), categories=resolved_categories[column])
    return frame, resolved_categories


def _optimize_parameters(
    X_train: pd.DataFrame,
    X_valid: pd.DataFrame,
    y_train: list[float],
    y_valid: list[float],
    *,
    seed: int,
    n_trials: int,
) -> dict[str, Any]:
    from sklearn.metrics import root_mean_squared_error

    try:
        import optuna
    except ImportError as exc:
        raise AvmError("Optuna is required only for explicit AVM training.") from exc

    def objective(trial: Any) -> float:
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 100, 1000),
            "max_depth": trial.suggest_int("max_depth", 3, 12),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "subsample": trial.suggest_float("subsample", 0.1, 0.8),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 20),
            "gamma": trial.suggest_float("gamma", 1e-8, 1.0, log=True),
        }
        model = _make_regressor(params, seed=seed)
        model.fit(X_train, y_train)
        return float(root_mean_squared_error(y_valid, model.predict(X_valid)))

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(direction="minimize", sampler=optuna.samplers.TPESampler(seed=seed))
    study.optimize(objective, n_trials=n_trials)
    return study.best_params.copy()


def _make_regressor(params: dict[str, Any], *, seed: int) -> XGBRegressor:
    return XGBRegressor(
        objective="reg:squarederror",
        tree_method="hist",
        enable_categorical=True,
        random_state=seed,
        **params,
    )


def _save_artifact(model: XGBRegressor, metadata: dict[str, Any], model_path: Path, metadata_path: Path) -> None:
    model_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    model_temporary = model_path.with_name(f".{model_path.stem}.{uuid.uuid4().hex}.tmp{model_path.suffix or '.json'}")
    metadata_temporary = metadata_path.with_name(f".{metadata_path.stem}.{uuid.uuid4().hex}.tmp.json")
    try:
        model.save_model(str(model_temporary))
        metadata_temporary.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
        model_temporary.replace(model_path)
        metadata_temporary.replace(metadata_path)
    finally:
        model_temporary.unlink(missing_ok=True)
        metadata_temporary.unlink(missing_ok=True)


@lru_cache(maxsize=4)
def _load_model(model_path_string: str, metadata_path_string: str) -> tuple[XGBRegressor, dict[str, Any]]:
    model_path = Path(model_path_string)
    metadata_path = Path(metadata_path_string)
    if not model_path.is_file() or not metadata_path.is_file():
        raise ModelArtifactMissingError(
            f"Trained AVM artifacts are missing. Expected model={model_path} and metadata={metadata_path}."
        )
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        _validate_metadata(metadata)
        model = XGBRegressor()
        model.load_model(str(model_path))
    except (OSError, ValueError, json.JSONDecodeError, XGBoostError) as exc:
        raise ModelArtifactIncompatibleError("The saved AVM artifact could not be loaded.") from exc
    model_features = list(model.get_booster().feature_names or [])
    if model_features and model_features != metadata["feature_columns"]:
        raise ModelArtifactIncompatibleError("The saved AVM model feature names do not match its metadata.")
    return model, metadata


def _validate_metadata(metadata: dict[str, Any]) -> None:
    if metadata.get("schema_version") != ARTIFACT_SCHEMA_VERSION:
        raise ModelArtifactIncompatibleError("The AVM artifact schema version is unsupported.")
    if metadata.get("target_transform") != "none":
        raise ModelArtifactIncompatibleError("The AVM artifact uses an unsupported target transformation.")
    if metadata.get("feature_columns") != list(FEATURE_COLUMNS):
        raise ModelArtifactIncompatibleError("The AVM artifact feature schema is incompatible with this service.")
    if metadata.get("categorical_features") != list(CATEGORICAL_FEATURES):
        raise ModelArtifactIncompatibleError("The AVM artifact categorical feature schema is incompatible with this service.")
    categories = metadata.get("categories")
    if not isinstance(categories, dict) or any(not isinstance(categories.get(column), list) for column in CATEGORICAL_FEATURES):
        raise ModelArtifactIncompatibleError("The AVM artifact category metadata is invalid.")


def _category(value: Any) -> str:
    return str(value) if value not in (None, "") else MISSING_CATEGORY


def _number_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _number_or_nan(value: Any) -> float:
    number = _number_or_none(value)
    return number if number is not None else float("nan")


def _bool_or_nan(value: Any) -> float:
    if value is None:
        return float("nan")
    return 1.0 if bool(value) else 0.0
