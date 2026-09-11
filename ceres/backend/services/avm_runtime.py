"""Thread-isolated runtime adapter for the persisted AVM artifact.

This module intentionally adapts PostgreSQL estate records to the existing
feature-preparation contract. It never fits, optimizes, or mutates a model.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from types import MappingProxyType, SimpleNamespace
from typing import Any, Mapping

from backend.services.errors import DomainValidationError, UnavailableError


@dataclass(frozen=True)
class AvmPrediction:
    estimated_price: float
    inference_ms: float


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
        try:
            from train.avm import (
                FeaturePreparationError,
                ModelArtifactIncompatibleError,
                ModelArtifactMissingError,
                predict_price,
            )

            estimate = float(predict_price(_as_existing_estate(estate)))
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
        return AvmPrediction(estimated_price=estimate, inference_ms=(time.perf_counter() - started) * 1_000)


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
