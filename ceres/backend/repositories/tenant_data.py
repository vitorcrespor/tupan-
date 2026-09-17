from __future__ import annotations

from contextlib import asynccontextmanager
import json
from dataclasses import dataclass
from typing import Any, AsyncIterator
from uuid import UUID, uuid4

from backend.services.control_plane import ControlPlaneService
from backend.services.errors import DomainValidationError, NotFoundError


_JSON_OBJECT_FIELDS = {
    "attributes",
    "error",
    "estimate_provenance",
    "market_metrics",
    "metrics",
    "result",
}

DEFAULT_ESTATE_H3_RESOLUTION = 9


def _decode_json_object(field: str, value: Any) -> Any:
    if field not in _JSON_OBJECT_FIELDS or not isinstance(value, str):
        return value
    decoded = json.loads(value)
    if decoded is not None and not isinstance(decoded, dict):
        raise ValueError(f"Database field {field!r} must contain a JSON object.")
    return decoded


def _record(record: Any) -> dict[str, Any]:
    """Convert asyncpg values into transport-safe API primitives at the boundary."""
    return {
        key: str(value) if isinstance(value, UUID) else _decode_json_object(key, value)
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
                """SELECT id, portfolio_id, title, property_type, status, asking_price, estimated_price, area_m2,
                          to_jsonb(estates)->'estimate_provenance' AS estimate_provenance,
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
                          attributes, created_at, updated_at,
                          to_jsonb(estates)->'estimate_provenance' AS estimate_provenance
                   FROM estates WHERE id = $1 AND organization_id = $2""",
                estate_id, context.organization_id,
            )
        if row is None:
            raise NotFoundError("Estate not found.")
        return _record(row)

    async def latest_liquidity_survival_model(self, context: TenantContext) -> dict[str, Any] | None:
        """Read only the aggregate, platform-wide model artifact.

        No caller can influence its scope.  The estate that is scored remains
        constrained by the tenant query that fetched it.
        """
        try:
            async with self.transaction(context) as connection:
                row = await connection.fetchrow(
                    """SELECT artifact
                       FROM liquidity_survival_models
                       WHERE scope = 'platform'
                       ORDER BY created_at DESC
                       LIMIT 1"""
                )
        except Exception as exc:
            # Rolling out the API before its additive migration must leave the
            # established estate endpoints usable.  Do not hide any other
            # database error behind an artificial "unavailable" score.
            if exc.__class__.__name__ == "UndefinedTableError":
                return None
            raise
        if row is None:
            return None
        artifact = dict(row).get("artifact")
        return json.loads(artifact) if isinstance(artifact, str) else artifact

    async def estate_analytics_page(self, context: TenantContext, *, limit: int, offset: int,
                                   city: str | None, area: str | None, kind: str | None,
                                   portfolio_id: str | None, query: str | None) -> dict[str, Any]:
        """Bounded catalog read; every row and the total share the tenant predicate."""
        if portfolio_id is not None:
            await self.get_portfolio(context, portfolio_id)
        predicate = """organization_id = $1
            AND ($2::text IS NULL OR city = $2) AND ($3::text IS NULL OR area = $3)
            AND ($4::text IS NULL OR property_type = $4)
            AND ($5::uuid IS NULL OR portfolio_id = $5::uuid)
            AND ($6::text IS NULL OR concat_ws(' ', title, address, summary, city, area) ILIKE '%' || $6 || '%')"""
        parameters = (context.organization_id, city, area, kind, portfolio_id, query)
        async with self.transaction(context) as connection:
            total = await connection.fetchval(f"SELECT COUNT(*) FROM estates WHERE {predicate}", *parameters)
            rows = await connection.fetch(
                f"""WITH catalog AS (
                         SELECT estates.*, ST_Y(location::geometry) AS latitude,
                                ST_X(location::geometry) AS longitude
                         FROM estates WHERE {predicate}
                         ORDER BY created_at DESC, id LIMIT $7 OFFSET $8
                     )
                      SELECT catalog.*, market.market_metrics,
                            (SELECT COUNT(*)::integer
                               FROM estates AS peer
                              WHERE peer.organization_id = catalog.organization_id
                                AND peer.id <> catalog.id
                                AND peer.status = 'active'
                                AND (catalog.property_type IS NULL OR peer.property_type = catalog.property_type)
                                AND (
                                    (catalog.location IS NOT NULL AND peer.location IS NOT NULL
                                     AND ST_DWithin(peer.location, catalog.location, 2500))
                                    OR
                                    (catalog.location IS NULL
                                     AND peer.city IS NOT DISTINCT FROM catalog.city
                                     AND peer.area IS NOT DISTINCT FROM catalog.area)
                                )) AS comparable_count
                      FROM catalog
                      LEFT JOIN LATERAL (
                          SELECT aggregate.metrics AS market_metrics
                          FROM heatmap_aggregates AS aggregate
                          WHERE aggregate.scope = 'platform'
                            AND aggregate.h3_resolution = $9
                            AND catalog.location IS NOT NULL
                            AND aggregate.boundary IS NOT NULL
                            AND ST_Covers(aggregate.boundary::geometry, catalog.location::geometry)
                          ORDER BY aggregate.period_end DESC, aggregate.calculated_at DESC
                          LIMIT 1
                      ) AS market ON TRUE
                      ORDER BY catalog.created_at DESC, catalog.id""",
                *parameters, limit, offset, DEFAULT_ESTATE_H3_RESOLUTION,
            )
        from backend.services.published_metrics import published_cell_indicators

        items = []
        for row in rows:
            item = _record(row)
            market_metrics = item.pop("market_metrics", None) or {}
            item["market_heat"] = published_cell_indicators(market_metrics).get("market_heat")
            items.append(item)
        return {"items": items, "page": {"limit": limit, "offset": offset, "total": total}}

    async def report_summary(
        self,
        context: TenantContext,
        *,
        city: str | None,
        area: str | None,
        featured_limit: int,
    ) -> dict[str, Any]:
        """Return complete-scope tenant aggregates and a bounded recent list.

        The aggregate CTE and featured list share exactly the same tenant and
        geography predicate.  This prevents ReportBuilder from treating its
        first catalog page as a population or turning missing values into zero.
        """
        async with self.transaction(context) as connection:
            row = await connection.fetchrow(
                """WITH scoped AS MATERIALIZED (
                       SELECT id, title, city, area, asking_price, price_per_m2,
                              days_on_market, updated_at
                       FROM estates
                       WHERE organization_id = $1 AND status = 'active'
                         AND ($2::text IS NULL OR city = $2)
                         AND ($3::text IS NULL OR area = $3)
                   ), featured AS (
                       SELECT * FROM scoped
                       ORDER BY updated_at DESC, id DESC
                       LIMIT $4
                   )
                   SELECT COUNT(*)::int AS active_estate_count,
                          COUNT(asking_price)::int AS asking_price_count,
                          COUNT(price_per_m2)::int AS price_per_m2_count,
                          COUNT(days_on_market)::int AS days_on_market_count,
                          AVG(asking_price) AS average_asking_price,
                          AVG(price_per_m2) AS average_price_per_m2,
                          AVG(days_on_market) AS average_days_on_market,
                          COALESCE((
                              SELECT jsonb_agg(jsonb_build_object(
                                  'id', id::text, 'title', title, 'city', city,
                                  'area', area, 'asking_price', asking_price,
                                  'price_per_m2', price_per_m2,
                                  'days_on_market', days_on_market,
                                  'updated_at', updated_at::text
                              ) ORDER BY updated_at DESC, id DESC)
                              FROM featured
                          ), '[]'::jsonb) AS featured_estates
                   FROM scoped""",
                context.organization_id,
                city,
                area,
                featured_limit,
            )
        result = _record(row or {})
        featured = result.get("featured_estates") or []
        if isinstance(featured, str):
            featured = json.loads(featured)
        result["featured_estates"] = featured
        return result

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
        common_columns = """id, title, property_type, asking_price, estimated_price,
                            to_jsonb(estates)->'estimate_provenance' AS estimate_provenance, area_m2, price_per_m2,
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

    async def published_market_observations(
        self,
        context: TenantContext,
        *,
        city=None,
        area=None,
        h3_index=None,
        liquidity_horizon_days: int | None = None,
    ) -> list[dict[str, Any]]:
        """Read a single published geography, never recompute across tenants.

        Exact NULL semantics prevent mixing national, city, neighborhood and
        H3 observations. Distinct dates retain only the latest source revision.
        """
        async with self.transaction(context) as connection:
            rows = await connection.fetch(
                """SELECT DISTINCT ON (metric, observed_on, source_name)
                          metric, value, unit, observed_on, source_name
                   FROM market_observations
                   WHERE scope = 'platform' AND organization_id IS NULL
                     AND city IS NOT DISTINCT FROM $1::text
                     AND area IS NOT DISTINCT FROM $2::text
                     AND h3_index IS NOT DISTINCT FROM $3::text
                     AND property_type IS NULL
                     AND (
                         (metric <> 'liquidity' AND dimensions = '{}'::jsonb)
                         OR (
                             metric = 'liquidity'
                             AND $4::integer IS NOT NULL
                             AND dimensions @> jsonb_build_object('liquidity_horizon_days', $4::integer)
                         )
                     )
                     AND observed_on <= CURRENT_DATE
                   ORDER BY metric, observed_on, source_name, created_at DESC, id DESC
                   LIMIT 10001""", city, area, h3_index, liquidity_horizon_days,
            )
        if len(rows) > 10000:
            raise DomainValidationError('Published history exceeds the supported observation limit.')
        return [_record(row) for row in rows]

    async def estate_market_context(self, context: TenantContext, estate: dict[str, Any]) -> list[dict[str, Any]]:
        """Use the same exact-scope, unit-checked publications as the market UI."""
        from backend.services.published_metrics import published_market_response

        rows = await self.published_market_observations(context, city=estate.get('city'), area=estate.get('area'))
        response = published_market_response(rows, city=estate.get('city'), area=estate.get('area'))
        return [dict(metric=item.metric, value=item.value, unit=item.unit, observed_on=item.observed_on,
                     source_name=item.source_name, scope='platform')
                for item in response.metrics if item.status == 'available']

    async def estate_location_metrics(
        self,
        context: TenantContext,
        estate: dict[str, Any],
        *,
        h3_resolution: int = DEFAULT_ESTATE_H3_RESOLUTION,
    ) -> dict[str, Any] | None:
        """Read a precomputed heatmap aggregate; heat is never recalculated in a request."""
        latitude, longitude = estate.get("latitude"), estate.get("longitude")
        if latitude is None or longitude is None:
            return None
        async with self.transaction(context) as connection:
            row = await connection.fetchrow(
                """SELECT h3_index, h3_resolution, city, area, period_start, period_end, metrics, input_version,
                          calculated_at, scope,
                          ST_AsGeoJSON(boundary::geometry) AS boundary, ST_AsGeoJSON(center::geometry) AS center
                   FROM heatmap_aggregates
                   WHERE scope = 'platform' AND boundary IS NOT NULL
                     AND h3_resolution = $3
                     AND ST_Covers(boundary::geometry, ST_SetSRID(ST_MakePoint($1, $2), 4326))
                   ORDER BY period_end DESC, calculated_at DESC LIMIT 1""",
                longitude, latitude, h3_resolution,
            )
        return _record(row) if row is not None else None

    async def portfolio_valuation_summary(self, context: TenantContext, portfolio_id: str) -> dict[str, Any]:
        async with self.transaction(context) as connection:
            row = await connection.fetchrow(
                """SELECT COUNT(*)::integer AS active_estate_count,
                          COUNT(*) FILTER (WHERE estimated_price IS NOT NULL
                              AND to_jsonb(estates)->'estimate_provenance'->>'recorded_at' IS NOT NULL)::integer AS estimate_lineage_count,
                          COUNT(*) FILTER (WHERE estimated_price IS NOT NULL
                              AND to_jsonb(estates)->'estimate_provenance'->>'status' = 'inputs_changed')::integer AS estimate_inputs_changed_count,
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
                          AVG(days_on_market) AS average_days_on_market,
                          COUNT(*) FILTER (
                              WHERE listed_since IS NOT NULL AND listed_since <= CURRENT_DATE
                          )::integer AS listing_age_count,
                          AVG(
                              CASE WHEN listed_since IS NOT NULL AND listed_since <= CURRENT_DATE
                                   THEN (CURRENT_DATE - listed_since)::double precision END
                          ) AS average_listing_age_days
                   FROM estates WHERE organization_id = $1 AND portfolio_id = $2 AND status = 'active'""",
                context.organization_id, portfolio_id,
            )
        return _record(row)

    async def portfolio_liquidity_sources(self, context: TenantContext, portfolio_id: str) -> list[dict[str, Any]]:
        """Return only this authorized portfolio's listing/sale durations.

        The portfolio liquidity metric is deliberately self-contained: unlike
        estate liquidity, it must not consult a similar-property or global
        survival cohort.
        """
        async with self.transaction(context) as connection:
            rows = await connection.fetch(
                """SELECT status, days_on_market, listed_since, last_sale_date
                   FROM estates
                   WHERE organization_id = $1 AND portfolio_id = $2
                     AND status IN ('active', 'sold')""",
                context.organization_id, portfolio_id,
            )
        return [_record(row) for row in rows]

    async def portfolio_metric_history(
        self,
        context: TenantContext,
        portfolio_id: str,
        *,
        limit: int = 366,
    ) -> list[dict[str, Any]]:
        """Read persisted portfolio snapshots, never reconstruct prior states."""
        async with self.transaction(context) as connection:
            rows = await connection.fetch(
                """SELECT observed_on, active_estate_count, asking_price_count, estimated_count,
                          days_on_market_count, listing_age_count, portfolio_value,
                          average_days_on_market, average_listing_age_days, average_price_gap
                   FROM portfolio_metric_snapshots
                   WHERE organization_id = $1 AND portfolio_id = $2
                   ORDER BY observed_on DESC
                   LIMIT $3""",
                context.organization_id, portfolio_id, limit,
            )
        # The UI needs chronological points; retain the database bound before
        # reversing rather than reading an unbounded tenant history.
        return list(reversed([_record(row) for row in rows]))

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
        """One bounded regional publication join; normalization shares market ownership."""
        from backend.services.published_metrics import published_market_response

        async with self.transaction(context) as connection:
            rows = await connection.fetch(
                """WITH regions AS (
                       SELECT city, area, COUNT(*)::integer AS estate_count
                       FROM estates WHERE organization_id = $1 AND portfolio_id = $2 AND status = 'active'
                       GROUP BY city, area
                   )
                   SELECT r.city, r.area, r.estate_count, COALESCE(p.observations, '[]'::json) AS observations
                   FROM regions r LEFT JOIN LATERAL (
                       SELECT json_agg(latest) AS observations FROM (
                           SELECT DISTINCT ON (metric, source_name) metric, value, unit, observed_on, source_name
                           FROM market_observations
                           WHERE scope = 'platform' AND organization_id IS NULL
                             AND city IS NOT DISTINCT FROM r.city AND area IS NOT DISTINCT FROM r.area
                             AND h3_index IS NULL AND property_type IS NULL AND dimensions = '{}'::jsonb
                             AND observed_on <= CURRENT_DATE
                             AND metric IN ('price_m2', 'market_heat')
                           ORDER BY metric, source_name, observed_on DESC, created_at DESC, id DESC
                       ) latest
                   ) p ON TRUE ORDER BY r.estate_count DESC""",
                context.organization_id, portfolio_id,
            )
        results = []
        for row in rows:
            observations = row['observations']
            if isinstance(observations, str):
                observations = json.loads(observations)
            metrics = published_market_response(observations).metrics
            values = {item.metric: item for item in metrics}
            dates = [item.observed_on for item in metrics if item.status == 'available' and item.observed_on]
            results.append(dict(city=row['city'], area=row['area'], estate_count=row['estate_count'],
                average_price_m2=values['price_m2'].value, market_heat=values['market_heat'].value,
                latest_observed_on=max(dates) if dates else None))
        return results

    async def list_geographic_regions(self, context: TenantContext, *, published_only: bool = True) -> list[dict[str, Any]]:
        async with self.transaction(context) as connection:
            rows = await connection.fetch(
                """WITH regions AS (
                     SELECT city, area FROM heatmap_aggregates WHERE scope = 'platform'
                     UNION
                     SELECT city, area FROM estates WHERE organization_id = $1 AND NOT $2::boolean
                   ) SELECT city, array_agg(DISTINCT area ORDER BY area) FILTER (WHERE area IS NOT NULL) AS areas
                     FROM regions WHERE city IS NOT NULL GROUP BY city ORDER BY city""",
                context.organization_id, published_only,
            )
        return [{"city": row["city"], "areas": row["areas"] or []} for row in rows]

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

    async def published_heatmap_snapshot(
        self,
        context: TenantContext,
        *,
        city: str | None,
        area: str | None,
        h3_index: str | None,
        default_h3_resolution: int = 9,
    ) -> list[dict[str, Any]]:
        """Read the newest precomputed cell per index for a compact market snapshot.

        The city/global reader deliberately uses the canonical H3 9
        publication; an H3-index request determines its own resolution from
        the stored index. This is still a read over platform aggregates, never
        a recomputation over tenant estates.
        """
        async with self.transaction(context) as connection:
            rows = await connection.fetch(
                """WITH selected_publication AS (
                       SELECT input_version
                       FROM heatmap_aggregates
                       WHERE scope = 'platform'
                         AND ($1::text IS NULL OR h3_index = $1)
                         AND ($1::text IS NOT NULL OR h3_resolution = $2)
                         AND ($3::text IS NULL OR city = $3)
                         AND ($4::text IS NULL OR area = $4)
                       ORDER BY calculated_at DESC, input_version DESC
                       LIMIT 1
                   )
                   SELECT DISTINCT ON (h3_index)
                          h3_index, h3_resolution, city, area, period_start, period_end,
                          metrics, input_version, calculated_at, scope
                   FROM heatmap_aggregates
                   WHERE scope = 'platform'
                     AND ($1::text IS NULL OR h3_index = $1)
                     AND ($1::text IS NOT NULL OR h3_resolution = $2)
                     AND ($3::text IS NULL OR city = $3)
                     AND ($4::text IS NULL OR area = $4)
                     AND input_version IS NOT DISTINCT FROM (
                         SELECT input_version FROM selected_publication
                     )
                   ORDER BY h3_index, calculated_at DESC""",
                h3_index, default_h3_resolution, city, area,
            )
        return [_record(row) for row in rows]

    async def portfolio_positions(self, context: TenantContext, portfolio_id: str) -> dict[str, Any]:
        """Full-population counts plus a bounded price-position detail, not notifications."""
        async with self.transaction(context) as connection:
            row = await connection.fetchrow(
                """WITH positions AS (
                    SELECT id::text AS property_id, title, area AS region, asking_price, estimated_price,
                           to_jsonb(estates)->'estimate_provenance' AS estimate_provenance,
                           CASE WHEN estimated_price > 0 AND asking_price IS NOT NULL
                                THEN (asking_price - estimated_price) / estimated_price END AS price_gap,
                           CASE WHEN estimated_price > 0 AND asking_price IS NOT NULL
                                THEN asking_price - estimated_price END AS difference
                    FROM estates WHERE organization_id = $1 AND portfolio_id = $2 AND status = 'active'
                )
                SELECT COUNT(*) FILTER (WHERE price_gap > 0)::integer AS above_count,
                       COUNT(*) FILTER (WHERE price_gap < 0)::integer AS below_count,
                       COUNT(*) FILTER (WHERE price_gap = 0)::integer AS equal_count,
                       COUNT(*) FILTER (WHERE price_gap IS NULL)::integer AS missing_count,
                       COUNT(asking_price)::integer AS asking_count,
                       COUNT(estimated_price)::integer AS estimated_count,
                       COALESCE((SELECT jsonb_agg(detail) FROM (
                           SELECT * FROM positions WHERE price_gap IS NOT NULL AND price_gap <> 0
                           ORDER BY abs(price_gap) DESC, property_id LIMIT 100
                       ) detail), '[]'::jsonb) AS rows FROM positions""",
                context.organization_id, portfolio_id,
            )
        result = _record(row)
        if isinstance(result['rows'], str):
            result['rows'] = __import__('json').loads(result['rows'])
        return result
