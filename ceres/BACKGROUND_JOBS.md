# Background processing

Tupan uses one FastAPI process, PostgreSQL, and one or more identical worker
processes. PostgreSQL is the queue; Redis and Kafka are not required for the
current workload.

## Job lifecycle

`jobs` is the source of truth for durable work. After migration `003`, every
job has `job_id`, `organization_id`, `user_id`, `job_type`, `status`,
`progress`, timestamps, `result_reference`, and structured `error`/`result`
fields.

```
PENDING -> RUNNING -> SUCCEEDED
                  -> FAILED
```

The desktop submits a job with `POST /api/v1/jobs` and polls
`GET /api/v1/jobs/{job_id}`. It never supplies `organization_id`, `user_id`,
attempt limits, or database credentials. An idempotency key is required;
repeating a submission with the same tenant/job-type/key returns the existing
job rather than creating duplicate work.

The worker claims jobs using `FOR UPDATE SKIP LOCKED`, so concurrent workers
do not process the same job. It increments the persisted attempt count before
execution; transient errors retry with exponential delays (1, 2, 4… seconds,
maximum five minutes), subject to a default maximum of three attempts. Invalid
inputs and unknown job types fail once. Workers recover stale `RUNNING` jobs at
startup; exhausted attempts become `FAILED`.

## Tenant handling

The worker's claim credential (`WORKER_DATABASE_URL`) stays server-side and is
separate from the API credential. It has no broad RLS bypass. It may execute two non-public, queue-only PostgreSQL claim/recovery functions; the claimed job’s persisted organization id is immediately converted into an
immutable `TenantContext`. Every handler transaction executes:

```sql
SELECT set_config('app.organization_id', :organization_id, true);
```

and includes organization predicates. Thus handler input never trusts an
organization identifier in the job payload, and concurrent jobs never share
tenant-specific mutable state.

## Registered work

| Job type | Worker behavior | Idempotency / result |
| --- | --- | --- |
| `heatmap_precompute` | Reads authorized active estates; aggregates common inventory, asking-price, price/m², and DOM values by H3 cell; writes PostGIS boundaries/centres to `heatmap_aggregates`. | PostgreSQL partial unique index plus `ON CONFLICT DO UPDATE`; retries overwrite the same aggregate instead of duplicating it. |

The architecture intentionally does **not** claim handlers for imports,
embeddings, notification delivery, market refresh, AVM training, or bulk
portfolio analysis yet. They should be registered only after their authorized
source/destination and idempotency key are defined. Unrecognized job types fail
once with `unsupported_job_type`, rather than pretending the work happened.

## Heatmap path and staleness

```
estate / market source data
  -> heatmap_precompute job
  -> H3 + PostGIS aggregate rows
  -> GET /api/v1/market/heatmap
  -> desktop map rendering
```

`heatmap_aggregates` is the materialized geographic read model:

| Item | Definition |
| --- | --- |
| Key | `(organization_id, h3_index, h3_resolution, period_start, period_end, input_version)` |
| Tenant scope | Explicit organization id; platform rows remain explicitly shared only when written by a controlled ingestion process. |
| Source of truth | Tenant `estates`; the initial worker aggregates active listing fields only. Explicit market-observation enrichment should be added as a separate versioned handler. |
| TTL | No in-memory TTL. PostgreSQL rows remain until replaced by an idempotent precompute job. |
| Invalidation | An `estates` database trigger automatically coalesces each tenant/city/area change into a `heatmap_precompute` job. Market-observation refreshes, a changed H3 resolution, or a changed aggregation version need their own versioned trigger/handler. |
| Acceptable staleness | The last successful aggregate is served until its next queued refresh completes. Use the returned `calculated_at` timestamp to show freshness. |

No separate process-memory cache has been added: indexed aggregate queries are
already the low-latency path, and there is no production latency evidence that
justifies a cross-process cache. Add Redis only if measured read pressure or
multi-process invalidation makes this table insufficient; its cache key must
include the organization and aggregate input version.

## Running locally

Apply all migrations, then use a backend-only worker credential:

```powershell
psql $env:DATABASE_URL -f backend/migrations/001_cloud_control_plane.sql
psql $env:DATABASE_URL -f backend/migrations/002_production_data_platform.sql
psql $env:DATABASE_URL -f backend/migrations/003_background_jobs.sql
psql $env:DATABASE_URL -f backend/migrations/004_observability.sql

$env:WORKER_DATABASE_URL = $env:DATABASE_URL # local development only
python -m backend.worker
```

In production, `WORKER_DATABASE_URL` must use a dedicated backend worker role;
never place it in the desktop application or a Vite environment file. Provision
that role separately, grant it only the handler tables it needs, and grant the
queue functions explicitly after migration:

```sql
GRANT USAGE ON SCHEMA public TO tupan_worker;
GRANT EXECUTE ON FUNCTION public.claim_next_background_job() TO tupan_worker;
GRANT EXECUTE ON FUNCTION public.recover_stale_background_jobs(INTEGER) TO tupan_worker;
GRANT SELECT, UPDATE ON jobs TO tupan_worker;
GRANT SELECT ON estates TO tupan_worker;
GRANT SELECT, INSERT, UPDATE ON heatmap_aggregates TO tupan_worker;
```

The controlled migration/queue owner owns the two `SECURITY DEFINER` functions;
`PUBLIC` has no execute permission. The worker role itself remains subject to
RLS for every handler query.
