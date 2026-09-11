-- Minimal PostgreSQL-backed background job queue.
-- Apply after 001_cloud_control_plane.sql and 002_production_data_platform.sql.
-- The API role must NOT have BYPASSRLS. The worker uses a separate backend-only
-- database role for claiming work, then re-enters every job under its origin
-- organization context before reading or writing tenant data.

DO $$ BEGIN
    CREATE TYPE background_job_status AS ENUM ('PENDING', 'RUNNING', 'SUCCEEDED', 'FAILED');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- The partial index references the old enum value and must be rebuilt before
-- converting the column type.
DROP INDEX IF EXISTS jobs_claim_idx;

ALTER TABLE jobs ALTER COLUMN status DROP DEFAULT;
ALTER TABLE jobs
    ALTER COLUMN status TYPE background_job_status
    USING (
        CASE status::text
            WHEN 'queued' THEN 'PENDING'::background_job_status
            WHEN 'running' THEN 'RUNNING'::background_job_status
            WHEN 'succeeded' THEN 'SUCCEEDED'::background_job_status
            WHEN 'failed' THEN 'FAILED'::background_job_status
            WHEN 'cancelled' THEN 'FAILED'::background_job_status
            ELSE 'FAILED'::background_job_status
        END
    );
ALTER TABLE jobs ALTER COLUMN status SET DEFAULT 'PENDING'::background_job_status;

ALTER TABLE jobs
    ADD COLUMN IF NOT EXISTS progress SMALLINT NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 100),
    ADD COLUMN IF NOT EXISTS max_attempts SMALLINT NOT NULL DEFAULT 3 CHECK (max_attempts BETWEEN 1 AND 10),
    ADD COLUMN IF NOT EXISTS result_reference TEXT;

CREATE INDEX IF NOT EXISTS jobs_claim_idx
    ON jobs (status, available_at, created_at)
    WHERE status = 'PENDING';

-- Existing idempotency is retained: a retry/repeated submit with the same
-- (organization_id, job_type, idempotency_key) always resolves to one job.
-- Only these narrowly scoped functions may see pending jobs across tenants.
-- Their owner must be the controlled migration/queue-owner role, which is the
-- sole role permitted to bypass the jobs RLS policy for this purpose. PUBLIC
-- execution is explicitly revoked; grant execute only to the worker role at
-- deployment time. Handler data queries do not use these functions.
CREATE OR REPLACE FUNCTION public.claim_next_background_job()
RETURNS TABLE (
    job_id UUID,
    organization_id UUID,
    user_id UUID,
    job_type TEXT,
    payload JSONB,
    input_version TEXT,
    attempt_count INTEGER,
    max_attempts SMALLINT
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    WITH candidate AS (
        SELECT id FROM public.jobs
        WHERE status = 'PENDING' AND available_at <= now() AND attempt_count < max_attempts
        ORDER BY available_at, created_at
        FOR UPDATE SKIP LOCKED
        LIMIT 1
    )
    UPDATE public.jobs AS job
    SET status = 'RUNNING', started_at = COALESCE(started_at, now()),
        updated_at = now(), attempt_count = attempt_count + 1, progress = 0
    FROM candidate
    WHERE job.id = candidate.id
    RETURNING job.id, job.organization_id, job.requested_by_user_id, job.job_type,
              job.payload, job.input_version, job.attempt_count, job.max_attempts;
$$;
REVOKE ALL ON FUNCTION public.claim_next_background_job() FROM PUBLIC;

CREATE OR REPLACE FUNCTION public.recover_stale_background_jobs(stale_after_seconds INTEGER)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    affected INTEGER;
BEGIN
    UPDATE public.jobs
    SET status = CASE WHEN attempt_count < max_attempts THEN 'PENDING' ELSE 'FAILED' END,
        available_at = CASE WHEN attempt_count < max_attempts THEN now() ELSE available_at END,
        completed_at = CASE WHEN attempt_count < max_attempts THEN NULL ELSE now() END,
        error = CASE WHEN attempt_count < max_attempts THEN error
                     ELSE jsonb_build_object('code', 'stale_worker', 'message', 'Worker stopped before completion') END,
        updated_at = now()
    WHERE status = 'RUNNING' AND started_at < now() - (stale_after_seconds * interval '1 second');
    GET DIAGNOSTICS affected = ROW_COUNT;
    RETURN affected;
END;
$$;
REVOKE ALL ON FUNCTION public.recover_stale_background_jobs(INTEGER) FROM PUBLIC;
-- Coalesce estate changes into a durable heatmap refresh in the same database
-- transaction as the source-data mutation. This is a minimal transactional
-- outbox for the one registered derived-data job: estate writes stay fast, and
-- the worker consumes the refresh later. A running job reads current source
-- data, so it is not duplicated while active.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE OR REPLACE FUNCTION public.enqueue_estate_heatmap_refresh()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
DECLARE
    target_organization UUID;
    target_city TEXT;
    target_area TEXT;
    refresh_key TEXT;
BEGIN
    IF TG_OP = 'DELETE' THEN
        target_organization := OLD.organization_id;
        target_city := OLD.city;
        target_area := OLD.area;
    ELSE
        target_organization := NEW.organization_id;
        target_city := NEW.city;
        target_area := NEW.area;
    END IF;

    refresh_key := format(
        'heatmap:%s:%s:%s:9:estate-base-v1',
        target_organization,
        coalesce(target_city, '_'),
        coalesce(target_area, '_')
    );

    INSERT INTO public.jobs (
        id, organization_id, requested_by_user_id, job_type, status, idempotency_key,
        payload, input_version, progress, available_at
    ) VALUES (
        gen_random_uuid(), target_organization, NULL, 'heatmap_precompute', 'PENDING', refresh_key,
        jsonb_build_object('h3_resolution', 9, 'city', target_city, 'area', target_area,
                           'input_version', 'estate-base-v1'),
        'estate-base-v1', 0, now()
    )
    ON CONFLICT (organization_id, job_type, idempotency_key) WHERE idempotency_key IS NOT NULL
    DO UPDATE SET
        status = 'PENDING',
        payload = EXCLUDED.payload,
        input_version = EXCLUDED.input_version,
        progress = 0,
        result = NULL,
        result_reference = NULL,
        error = NULL,
        completed_at = NULL,
        available_at = now(),
        updated_at = now()
    WHERE public.jobs.status <> 'RUNNING';

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS estates_enqueue_heatmap_refresh ON public.estates;
CREATE TRIGGER estates_enqueue_heatmap_refresh
AFTER INSERT OR UPDATE OR DELETE ON public.estates
FOR EACH ROW EXECUTE FUNCTION public.enqueue_estate_heatmap_refresh();