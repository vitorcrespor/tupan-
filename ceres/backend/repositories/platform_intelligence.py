"""Database-only input/output boundary for platform-level intelligence.

This repository is deliberately unavailable to HTTP request handlers.  Its
separate PostgreSQL role reads the minimum source columns across the database
and publishes only aggregate ``scope = platform`` records.
"""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from datetime import date
from typing import Any, AsyncIterator
from uuid import NAMESPACE_URL, uuid4, uuid5

from backend.services.errors import InsufficientDataError, UnavailableError


class PlatformIntelligenceRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or os.getenv("PLATFORM_INTELLIGENCE_DATABASE_URL", "").strip()
        self._pool: Any | None = None

    async def start(self) -> None:
        if self._pool is not None:
            return
        if not self._database_url:
            raise UnavailableError(
                "Platform intelligence storage is not configured.",
                details={"reason": "platform_intelligence_database_url_missing"},
            )
        try:
            import asyncpg

            self._pool = await asyncpg.create_pool(self._database_url, min_size=1, max_size=2)
        except ImportError as exc:
            raise UnavailableError("The platform intelligence database dependency is unavailable.") from exc
        except Exception as exc:
            raise UnavailableError(
                "Platform intelligence storage could not be reached.",
                details={"reason": "platform_intelligence_database_unavailable"},
            ) from exc

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[Any]:
        if self._pool is None:
            raise RuntimeError("PlatformIntelligenceRepository.start() must be called first.")
        async with self._pool.acquire() as connection:
            async with connection.transaction():
                yield connection

    async def heatmap_sources(self) -> list[dict[str, Any]]:
        """Read active global listings for an aggregate-only publication."""
        async with self.transaction() as connection:
            rows = await connection.fetch(
                """SELECT ST_Y(location::geometry) AS latitude, ST_X(location::geometry) AS longitude,
                          asking_price, price_per_m2, area_m2, days_on_market, city, area
                   FROM estates
                   WHERE status = 'active' AND location IS NOT NULL
                     AND COALESCE(attributes->>'is_demo', 'false') <> 'true'
                     AND COALESCE(attributes->>'training_allowed', 'true') <> 'false'"""
            )
        return [dict(row) for row in rows]

    async def heatmap_sale_sources(self) -> list[dict[str, Any]]:
        """Read dated global sales used only as aggregate heat evidence.

        This trusted platform process never exposes these records or their
        tenant identifiers to an HTTP caller. Synthetic/demo and explicitly
        excluded training records remain outside the global publication.
        """
        async with self.transaction() as connection:
            rows = await connection.fetch(
                """SELECT ST_Y(location::geometry) AS latitude, ST_X(location::geometry) AS longitude,
                          last_sale_date, last_sale_price
                   FROM estates
                   WHERE status = 'sold' AND location IS NOT NULL
                     AND last_sale_date IS NOT NULL
                     AND last_sale_price IS NOT NULL AND last_sale_price > 0
                     AND last_sale_date <= CURRENT_DATE
                     AND COALESCE(attributes->>'is_demo', 'false') <> 'true'
                     AND COALESCE(attributes->>'training_allowed', 'true') <> 'false'"""
            )
        return [dict(row) for row in rows]

    async def avm_training_sources(self) -> list[dict[str, Any]]:
        async with self.transaction() as connection:
            rows = await connection.fetch(
                """SELECT property_type, city, area, rooms, bathrooms, parking_spaces, area_m2,
                          age_years, days_on_market, exclusive, attributes, last_sale_price
                   FROM estates
                   WHERE status = 'sold' AND last_sale_price IS NOT NULL AND last_sale_price > 0
                     AND COALESCE(attributes->>'is_demo', 'false') <> 'true'
                     AND COALESCE(attributes->>'training_allowed', 'true') <> 'false'"""
            )
        return [dict(row) for row in rows]

    async def liquidity_training_sources(self) -> list[dict[str, Any]]:
        """Read the minimal global inputs for right-censored listing survival.

        Raw source rows never leave the trusted offline worker.  The published
        artifact retains only aggregate Kaplan-Meier strata and event counts.
        """
        async with self.transaction() as connection:
            rows = await connection.fetch(
                """SELECT status, property_type, city, area, asking_price, price_per_m2,
                          days_on_market, listed_since, last_sale_date
                   FROM estates
                   WHERE status IN ('active', 'sold')
                     AND COALESCE(attributes->>'is_demo', 'false') <> 'true'
                     AND COALESCE(attributes->>'training_allowed', 'true') <> 'false'"""
            )
        return [dict(row) for row in rows]

    async def h3_liquidity_training_sources(self) -> list[dict[str, Any]]:
        """Read geocoded survival inputs for exact-cell H3 liquidity.

        This is intentionally separate from ``liquidity_training_sources`` so
        publishing H3 cells does not narrow the support of the existing global
        estate-level survival artifact to geocoded observations only.
        """
        async with self.transaction() as connection:
            rows = await connection.fetch(
                """SELECT status, property_type, city, area, asking_price, price_per_m2,
                          days_on_market, listed_since, last_sale_date,
                          ST_Y(location::geometry) AS latitude,
                          ST_X(location::geometry) AS longitude
                   FROM estates
                   WHERE status IN ('active', 'sold')
                     AND location IS NOT NULL
                     AND COALESCE(attributes->>'is_demo', 'false') <> 'true'
                     AND COALESCE(attributes->>'training_allowed', 'true') <> 'false'"""
            )
        return [dict(row) for row in rows]

    async def publish_liquidity_survival_model(self, artifact: dict[str, Any]) -> None:
        """Atomically replace the current global survival artifact."""
        required = ("model_version", "trained_as_of", "source_observation_count", "event_count", "strata")
        if any(key not in artifact for key in required):
            raise ValueError("liquidity survival artifact is incomplete")
        async with self.transaction() as connection:
            await connection.execute("DELETE FROM liquidity_survival_models WHERE scope = 'platform'")
            await connection.execute(
                """INSERT INTO liquidity_survival_models (
                       id, scope, model_version, trained_as_of, artifact,
                       source_observation_count, event_count
                   ) VALUES ($1, 'platform', $2, $3::date, $4::jsonb, $5, $6)""",
                str(uuid4()),
                str(artifact["model_version"]),
                str(artifact["trained_as_of"]),
                json.dumps(artifact),
                int(artifact["source_observation_count"]),
                int(artifact["event_count"]),
            )

    async def valuation_observations(self, *, target_kind: str = "transaction") -> list[dict[str, Any]]:
        """Read the explicit, point-in-time AVM contract for trusted training.

        The platform role cannot fall back to a live tenant estate snapshot:
        absence of this table/data is a migration or ingestion problem, not a
        reason to silently train on asking prices or current estimates.
        """
        if target_kind not in {"transaction", "asking"}:
            raise ValueError("target_kind must be transaction or asking")
        async with self.transaction() as connection:
            rows = await connection.fetch(
                """SELECT property_id, transaction_id, listing_cluster_id,
                          valuation_time, available_at, feature_as_of,
                          source_id, source_version, target_kind,
                          transaction_nature, price_brl, features,
                          feature_lineage, verified, training_allowed
                   FROM valuation_observations
                   WHERE target_kind = $1
                     AND verified = TRUE
                     AND training_allowed = TRUE
                   ORDER BY valuation_time, transaction_id""",
                target_kind,
            )
        result = []
        for row in rows:
            value = dict(row)
            for key in ("features", "feature_lineage"):
                if isinstance(value.get(key), str):
                    value[key] = json.loads(value[key])
            value["verified"] = bool(value.get("verified"))
            value["training_allowed"] = bool(value.get("training_allowed"))
            result.append(value)
        return result

    async def upsert_valuation_observations(
        self,
        rows: list[dict[str, Any]],
        *,
        connection: Any | None = None,
    ) -> int:
        """Persist verified global transaction observations idempotently.

        This is an offline-only path. It accepts the narrow observation
        contract produced by a curated importer and never receives tenant
        estates, client IDs or an arbitrary SQL payload.
        """
        if not rows:
            return 0
        payloads = []
        for row in rows:
            required = (
                "property_id", "transaction_id", "valuation_time", "available_at",
                "feature_as_of", "source_id", "source_version", "sale_price_brl",
                "transaction_nature", "features", "feature_lineage",
            )
            if any(row.get(field) in (None, "") for field in required):
                raise ValueError("Valuation observation is missing a required field.")
            if row.get("transaction_nature") != "arm_length":
                raise ValueError("Only arm-length transactions may be ingested.")
            if row.get("verified") is not True or row.get("training_allowed") is not True:
                raise ValueError("Only verified, training-allowed observations may be ingested.")
            try:
                price_brl = float(row["sale_price_brl"])
            except (TypeError, ValueError) as exc:
                raise ValueError("Valuation observation price must be numeric.") from exc
            if price_brl <= 0:
                raise ValueError("Valuation observation price must be positive.")
            features = row["features"]
            lineage = row["feature_lineage"]
            if not isinstance(features, dict) or not isinstance(lineage, dict):
                raise ValueError("Valuation features and lineage must be objects.")
            source_id = str(row["source_id"])
            transaction_id = str(row["transaction_id"])
            observation_id = uuid5(
                NAMESPACE_URL,
                f"tupan-valuation-observation:{source_id}:{transaction_id}",
            )
            payloads.append((
                str(observation_id), str(row["property_id"]), transaction_id,
                row.get("listing_cluster_id"), str(row["valuation_time"]), str(row["available_at"]),
                str(row["feature_as_of"]), source_id, str(row["source_version"]), price_brl,
                json.dumps(features), json.dumps(lineage),
            ))

        statement = """INSERT INTO valuation_observations (
                       observation_id, property_id, transaction_id, listing_cluster_id,
                       valuation_time, available_at, feature_as_of,
                       source_id, source_version, target_kind, transaction_nature,
                       price_brl, features, feature_lineage, verified, training_allowed
                   ) VALUES (
                       $1, $2, $3, $4, $5::timestamptz, $6::timestamptz, $7::timestamptz,
                       $8, $9, 'transaction', 'arm_length', $10, $11::jsonb, $12::jsonb, TRUE, TRUE
                   )
                   ON CONFLICT (transaction_id) DO UPDATE SET
                       property_id = EXCLUDED.property_id,
                       listing_cluster_id = EXCLUDED.listing_cluster_id,
                       valuation_time = EXCLUDED.valuation_time,
                       available_at = EXCLUDED.available_at,
                       feature_as_of = EXCLUDED.feature_as_of,
                       source_version = EXCLUDED.source_version,
                       price_brl = EXCLUDED.price_brl,
                       features = EXCLUDED.features,
                       feature_lineage = EXCLUDED.feature_lineage,
                       verified = TRUE,
                       training_allowed = TRUE
                   WHERE valuation_observations.source_id = EXCLUDED.source_id"""
        if connection is not None:
            await connection.executemany(statement, payloads)
        else:
            async with self.transaction() as transaction:
                await transaction.executemany(statement, payloads)
        return len(payloads)

    async def replace_platform_heatmap(
        self,
        rows: list[dict[str, Any]],
        *,
        allow_empty: bool,
        h3_resolution: int,
        input_version: str,
        market_observations: list[dict[str, Any]] | None = None,
    ) -> int:
        if not 0 <= h3_resolution <= 15:
            raise ValueError("h3_resolution must be between 0 and 15")
        if not input_version:
            raise ValueError("input_version is required")
        if any(row.get("h3_resolution") != h3_resolution or row.get("input_version") != input_version for row in rows):
            raise ValueError("Platform heatmap rows must match their publication resolution and input version")
        async with self.transaction() as connection:
            existing_count = int(
                await connection.fetchval(
                    """SELECT count(*) FROM heatmap_aggregates
                       WHERE scope = 'platform' AND h3_resolution = $1 AND input_version = $2""",
                    h3_resolution, input_version,
                ) or 0
            )
            if not rows and existing_count and not allow_empty:
                raise InsufficientDataError(
                    "Refusing to replace an existing platform heatmap with an empty source set.",
                    details={"reason": "empty_platform_heatmap_source", "existing_cell_count": existing_count},
                )
            # A publication is independent for every H3 resolution and input
            # version. Replacing resolution 8 must not delete 9/10, nor must a
            # market-heat refresh delete an unrelated transaction aggregate.
            await connection.execute(
                """DELETE FROM heatmap_aggregates
                   WHERE scope = 'platform' AND h3_resolution = $1 AND input_version = $2""",
                h3_resolution, input_version,
            )
            for row in rows:
                await connection.execute(
                    """INSERT INTO heatmap_aggregates (
                           id, organization_id, scope, h3_index, h3_resolution, period_start, period_end,
                           city, area, boundary, center, metrics, input_version, calculated_at
                       ) VALUES (
                           $1, NULL, 'platform', $2, $3, $4, $5, $6, $7,
                           ST_SetSRID(ST_GeomFromGeoJSON($8), 4326)::geography,
                           ST_SetSRID(ST_GeomFromGeoJSON($9), 4326)::geography,
                           $10::jsonb, $11, now()
                       )
                       ON CONFLICT (h3_index, h3_resolution, period_start, period_end, input_version)
                         WHERE scope = 'platform'
                       DO UPDATE SET city = EXCLUDED.city, area = EXCLUDED.area,
                                     boundary = EXCLUDED.boundary, center = EXCLUDED.center,
                                     metrics = EXCLUDED.metrics, calculated_at = now()""",
                    str(uuid4()), row["h3_index"], row["h3_resolution"], row["period_start"], row["period_end"],
                    row.get("city"), row.get("area"), json.dumps(row["boundary"]), json.dumps(row["center"]),
                    json.dumps(row["metrics"]), row["input_version"],
                )
            if market_observations:
                await _upsert_platform_market_observations(connection, market_observations)
        return len(rows)

    async def publish_market_observations(self, rows: list[dict[str, Any]]) -> int:
        """Persist aggregate-only market observations from an offline publication.

        The identifier is deterministic for one published scope, metric, date
        and source. Re-running a publisher updates that exact observation
        rather than creating an ambiguous second point, while a new source
        revision remains independently traceable through ``source_reference``.
        """
        if not rows:
            return 0

        async with self.transaction() as connection:
            await _upsert_platform_market_observations(connection, rows)
        return len(rows)


async def _upsert_platform_market_observations(connection: Any, rows: list[dict[str, Any]]) -> None:
    """Use the heatmap transaction when a publication includes its history."""
    payloads = []
    for row in rows:
        required = ("metric", "value", "unit", "observed_on", "source_name")
        if any(row.get(field) is None for field in required):
            raise ValueError("Published market observations require metric, value, unit, date and source.")
        dimensions = row.get("dimensions") or {}
        identity = {
            "metric": str(row["metric"]),
            "observed_on": str(row["observed_on"]),
            "source_name": str(row["source_name"]),
            "source_reference": row.get("source_reference"),
            "property_type": row.get("property_type"),
            "city": row.get("city"),
            "area": row.get("area"),
            "h3_index": row.get("h3_index"),
            "dimensions": dimensions,
        }
        observation_id = uuid5(
            NAMESPACE_URL,
            "tupan-platform-market-observation:" + json.dumps(
                identity, sort_keys=True, separators=(",", ":"), ensure_ascii=True,
            ),
        )
        payloads.append((
            str(observation_id), row["observed_on"], row["metric"], row["value"], row["unit"],
            row.get("property_type"), row.get("city"), row.get("area"), row.get("h3_index"),
            row["source_name"], row.get("source_reference"), json.dumps(dimensions),
        ))
    await connection.executemany(
        """INSERT INTO market_observations (
               id, organization_id, scope, observed_on, metric, value, unit,
               property_type, city, area, h3_index, source_name,
               source_reference, dimensions
           ) VALUES (
               $1, NULL, 'platform', $2::date, $3, $4, $5,
               $6, $7, $8, $9, $10, $11, $12::jsonb
           )
           ON CONFLICT (id) DO UPDATE SET
               value = EXCLUDED.value,
               unit = EXCLUDED.unit,
               source_reference = EXCLUDED.source_reference,
               created_at = now()""",
        payloads,
    )
