"""Thread-isolated runtime adapter for the persisted AVM artifact.

This module intentionally adapts PostgreSQL estate records to the existing
feature-preparation contract. It never fits, optimizes, or mutates a model.
"""

from __future__ import annotations

import time
import json
from dataclasses import dataclass
from types import MappingProxyType, SimpleNamespace
from typing import Any, Mapping

from backend.services.errors import DomainValidationError, UnavailableError


@dataclass(frozen=True)
class AvmPrediction:
    estimated_price: float
    inference_ms: float
    diagnostics: Mapping[str, Any] | None = None
    lower_bound: float | None = None
    upper_bound: float | None = None
    interval_level: float | None = None
    calibration_sample_count: int | None = None
    out_of_time_coverage: float | None = None
    model_version: str | None = None
    uncertainty_status: str = "not_calibrated"


class AvmRuntime:
    """Run the existing CPU-bound XGBoost inference outside the event loop."""

    async def predict(self, estate: Mapping[str, Any]) -> AvmPrediction:
        # Feature preparation includes Pandas/XGBoost work. ``to_thread`` keeps
        # that CPU work from delaying unrelated async database/network requests.
        import asyncio

        return await asyncio.to_thread(self._predict_sync, MappingProxyType(dict(estate)))

    @staticmethod
    def _predict_sync(estate: Mapping[str, Any]) -> AvmPrediction:
        started = time.perf_counter()
        promoted = _promoted_transaction_prediction(estate)
        if promoted is not None:
            elapsed = (time.perf_counter() - started) * 1_000
            return AvmPrediction(
                estimated_price=promoted["estimated_price"],
                lower_bound=promoted["lower_bound"],
                upper_bound=promoted["upper_bound"],
                interval_level=promoted["interval_level"],
                calibration_sample_count=promoted["calibration_sample_count"],
                out_of_time_coverage=promoted["out_of_time_coverage"],
                model_version=promoted["model_version"],
                uncertainty_status="calibrated",
                inference_ms=elapsed,
                diagnostics=MappingProxyType(promoted["diagnostics"]),
            )
        try:
            from train.avm import (
                FeaturePreparationError,
                ModelArtifactIncompatibleError,
                ModelArtifactMissingError,
                predict_price,
                load_price_model,
            )

            estimate = float(predict_price(_as_existing_estate(estate)))
            _, metadata = load_price_model()
        except ModelArtifactMissingError as exc:
            raise UnavailableError(
                "No trained AVM artifact is available for estate analysis.",
                details={"reason": "model_artifact_missing"},
            ) from exc
        except ModelArtifactIncompatibleError as exc:
            raise UnavailableError(
                "The deployed AVM artifact is incompatible with estate analysis.",
                details={"reason": "model_artifact_incompatible"},
            ) from exc
        except FeaturePreparationError as exc:
            raise DomainValidationError(
                "The estate has incomplete or incompatible AVM features.",
                details={"reason": str(exc)},
            ) from exc
        except Exception as exc:
            raise UnavailableError("The AVM inference service is unavailable.") from exc
        diagnostics = {key: metadata.get(key) for key in ('model_type', 'target', 'schema_version', 'training_rows')}
        diagnostics["uncertainty_status"] = "not_calibrated"
        return AvmPrediction(estimated_price=estimate, inference_ms=(time.perf_counter() - started) * 1_000,
                             diagnostics=MappingProxyType(diagnostics))


def _promoted_transaction_prediction(estate: Mapping[str, Any]) -> dict[str, Any] | None:
    """Use the transaction AVM only after an explicit artifact promotion.

    A candidate artifact is intentionally ignored here: training and model
    promotion are operational workflows, not request-time behavior. If a
    promoted artifact is present but invalid, fail closed instead of silently
    falling back to a different model with different semantics.
    """
    from train.transaction_avm import candidate_artifact_paths, predict_transaction_price

    model_path, metadata_path = candidate_artifact_paths()
    if not model_path.is_file() or not metadata_path.is_file():
        return None
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise UnavailableError(
            "The promoted transaction AVM metadata could not be read.",
            details={"reason": "transaction_avm_metadata_invalid"},
        ) from exc
    if not isinstance(metadata, dict):
        raise UnavailableError(
            "The promoted transaction AVM metadata is not an object.",
            details={"reason": "transaction_avm_metadata_invalid"},
        )
    if metadata.get("promotion_status") not in {"production", "promoted"}:
        return None
    try:
        result = predict_transaction_price(_as_transaction_features(estate))
    except Exception as exc:
        raise UnavailableError(
            "The promoted transaction AVM could not score this estate.",
            details={"reason": "transaction_avm_inference_failed"},
        ) from exc
    uncertainty = metadata.get("uncertainty") or {}
    return {
        **result,
        "diagnostics": {
            "model_type": metadata.get("model_type"),
            "target": metadata.get("target"),
            "schema_version": metadata.get("schema_version"),
            "training_rows": metadata.get("training_rows"),
            "uncertainty_status": "calibrated",
            "uncertainty_method": uncertainty.get("method"),
            "out_of_time_median_width_pct": uncertainty.get("out_of_time_median_width_pct"),
            "calibration_sample_count": result.get("calibration_sample_count"),
            "out_of_time_coverage": result.get("out_of_time_coverage"),
            "model_version": result.get("model_version"),
        },
    }


def _as_transaction_features(estate: Mapping[str, Any]) -> dict[str, Any]:
    """Map the authorized estate projection to the transaction AVM contract."""
    attributes = estate.get("attributes") or {}
    if not isinstance(attributes, Mapping):
        attributes = {}

    def attr(*names: str) -> Any:
        for name in names:
            value = attributes.get(name)
            if value is not None:
                return value
        return None

    return {
        "usable_area_m2": estate.get("area_m2"),
        "built_area_m2": attr("built_area_m2", "built_area"),
        "lot_area_m2": attr("lot_area_m2", "lot_area"),
        "latitude": estate.get("latitude"),
        "longitude": estate.get("longitude"),
        "property_type": estate.get("property_type"),
        "subtype": estate.get("subtype") or attr("subtype"),
        "city": estate.get("city"),
        "state": estate.get("state") or attr("state"),
        "rooms": estate.get("rooms"),
        "suites": attr("suites"),
        "bathrooms": estate.get("bathrooms"),
        "parking_spaces": estate.get("parking_spaces"),
        "floor": attr("floor"),
        "building_floors": attr("building_floors"),
        "year_built": attr("year_built"),
        "renovation_year": attr("renovation_year"),
        "condition": attr("condition"),
        "elevator": attr("elevator"),
        "condo_fee_brl": attr("condo_fee_brl", "condo_fee"),
        "h3_r7": attr("h3_r7"),
        "h3_r8": attr("h3_r8"),
        "h3_r9": attr("h3_r9"),
    }


def _as_existing_estate(estate: Mapping[str, Any]) -> SimpleNamespace:
    """Map storage fields to the existing ``train.avm._feature_row`` shape."""
    attributes = estate.get("attributes") or {}
    profile = attributes.get("four_metric") or attributes.get("profile") or {}
    return SimpleNamespace(
        kind=estate.get("property_type"),
        location=SimpleNamespace(city=estate.get("city"), area=estate.get("area")),
        real_estate_metrics=SimpleNamespace(
            number_of_rooms=estate.get("rooms"),
            number_of_bathrooms=estate.get("bathrooms"),
            number_of_parking_spaces=estate.get("parking_spaces"),
            square_metrage=estate.get("area_m2"),
        ),
        age=estate.get("age_years"),
        dom=estate.get("days_on_market"),
        exclusive=estate.get("exclusive"),
        four_metric=SimpleNamespace(
            luxury=profile.get("luxury"),
            leisure=profile.get("leisure"),
            location_=profile.get("location_", profile.get("location_score")),
            leverage=profile.get("leverage"),
        ),
    )
