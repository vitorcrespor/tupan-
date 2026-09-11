"""PostgreSQL queue primitives used only by the backend worker process."""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import date, datetime
from uuid import uuid4
from typing import Any, AsyncIterator

from backend.repositories.tenant_data import TenantContext
from backend.services.errors import UnavailableError


@dataclass(frozen=True)
class ClaimedJob:
    job_id: str
    organization_id: str
    user_id: str | None
    job_type: str
    payload: dict[str, Any]
    input_version: str | None
    attempt_count: int
    max_attempts: int
    created_at: datetime | None = None


@dataclass(frozen=True)
class JobResult:
    result_reference: str | None
    result: dict[str, Any]


class JobQueueRepository:
    """Claim globally, then access every job payload under its tenant context.

    ``WORKER_DATABASE_URL`` is intentionally separate from the API's database
    URL. Its role may claim pending jobs across tenants, but every handler data
    query uses ``tenant_transaction`` and explicitly sets `app.organization_id`.
    """

    def __init__(self, database_url: str | None = None) -> None:
        self._database_url = database_url or os.getenv("WORKER_DATABASE_URL", "").strip()
        self._pool: Any | None = None

    async def start(self, *, max_connections: int = 4) -> None:
        if self._pool is not None:
            return
        if not self._database_url:
            raise UnavailableError(
                "Worker database storage is not configured.",
                details={"reason": "worker_database_url_missing"},
            )
        try:
            import asyncpg

            self._pool = await asyncpg.create_pool(self._database_url, min_size=1, max_size=max_connections)
        except ImportError as exc:
            raise UnavailableError("The worker database dependency is unavailable.") from exc
        except Exception as exc:
            raise UnavailableError(
                "Worker database storage could not be reached.",
                details={"reason": "worker_database_unavailable"},
            ) from exc

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def claim_next(self) -> ClaimedJob | None:
        """Atomically claim through the queue-only privileged database function."""
        pool = self._require_pool()
        async with pool.acquire() as connection:
            row = await connection.fetchrow("SELECT * FROM public.claim_next_background_job()")
        return self._claimed_job(row) if row is not None else None

    async def requeue_stale_running(self, *, stale_after_seconds: int) -> int:
        """Recover abandoned jobs through the same queue-only privileged boundary."""
        pool = self._require_pool()
        async with pool.acquire() as connection:
            affected = await connection.fetchval(
                "SELECT public.recover_stale_background_jobs($1)", stale_after_seconds
            )
        return int(affected or 0)
    @asynccontextmanager
    async def tenant_transaction(self, context: TenantContext) -> AsyncIterator[Any]:
        pool = self._require_pool()
        async with pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute("SELECT set_config('app.organization_id', $1, true)", context.organization_id)
                yield connection

    async def set_progress(self, context: TenantContext, job_id: str, progress: int) -> None:
        bounded = min(100, max(0, int(progress)))
        async with self.tenant_transaction(context) as connection:
            await connection.execute(
                """UPDATE jobs SET progress = $3, updated_at = now()
                   WHERE id = $1 AND organization_id = $2 AND status = 'RUNNING'""",
                job_id, context.organization_id, bounded,
            )

    async def heatmap_source_estates(
        self,
        context: TenantContext,
        *,
        city: str | None,
        area: str | None,
    ) -> list[dict[str, Any]]:
        async with self.tenant_transaction(context) as connection:
            rows = await connection.fetch(
                """SELECT ST_Y(location::geometry) AS latitude, ST_X(location::geometry) AS longitude,
                          asking_price, price_per_m2, area_m2, days_on_market, city, area
                   FROM estates
                   WHERE organization_id = $1 AND status = 'active' AND location IS NOT NULL
                     AND ($2::text IS NULL OR city = $2) AND ($3::text IS NULL OR area = $3)""",
                context.organization_id, city, area,
            )
        return [dict(row) for row in rows]

    async def upsert_heatmap_aggregates(self, context: TenantContext, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        async with self.tenant_transaction(context) as connection:
            for row in rows:
                await connection.execute(
                    """INSERT INTO heatmap_aggregates (
                           id, organization_id, scope, h3_index, h3_resolution, period_start, period_end,
                           city, area, boundary, center, metrics, input_version, calculated_at
                       ) VALUES (
                           $1, $2, 'tenant', $3, $4, $5, $6, $7, $8,
                           ST_SetSRID(ST_GeomFromGeoJSON($9), 4326)::geography,
                           ST_SetSRID(ST_GeomFromGeoJSON($10), 4326)::geography,
                           $11::jsonb, $12, now()
                       )
                       ON CONFLICT (organization_id, h3_index, h3_resolution, period_start, period_end, input_version)
                         WHERE scope = 'tenant'
                       DO UPDATE SET city = EXCLUDED.city, area = EXCLUDED.area, boundary = EXCLUDED.boundary,
                                     center = EXCLUDED.center, metrics = EXCLUDED.metrics, calculated_at = now()""",
                    str(uuid4()), context.organization_id,
                    row["h3_index"], row["h3_resolution"], row["period_start"], row["period_end"],
                    row.get("city"), row.get("area"), json.dumps(row["boundary"]), json.dumps(row["center"]),
                    json.dumps(row["metrics"]), row["input_version"],
                )

    async def mark_succeeded(self, context: TenantContext, job: ClaimedJob, result: JobResult) -> None:
        async with self.tenant_transaction(context) as connection:
            await connection.execute(
                """UPDATE jobs SET status = 'SUCCEEDED', progress = 100, result = $3::jsonb,
                          result_reference = $4, completed_at = now(), updated_at = now()
                   WHERE id = $1 AND organization_id = $2 AND status = 'RUNNING'""",
                job.job_id, context.organization_id, json.dumps(result.result), result.result_reference,
            )

    async def retry_or_fail(
        self,
        context: TenantContext,
        job: ClaimedJob,
        *,
        error: dict[str, Any],
        retryable: bool,
    ) -> None:
        delay_seconds = min(300, 2 ** max(0, job.attempt_count - 1))
        should_retry = retryable and job.attempt_count < job.max_attempts
        async with self.tenant_transaction(context) as connection:
            await connection.execute(
                """UPDATE jobs
                   SET status = CASE WHEN $4 THEN 'PENDING' ELSE 'FAILED' END,
                       available_at = CASE WHEN $4 THEN now() + ($5 * interval '1 second') ELSE available_at END,
                       error = $3::jsonb,
                       completed_at = CASE WHEN $4 THEN NULL ELSE now() END,
                       updated_at = now()
                   WHERE id = $1 AND organization_id = $2 AND status = 'RUNNING'""",
                job.job_id, context.organization_id, json.dumps(error), should_retry, delay_seconds,
            )

    def _require_pool(self) -> Any:
        if self._pool is None:
            raise RuntimeError("JobQueueRepository.start() must be called first.")
        return self._pool

    @staticmethod
    def _claimed_job(row: Any) -> ClaimedJob:
        payload = row["payload"] or {}
        return ClaimedJob(
            job_id=str(row["job_id"]),
            organization_id=str(row["organization_id"]),
            user_id=str(row["user_id"]) if row["user_id"] is not None else None,
            job_type=str(row["job_type"]),
            payload=dict(payload),
            input_version=row["input_version"],
            attempt_count=int(row["attempt_count"]),
            max_attempts=int(row["max_attempts"]),
            created_at=row.get("created_at") if hasattr(row, "get") else None,
        )
