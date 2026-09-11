from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, AsyncIterator
from uuid import UUID, uuid4

from backend.services.control_plane import ControlPlaneService
from backend.services.errors import DomainValidationError, NotFoundError


def _record(record: Any) -> dict[str, Any]:
    """Convert asyncpg values into transport-safe API primitives at the boundary."""
    return {
        key: str(value) if isinstance(value, UUID) else value
        for key, value in dict(record).items()
    }


@dataclass(frozen=True)
class TenantContext:
    """Identity derived by the server from the authenticated session."""
    organization_id: str
    user_id: str
    role: str

    @classmethod
    def from_principal(cls, principal: dict[str, Any]) -> "TenantContext":
        return cls(str(principal["organization_id"]), str(principal["id"]), str(principal["role"]))


class TenantDataRepository:
    """PostgreSQL source-of-truth access with transaction-local tenant RLS.

    Each tenant query has two protections: an explicit organization predicate
    and the ``app.organization_id`` RLS context set inside this transaction.
    """

    def __init__(self, control_plane: ControlPlaneService) -> None:
        self._control_plane = control_plane

    @asynccontextmanager
    async def transaction(self, context: TenantContext) -> AsyncIterator[Any]:
        pool = await self._control_plane._database()
        async with pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute("SELECT set_config('app.organization_id', $1, true)", context.organization_id)
                yield connection

    async def list_portfolios(self, context: TenantContext) -> list[dict[str, Any]]:
        async with self.transaction(context) as connection:
            rows = await connection.fetch(
                """SELECT id, name, description, target_commission, created_by_user_id, created_at, updated_at
                   FROM portfolios WHERE organization_id = $1 ORDER BY created_at DESC""",
                context.organization_id,
            )
        return [_record(row) for row in rows]

    async def get_portfolio(self, context: TenantContext, portfolio_id: str) -> dict[str, Any]:
        async with self.transaction(context) as connection:
            row = await connection.fetchrow(
                """SELECT id, name, description, target_commission, created_by_user_id, created_at, updated_at
                   FROM portfolios WHERE id = $1 AND organization_id = $2""",
                portfolio_id, context.organization_id,
            )
        if row is None:
            raise NotFoundError("Portfolio not found.")
        return _record(row)

    async def create_portfolio(self, context: TenantContext, *, name: str, description: str | None, target_commission: float | None) -> dict[str, Any]:
        async with self.transaction(context) as connection:
            row = await connection.fetchrow(
                """INSERT INTO portfolios (id, organization_id, name, description, target_commission, created_by_user_id)
                   VALUES ($1, $2, $3, $4, $5, $6)
                   RETURNING id, name, description, target_commission, created_by_user_id, created_at, updated_at""",
                str(uuid4()), context.organization_id, name.strip(), description, target_commission, context.user_id,
            )
        return _record(row)
    async def list_estates(self, context: TenantContext, *, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        async with self.transaction(context) as connection:
            rows = await connection.fetch(
                """SELECT id, portfolio_id, title, property_type, status, asking_price, area_m2,
                          price_per_m2, rooms, bathrooms, parking_spaces, city, area, address,
                          ST_Y(location::geometry) AS latitude, ST_X(location::geometry) AS longitude,
                          created_at, updated_at
                   FROM estates WHERE organization_id = $1
                   ORDER BY created_at DESC LIMIT $2 OFFSET $3""",
                context.organization_id, limit, offset,
            )
        return [_record(row) for row in rows]

    async def get_estate(self, context: TenantContext, estate_id: str) -> dict[str, Any]:
        async with self.transaction(context) as connection:
            row = await connection.fetchrow(
                """SELECT id, portfolio_id, title, summary, property_type, status, exclusive,
                          asking_price, last_sale_price, estimated_price, area_m2, price_per_m2,
                          rooms, bathrooms, parking_spaces, age_years, days_on_market,
                          listed_since, last_sale_date, address, city, area, state, postal_code,
                          ST_Y(location::geometry) AS latitude, ST_X(location::geometry) AS longitude,
                          attributes, created_at, updated_at
                   FROM estates WHERE id = $1 AND organization_id = $2""",
                estate_id, context.organization_id,
            )
        if row is None:
            raise NotFoundError("Estate not found.")
        return _record(row)

    async def create_estate(self, context: TenantContext, values: dict[str, Any]) -> dict[str, Any]:
        latitude, longitude = values.get("latitude"), values.get("longitude")
        if (latitude is None) != (longitude is None):
            raise DomainValidationError("Latitude and longitude must be supplied together.")
        estate_id = str(uuid4())
        async with self.transaction(context) as connection:
            if values.get("portfolio_id") is not None:
                portfolio = await connection.fetchval(
                    "SELECT 1 FROM portfolios WHERE id = $1 AND organization_id = $2",
                    values["portfolio_id"], context.organization_id,
                )
                if not portfolio:
                    raise NotFoundError("Portfolio not found.")
            row = await connection.fetchrow(
                """INSERT INTO estates (
                    id, organization_id, portfolio_id, external_id, source_name, status, title,
                    summary, property_type, exclusive, asking_price, last_sale_price, estimated_price,
                    area_m2, price_per_m2, rooms, bathrooms, parking_spaces, age_years, days_on_market,
                    listed_since, last_sale_date, address, city, area, state, postal_code, location, attributes
                ) VALUES (
                    $1,$2,$3,$4,$5,$6::estate_status,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,
                    $21,$22,$23,$24,$25,$26,$27,
                    CASE WHEN $28::double precision IS NULL THEN NULL
                         ELSE ST_SetSRID(ST_MakePoint($29::double precision,$28::double precision),4326)::geography END,
                    $30::jsonb
                ) RETURNING id""",
                estate_id, context.organization_id, values.get("portfolio_id"), values.get("external_id"),
                values.get("source_name"), values.get("status", "active"), values.get("title"),
                values.get("summary"), values.get("property_type"), values.get("exclusive"),
                values.get("asking_price"), values.get("last_sale_price"), values.get("estimated_price"),
                values.get("area_m2"), values.get("price_per_m2"), values.get("rooms"), values.get("bathrooms"),
                values.get("parking_spaces"), values.get("age_years"), values.get("days_on_market"),
                values.get("listed_since"), values.get("last_sale_date"), values.get("address"), values.get("city"),
                values.get("area"), values.get("state"), values.get("postal_code"), latitude, longitude,
                __import__("json").dumps(values.get("attributes") or {}),
            )
        return await self.get_estate(context, str(row["id"]))

    async def update_estate(self, context: TenantContext, estate_id: str, values: dict[str, Any]) -> dict[str, Any]:
        permitted = {"title", "summary", "property_type", "status", "asking_price", "estimated_price", "area_m2", "price_per_m2", "rooms", "bathrooms", "parking_spaces", "city", "area", "address", "attributes"}
        values = {key: value for key, value in values.items() if key in permitted}
        if not values:
            return await self.get_estate(context, estate_id)
        fields, parameters = [], [estate_id, context.organization_id]
        for position, (field, value) in enumerate(values.items(), start=3):
            fields.append(f"{field} = ${position}" + ("::jsonb" if field == "attributes" else ""))
            parameters.append(__import__("json").dumps(value or {}) if field == "attributes" else value)
        fields.append("updated_at = now()")
        async with self.transaction(context) as connection:
            result = await connection.execute(
                f"UPDATE estates SET {', '.join(fields)} WHERE id = $1 AND organization_id = $2", *parameters
            )
        if result.endswith("0"):
            raise NotFoundError("Estate not found.")
        return await self.get_estate(context, estate_id)

    async def move_estate_to_portfolio(self, context: TenantContext, estate_id: str, portfolio_id: str | None) -> dict[str, Any]:
        async with self.transaction(context) as connection:
            if portfolio_id is not None:
                portfolio = await connection.fetchval(
                    "SELECT 1 FROM portfolios WHERE id = $1 AND organization_id = $2", portfolio_id, context.organization_id
                )
                if not portfolio:
                    raise NotFoundError("Portfolio not found.")
            result = await connection.execute(
                "UPDATE estates SET portfolio_id = $3, updated_at = now() WHERE id = $1 AND organization_id = $2",
                estate_id, context.organization_id, portfolio_id,
            )
        if result.endswith("0"):
            raise NotFoundError("Estate not found.")
        return await self.get_estate(context, estate_id)

    async def delete_estate(self, context: TenantContext, estate_id: str) -> None:
        async with self.transaction(context) as connection:
            result = await connection.execute(
                "DELETE FROM estates WHERE id = $1 AND organization_id = $2", estate_id, context.organization_id
            )
        if result.endswith("0"):
            raise NotFoundError("Estate not found.")

    async def create_job(self, context: TenantContext, *, job_type: str, payload: dict[str, Any], idempotency_key: str, input_version: str | None = None) -> dict[str, Any]:
        """Persist one idempotent tenant-owned job and return its current state."""
        async with self.transaction(context) as connection:
            row = await connection.fetchrow(
                """INSERT INTO jobs (id, organization_id, requested_by_user_id, job_type, idempotency_key, payload, input_version)
                   VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7)
                   ON CONFLICT (organization_id, job_type, idempotency_key) WHERE idempotency_key IS NOT NULL
                   DO UPDATE SET updated_at = now()
                   RETURNING id AS job_id, organization_id, requested_by_user_id AS user_id, job_type,
                             status::text AS status, progress, input_version, attempt_count, max_attempts,
                             result_reference, result, error, created_at, started_at, completed_at""",
                str(uuid4()), context.organization_id, context.user_id, job_type, idempotency_key,
                __import__("json").dumps(payload), input_version,
            )
        return _record(row)

    async def get_job(self, context: TenantContext, job_id: str) -> dict[str, Any]:
        async with self.transaction(context) as connection:
            row = await connection.fetchrow(
                """SELECT id AS job_id, organization_id, requested_by_user_id AS user_id, job_type,
                          status::text AS status, progress, result_reference, result, error, input_version,
                          attempt_count, max_attempts, created_at, started_at, completed_at
                   FROM jobs WHERE id = $1 AND organization_id = $2""",
                job_id, context.organization_id,
            )
        if row is None:
            raise NotFoundError("Job not found.")
        return _record(row)
    async def list_estate_comparables(
        self,
        context: TenantContext,
        estate: dict[str, Any],
        *,
        radius_meters: int,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Return nearby peer listings using PostGIS when coordinates exist."""
        latitude, longitude = estate.get("latitude"), estate.get("longitude")
        common_columns = """id, title, property_type, asking_price, estimated_price, area_m2, price_per_m2,
                            rooms, bathrooms, parking_spaces, days_on_market, city, area"""
        async with self.transaction(context) as connection:
            if latitude is not None and longitude is not None:
                rows = await connection.fetch(
                    f"""SELECT {common_columns},
                                ST_Distance(location, ST_SetSRID(ST_MakePoint($3, $4), 4326)::geography) AS distance_meters
                         FROM estates
                         WHERE organization_id = $1 AND id <> $2 AND status = 'active'
                           AND ($5::text IS NULL OR property_type = $5)
                           AND location IS NOT NULL
                           AND ST_DWithin(location, ST_SetSRID(ST_MakePoint($3, $4), 4326)::geography, $6)
                         ORDER BY distance_meters ASC, created_at DESC LIMIT $7""",
                    context.organization_id, estate["id"], longitude, latitude,
                    estate.get("property_type"), radius_meters, limit,
                )
            else:
                rows = await connection.fetch(
                    f"""SELECT {common_columns}, NULL::double precision AS distance_meters
                         FROM estates
                         WHERE organization_id = $1 AND id <> $2 AND status = 'active'
                           AND ($3::text IS NULL OR property_type = $3)
                           AND city IS NOT DISTINCT FROM $4 AND area IS NOT DISTINCT FROM $5
                         ORDER BY created_at DESC LIMIT $6""",
                    context.organization_id, estate["id"], estate.get("property_type"),
                    estate.get("city"), estate.get("area"), limit,
                )
        return [_record(row) for row in rows]

    async def estate_local_statistics(
        self,
        context: TenantContext,
        estate: dict[str, Any],
        *,
        radius_meters: int,
    ) -> dict[str, Any]:
        """Run an aggregate in PostgreSQL instead of pulling every peer into Python."""
        latitude, longitude = estate.get("latitude"), estate.get("longitude")
        aggregate = """COUNT(*)::integer AS comparable_count,
                         AVG(asking_price) AS average_asking_price,
                         percentile_cont(0.5) WITHIN GROUP (ORDER BY asking_price) AS median_asking_price,
                         AVG(price_per_m2) AS average_price_per_m2,
                         percentile_cont(0.5) WITHIN GROUP (ORDER BY price_per_m2) AS median_price_per_m2,
                         AVG(days_on_market) AS average_days_on_market"""
        async with self.transaction(context) as connection:
            if latitude is not None and longitude is not None:
                row = await connection.fetchrow(
                    f"""SELECT {aggregate} FROM estates
                         WHERE organization_id = $1 AND id <> $2 AND status = 'active'
                           AND ($5::text IS NULL OR property_type = $5) AND location IS NOT NULL
                           AND ST_DWithin(location, ST_SetSRID(ST_MakePoint($3, $4), 4326)::geography, $6)""",
                    context.organization_id, estate["id"], longitude, latitude,
                    estate.get("property_type"), radius_meters,
                )
            else:
                row = await connection.fetchrow(
                    f"""SELECT {aggregate} FROM estates
                         WHERE organization_id = $1 AND id <> $2 AND status = 'active'
                           AND ($3::text IS NULL OR property_type = $3)
                           AND city IS NOT DISTINCT FROM $4 AND area IS NOT DISTINCT FROM $5""",
                    context.organization_id, estate["id"], estate.get("property_type"),
                    estate.get("city"), estate.get("area"),
                )
        return _record(row or {"comparable_count": 0})

    async def estate_market_context(self, context: TenantContext, estate: dict[str, Any]) -> list[dict[str, Any]]:
        """Fetch the newest authorized market observation for every metric."""
        async with self.transaction(context) as connection:
            rows = await connection.fetch(
                """SELECT DISTINCT ON (metric) metric, value, unit, observed_on, source_name, scope
                   FROM market_observations
                   WHERE scope = 'platform'
                     AND (city IS NULL OR city = $1)
                     AND (area IS NULL OR area = $2)
                     AND (property_type IS NULL OR property_type = $3)
                   ORDER BY metric, observed_on DESC, created_at DESC""",
                estate.get("city"), estate.get("area"), estate.get("property_type"),
            )
        return [_record(row) for row in rows]

    async def estate_location_metrics(self, context: TenantContext, estate: dict[str, Any]) -> dict[str, Any] | None:
        """Read a precomputed heatmap aggregate; heat is never recalculated in a request."""
        latitude, longitude = estate.get("latitude"), estate.get("longitude")
        async with self.transaction(context) as connection:
            if latitude is not None and longitude is not None:
                row = await connection.fetchrow(
                    """SELECT h3_index, h3_resolution, period_start, period_end, metrics, calculated_at,
                              ST_AsGeoJSON(boundary::geometry) AS boundary, ST_AsGeoJSON(center::geometry) AS center
                       FROM heatmap_aggregates
                       WHERE scope = 'platform' AND boundary IS NOT NULL
                         AND ST_Covers(boundary::geometry, ST_SetSRID(ST_MakePoint($1, $2), 4326))
                       ORDER BY calculated_at DESC LIMIT 1""",
                    longitude, latitude,
                )
            else:
                row = await connection.fetchrow(
                    """SELECT h3_index, h3_resolution, period_start, period_end, metrics, calculated_at,
                              ST_AsGeoJSON(boundary::geometry) AS boundary, ST_AsGeoJSON(center::geometry) AS center
                       FROM heatmap_aggregates
                       WHERE scope = 'platform'
                         AND city IS NOT DISTINCT FROM $1 AND area IS NOT DISTINCT FROM $2
                       ORDER BY calculated_at DESC LIMIT 1""",
                    estate.get("city"), estate.get("area"),
                )
        return _record(row) if row is not None else None

    async def portfolio_valuation_summary(self, context: TenantContext, portfolio_id: str) -> dict[str, Any]:
        async with self.transaction(context) as connection:
            row = await connection.fetchrow(
                """SELECT COUNT(*)::integer AS active_estate_count,
                          COALESCE(SUM(asking_price), 0) AS portfolio_value,
                          COALESCE(SUM(estimated_price), 0) AS estimated_value,
                          AVG(CASE WHEN estimated_price > 0 AND asking_price IS NOT NULL
                                   THEN (asking_price - estimated_price) / estimated_price END) AS average_price_gap
                   FROM estates WHERE organization_id = $1 AND portfolio_id = $2 AND status = 'active'""",
                context.organization_id, portfolio_id,
            )
        return _record(row)

    async def portfolio_geographic_concentration(self, context: TenantContext, portfolio_id: str) -> list[dict[str, Any]]:
        async with self.transaction(context) as connection:
            rows = await connection.fetch(
                """WITH values_by_region AS (
                       SELECT city, area, COUNT(*)::integer AS estate_count, COALESCE(SUM(asking_price), 0) AS portfolio_value
                       FROM estates WHERE organization_id = $1 AND portfolio_id = $2 AND status = 'active'
                       GROUP BY city, area
                   ), totals AS (SELECT COALESCE(SUM(portfolio_value), 0) AS total_value FROM values_by_region)
                   SELECT city, area, estate_count, portfolio_value,
                          CASE WHEN total_value > 0 THEN portfolio_value / total_value ELSE 0 END AS share
                   FROM values_by_region CROSS JOIN totals ORDER BY portfolio_value DESC, estate_count DESC""",
                context.organization_id, portfolio_id,
            )
        return [_record(row) for row in rows]

    async def portfolio_pricing_statistics(self, context: TenantContext, portfolio_id: str) -> dict[str, Any]:
        async with self.transaction(context) as connection:
            row = await connection.fetchrow(
                """SELECT AVG(asking_price) AS average_asking_price,
                          percentile_cont(0.5) WITHIN GROUP (ORDER BY asking_price) AS median_asking_price,
                          AVG(price_per_m2) AS average_price_per_m2,
                          percentile_cont(0.5) WITHIN GROUP (ORDER BY price_per_m2) AS median_price_per_m2,
                          AVG(days_on_market) AS average_days_on_market
                   FROM estates WHERE organization_id = $1 AND portfolio_id = $2 AND status = 'active'""",
                context.organization_id, portfolio_id,
            )
        return _record(row)

    async def portfolio_property_distribution(self, context: TenantContext, portfolio_id: str) -> list[dict[str, Any]]:
        async with self.transaction(context) as connection:
            rows = await connection.fetch(
                """WITH distribution AS (
                       SELECT property_type, COUNT(*)::integer AS estate_count
                       FROM estates WHERE organization_id = $1 AND portfolio_id = $2 AND status = 'active'
                       GROUP BY property_type
                   ), totals AS (SELECT COALESCE(SUM(estate_count), 0) AS total_count FROM distribution)
                   SELECT property_type, estate_count,
                          CASE WHEN total_count > 0 THEN estate_count::double precision / total_count ELSE 0 END AS share
                   FROM distribution CROSS JOIN totals ORDER BY estate_count DESC, property_type""",
                context.organization_id, portfolio_id,
            )
        return [_record(row) for row in rows]

    async def portfolio_market_exposure(self, context: TenantContext, portfolio_id: str) -> list[dict[str, Any]]:
        """Join portfolio regions to latest authorized market observations once."""
        async with self.transaction(context) as connection:
            rows = await connection.fetch(
                """WITH regions AS (
                       SELECT city, area, COUNT(*)::integer AS estate_count
                       FROM estates WHERE organization_id = $1 AND portfolio_id = $2 AND status = 'active'
                       GROUP BY city, area
                   ), latest AS (
                       SELECT DISTINCT ON (city, area, metric) city, area, metric, value, observed_on
                       FROM market_observations
                       WHERE scope = 'platform'
                       ORDER BY city, area, metric, observed_on DESC, created_at DESC
                   )
                   SELECT r.city, r.area, r.estate_count,
                          MAX(l.value) FILTER (WHERE l.metric = 'price_m2') AS average_price_m2,
                          MAX(l.value) FILTER (WHERE l.metric = 'market_heat') AS market_heat,
                          MAX(l.observed_on) AS latest_observed_on
                   FROM regions r LEFT JOIN latest l ON l.city IS NOT DISTINCT FROM r.city AND l.area IS NOT DISTINCT FROM r.area
                   GROUP BY r.city, r.area, r.estate_count ORDER BY r.estate_count DESC""",
                context.organization_id, portfolio_id,
            )
        return [_record(row) for row in rows]

    async def list_heatmap_aggregates(
        self,
        context: TenantContext,
        *,
        h3_resolution: int,
        city: str | None,
        area: str | None,
        period_start: Any | None,
        period_end: Any | None,
    ) -> list[dict[str, Any]]:
        async with self.transaction(context) as connection:
            rows = await connection.fetch(
                """SELECT h3_index, h3_resolution, city, area, period_start, period_end, metrics, input_version,
                          calculated_at, scope, ST_AsGeoJSON(boundary::geometry) AS boundary,
                          ST_AsGeoJSON(center::geometry) AS center
                   FROM heatmap_aggregates
                   WHERE scope = 'platform' AND h3_resolution = $1
                     AND ($2::text IS NULL OR city = $2) AND ($3::text IS NULL OR area = $3)
                     AND ($4::date IS NULL OR period_start >= $4) AND ($5::date IS NULL OR period_end <= $5)
                   ORDER BY calculated_at DESC""",
                h3_resolution, city, area, period_start, period_end,
            )
        return [_record(row) for row in rows]