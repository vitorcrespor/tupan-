"""Offline preparation of global market intelligence and AVM artifacts."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable, Iterator

from backend.repositories.platform_intelligence import PlatformIntelligenceRepository
from backend.services.avm_runtime import _as_existing_estate
from backend.services.heatmap_precompute import _aggregate_sources
from backend.services.market_heat import INPUT_VERSION as MARKET_HEAT_INPUT_VERSION, calculate_market_heat
from backend.services.liquidity_survival import attach_h3_liquidity, train_liquidity_survival_model
from backend.services.market_snapshot import market_snapshot_observations


@dataclass(frozen=True)
class PlatformHeatmapRefresh:
    source_estate_count: int
    sale_source_count: int
    aggregate_count: int
    heat_cell_count: int
    liquidity_cell_count: int
    h3_resolution: int
    period_start: date
    period_end: date


class PlatformIntelligenceService:
    """Runs only from a deployment/ingestion process, never an HTTP request."""

    def __init__(self, repository: PlatformIntelligenceRepository | None = None) -> None:
        self._repository = repository or PlatformIntelligenceRepository()

    async def refresh_heatmap(self, *, h3_resolution: int = 9, allow_empty: bool = False) -> PlatformHeatmapRefresh:
        """Publish one resolution; retained for compatibility with existing CLI callers."""
        return (await self.refresh_heatmaps(h3_resolutions=[h3_resolution], allow_empty=allow_empty))[0]

    async def refresh_heatmaps(
        self,
        *,
        h3_resolutions: Iterable[int],
        allow_empty: bool = False,
    ) -> list[PlatformHeatmapRefresh]:
        """Publish independent global heat snapshots for one or more H3 levels.

        Listing and sale sources are read once, then each resolution is computed
        offline and stored under the same immutable provider version. HTTP reads
        only the resulting aggregate rows.
        """
        resolutions = tuple(dict.fromkeys(int(resolution) for resolution in h3_resolutions))
        if not resolutions:
            raise ValueError("at least one h3_resolution is required")
        if any(not 0 <= resolution <= 15 for resolution in resolutions):
            raise ValueError("h3_resolution must be between 0 and 15.")
        today = date.today()
        await self._repository.start()
        try:
            listing_sources, sale_sources, liquidity_sources = await asyncio.gather(
                self._repository.heatmap_sources(), self._repository.heatmap_sale_sources(),
                self._repository.h3_liquidity_training_sources(),
            )
            publications = []
            for resolution in resolutions:
                base_aggregates = await asyncio.to_thread(
                    _aggregate_sources,
                    listing_sources,
                    resolution=resolution,
                    period_start=today,
                    period_end=today,
                    input_version=MARKET_HEAT_INPUT_VERSION,
                )
                aggregates = await asyncio.to_thread(
                    calculate_market_heat,
                    base_aggregates,
                    sale_sources,
                    h3_resolution=resolution,
                    as_of=today,
                )
                aggregates = await asyncio.to_thread(
                    attach_h3_liquidity,
                    aggregates,
                    liquidity_sources,
                    h3_resolution=resolution,
                    as_of=today,
                )
                observations = await asyncio.to_thread(
                    market_snapshot_observations,
                    aggregates,
                    observed_on=today,
                    source_reference=f"heatmap:{MARKET_HEAT_INPUT_VERSION}:h3-{resolution}",
                )
                # City and global metrics use the canonical resolution 9. Other
                # requested resolutions remain valuable for exact H3 history,
                # but must not compete to become a second city/global source.
                if resolution != 9:
                    observations = [row for row in observations if row["h3_index"] is not None]
                published = await self._repository.replace_platform_heatmap(
                    aggregates,
                    allow_empty=allow_empty,
                    h3_resolution=resolution,
                    input_version=MARKET_HEAT_INPUT_VERSION,
                    market_observations=observations,
                )
                publications.append(PlatformHeatmapRefresh(
                    source_estate_count=len(listing_sources), sale_source_count=len(sale_sources),
                    aggregate_count=published,
                    heat_cell_count=sum(item["metrics"].get("market_heat") is not None for item in aggregates),
                    liquidity_cell_count=sum(
                        any(
                            details.get("score") is not None
                            for details in item["metrics"].get("liquidity_by_horizon", {}).values()
                        )
                        for item in aggregates
                    ),
                    h3_resolution=resolution, period_start=today, period_end=today,
                ))
            return publications
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

    async def publish_liquidity_survival_model(self) -> dict[str, Any]:
        """Train and publish the global listing-liquidity artifact offline."""
        await self._repository.start()
        try:
            sources = await self._repository.liquidity_training_sources()
            artifact = await asyncio.to_thread(train_liquidity_survival_model, sources)
            if not artifact["strata"]:
                return {
                    "publication_status": "not_ready",
                    "reason": "insufficient_observed_listing_and_sale_support",
                    "source_observation_count": artifact["source_observation_count"],
                    "event_count": artifact["event_count"],
                }
            await self._repository.publish_liquidity_survival_model(artifact)
            return {
                "publication_status": "published",
                "model_version": artifact["model_version"],
                "trained_as_of": artifact["trained_as_of"],
                "source_observation_count": artifact["source_observation_count"],
                "event_count": artifact["event_count"],
                "supported_strata": len(artifact["strata"]),
            }
        finally:
            await self._repository.close()

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

    async def preview_itbi_campinas_observations(
        self,
        *,
        source: Path | None = None,
        geocode_cache: Path | None = None,
    ) -> dict[str, Any]:
        """Read curated training observations without network access or writes."""
        return await asyncio.to_thread(
            _preview_itbi_campinas_observations,
            source=source,
            geocode_cache=geocode_cache,
        )

    async def import_itbi_campinas_observations(
        self,
        *,
        source: Path | None = None,
        geocode_cache: Path | None = None,
    ) -> dict[str, Any]:
        """Import a reviewed ITBI workbook into the training-only store.

        Geocodes are read exclusively from the local cache. This command does
        not call Google, create estates, publish a model or expose observations
        through request-time APIs.
        """
        # Validate the complete source before the first write. The second pass
        # is intentional: it keeps large, lineage-rich payloads bounded while
        # avoiding a partial import caused by a malformed later workbook row.
        report = await self.preview_itbi_campinas_observations(
            source=source,
            geocode_cache=geocode_cache,
        )
        await self._repository.start()
        try:
            imported_count = 0
            async with self._repository.transaction() as connection:
                for observations in _iter_itbi_campinas_observation_batches(
                    source=source,
                    geocode_cache=geocode_cache,
                ):
                    imported_count += await self._repository.upsert_valuation_observations(
                        observations,
                        connection=connection,
                    )
        finally:
            await self._repository.close()
        return {
            **report,
            "imported_observation_count": imported_count,
            "target": "valuation_observations",
            "network_enrichment": "not_called",
            "promotion_status": "unchanged",
        }


def _as_avm_training_record(source: dict[str, Any]) -> SimpleNamespace:
    """Use the established AVM feature adapter, with a real sale as its label."""
    estate = _as_existing_estate(source)
    estate.predictions = SimpleNamespace(suggested_price=source["last_sale_price"])
    return estate


def _iter_itbi_campinas_observation_batches(
    *,
    source: Path | None,
    geocode_cache: Path | None,
    batch_size: int = 1_000,
) -> Iterator[list[dict[str, Any]]]:
    """Yield bounded observation batches from the local structured workbook."""
    import pandas as pd

    from train.itbi_campinas_data import (
        DEFAULT_GEOCODE_CACHE,
        DEFAULT_SOURCE,
        build_observations,
        load_geocode_cache,
    )

    source_path = source or DEFAULT_SOURCE
    cache_path = geocode_cache or DEFAULT_GEOCODE_CACHE
    if not source_path.is_file():
        raise FileNotFoundError(f"ITBI source workbook not found: {source_path.name}")
    if not cache_path.is_file():
        raise FileNotFoundError(f"ITBI geocode cache not found: {cache_path.name}")
    if batch_size < 1:
        raise ValueError("batch_size must be positive")
    frame = pd.read_excel(source_path, sheet_name="Dados Limpos")
    geocodes = load_geocode_cache(cache_path)
    for offset in range(0, len(frame), batch_size):
        observations, _counts = build_observations(
            frame.iloc[offset: offset + batch_size],
            geocodes=geocodes,
        )
        if observations:
            yield observations


def _preview_itbi_campinas_observations(
    *,
    source: Path | None,
    geocode_cache: Path | None,
) -> dict[str, Any]:
    """Validate and count all batches without keeping their rows in memory."""
    import pandas as pd

    from train.itbi_campinas_data import DEFAULT_GEOCODE_CACHE, DEFAULT_SOURCE, build_observations, load_geocode_cache

    source_path = source or DEFAULT_SOURCE
    cache_path = geocode_cache or DEFAULT_GEOCODE_CACHE
    if not source_path.is_file():
        raise FileNotFoundError(f"ITBI source workbook not found: {source_path.name}")
    if not cache_path.is_file():
        raise FileNotFoundError(f"ITBI geocode cache not found: {cache_path.name}")
    frame = pd.read_excel(source_path, sheet_name="Dados Limpos")
    geocodes = load_geocode_cache(cache_path)
    totals = {"source_rows": 0, "mapped_rows": 0, "geocoded_rows": 0, "missing_geocodes": 0}
    for offset in range(0, len(frame), 1_000):
        _observations, counts = build_observations(frame.iloc[offset: offset + 1_000], geocodes=geocodes)
        for key in totals:
            totals[key] += int(counts.get(key, 0))
    source_version = "ITBI_Campinas_2021_2026_LIMPO+GoogleGeocoding:v2" if geocodes else "ITBI_Campinas_2021_2026_LIMPO:v1"
    return {
        **totals,
        "source_name": source_path.name,
        "geocode_cache_name": cache_path.name,
        "geocode_cache_entries": len(geocodes),
        "source_id": "itbi_campinas",
        "source_version": source_version,
        "preview_only": True,
    }
