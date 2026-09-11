"""Offline preparation of global market intelligence and AVM artifacts."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date
from types import SimpleNamespace
from typing import Any

from backend.repositories.platform_intelligence import PlatformIntelligenceRepository
from backend.services.avm_runtime import _as_existing_estate
from backend.services.heatmap_precompute import _aggregate_sources


@dataclass(frozen=True)
class PlatformHeatmapRefresh:
    source_estate_count: int
    aggregate_count: int
    h3_resolution: int
    period_start: date
    period_end: date


class PlatformIntelligenceService:
    """Runs only from a deployment/ingestion process, never an HTTP request."""

    def __init__(self, repository: PlatformIntelligenceRepository | None = None) -> None:
        self._repository = repository or PlatformIntelligenceRepository()

    async def refresh_heatmap(self, *, h3_resolution: int = 9, allow_empty: bool = False) -> PlatformHeatmapRefresh:
        if not 0 <= h3_resolution <= 15:
            raise ValueError("h3_resolution must be between 0 and 15.")
        today = date.today()
        await self._repository.start()
        try:
            sources = await self._repository.heatmap_sources()
            aggregates = await asyncio.to_thread(
                _aggregate_sources,
                sources,
                resolution=h3_resolution,
                period_start=today,
                period_end=today,
                input_version="platform-estate-base-v1",
            )
            published = await self._repository.replace_platform_heatmap(aggregates, allow_empty=allow_empty)
            return PlatformHeatmapRefresh(
                source_estate_count=len(sources),
                aggregate_count=published,
                h3_resolution=h3_resolution,
                period_start=today,
                period_end=today,
            )
        finally:
            await self._repository.close()

    async def train_avm(self, *, trials: int = 100, seed: int | None = None) -> dict[str, Any]:
        """Train one shared AVM only from observed database sale prices."""
        await self._repository.start()
        try:
            sources = await self._repository.avm_training_sources()
        finally:
            await self._repository.close()
        training_records = [_as_avm_training_record(source) for source in sources]
        from train.avm import train_price_model

        return await asyncio.to_thread(
            train_price_model,
            training_records,
            seed=seed,
            n_trials=trials,
            target_label="estates.last_sale_price",
        )

    async def train_transaction_avm(self, *, seed: int = 42, n_estimators: int = 1800) -> dict[str, Any]:
        """Train the research-aligned candidate from explicit observations.

        This command never overwrites the legacy serving artifact. Promotion
        requires a separate scorecard review and model-registry decision.
        """
        await self._repository.start()
        try:
            sources = await self._repository.valuation_observations(target_kind="transaction")
        finally:
            await self._repository.close()
        from train.valuation_data import ValuationDataError, parse_records
        from train.transaction_avm import train_transaction_avm

        records, exclusions = parse_records(sources, target_kind="transaction")
        if not records:
            return {
                "candidate_only": True,
                "promotion_status": "not_ready",
                "reason": "no_eligible_transaction_observations",
                "eligible_observations": 0,
                "excluded_observations": exclusions,
            }
        if len(records) < 12:
            return {
                "candidate_only": True,
                "promotion_status": "not_ready",
                "reason": "at_least_12_observations_are_required_for_train_calibration_test",
                "eligible_observations": len(records),
                "excluded_observations": exclusions,
            }
        try:
            result = await asyncio.to_thread(
                train_transaction_avm,
                records,
                seed=seed,
                n_estimators=n_estimators,
            )
        except ValuationDataError as exc:
            # An empty or non-groupable history is an expected pre-production
            # state. Return a machine-readable scorecard instead of creating a
            # partial artifact or turning the preparation command into a 500.
            return {
                "candidate_only": True,
                "promotion_status": "not_ready",
                "reason": str(exc),
                "eligible_observations": len(records),
                "excluded_observations": exclusions,
            }
        result["excluded_observations"] = exclusions
        result["candidate_only"] = True
        return result


def _as_avm_training_record(source: dict[str, Any]) -> SimpleNamespace:
    """Use the established AVM feature adapter, with a real sale as its label."""
    estate = _as_existing_estate(source)
    estate.predictions = SimpleNamespace(suggested_price=source["last_sale_price"])
    return estate
