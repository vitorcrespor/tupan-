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
from uuid import uuid4

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
        async with self.transaction() as connection:
            rows = await connection.fetch(
                """SELECT ST_Y(location::geometry) AS latitude, ST_X(location::geometry) AS longitude,
                          asking_price, price_per_m2, area_m2, days_on_market, city, area
                   FROM estates
                   WHERE status = 'active' AND location IS NOT NULL"""
            )
        return [dict(row) for row in rows]

    async def avm_training_sources(self) -> list[dict[str, Any]]:
        async with self.transaction() as connection:
            rows = await connection.fetch(
                """SELECT property_type, city, area, rooms, bathrooms, parking_spaces, area_m2,
                          age_years, days_on_market, exclusive, attributes, last_sale_price
                   FROM estates
                   WHERE status = 'sold' AND last_sale_price IS NOT NULL AND last_sale_price > 0"""
            )
        return [dict(row) for row in rows]

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

    async def replace_platform_heatmap(
        self,
        rows: list[dict[str, Any]],
        *,
        allow_empty: bool,
    ) -> int:
        async with self.transaction() as connection:
            existing_count = int(
                await connection.fetchval("SELECT count(*) FROM heatmap_aggregates WHERE scope = 'platform'") or 0
            )
            if not rows and existing_count and not allow_empty:
                raise InsufficientDataError(
                    "Refusing to replace an existing platform heatmap with an empty source set.",
                    details={"reason": "empty_platform_heatmap_source", "existing_cell_count": existing_count},
                )
            await connection.execute("DELETE FROM heatmap_aggregates WHERE scope = 'platform'")
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
        return len(rows)
