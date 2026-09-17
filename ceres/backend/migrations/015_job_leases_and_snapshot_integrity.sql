-- Attempt-scoped worker leases and lossless portfolio snapshot coalescing.
-- Apply after 014_estimate_provenance.sql. Re-grant execution on the replaced
-- claim/recovery functions only to the provisioned worker role.

ALTER TABLE public.jobs
    ADD COLUMN IF NOT EXISTS execution_token UUID,
    ADD COLUMN IF NOT EXISTS heartbeat_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS rerun_requested BOOLEAN NOT NULL DEFAULT FALSE;

DROP FUNCTION IF EXISTS public.claim_next_background_job();

CREATE FUNCTION public.claim_next_background_job()
RETURNS TABLE (
    job_id UUID,
    organization_id UUID,
    user_id UUID,
    job_type TEXT,
    payload JSONB,
    input_version TEXT,
    attempt_count INTEGER,
    max_attempts SMALLINT,
    created_at TIMESTAMPTZ,
    execution_token UUID
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
    SET status = 'RUNNING', started_at = now(), heartbeat_at = now(),
        execution_token = gen_random_uuid(), completed_at = NULL,
        updated_at = now(), attempt_count = attempt_count + 1, progress = 0
    FROM candidate
    WHERE job.id = candidate.id
    RETURNING job.id, job.organization_id, job.requested_by_user_id, job.job_type,
              job.payload, job.input_version, job.attempt_count, job.max_attempts,
              job.created_at, job.execution_token;
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
    IF stale_after_seconds <= 0 THEN
        RAISE EXCEPTION 'stale_after_seconds must be positive';
    END IF;

    UPDATE public.jobs
    SET status = CASE WHEN attempt_count < max_attempts THEN 'PENDING' ELSE 'FAILED' END,
        available_at = CASE WHEN attempt_count < max_attempts THEN now() ELSE available_at END,
        started_at = CASE WHEN attempt_count < max_attempts THEN NULL ELSE started_at END,
        completed_at = CASE WHEN attempt_count < max_attempts THEN NULL ELSE now() END,
        error = CASE WHEN attempt_count < max_attempts THEN error
                     ELSE jsonb_build_object('code', 'stale_worker', 'message', 'Worker stopped before completion') END,
        execution_token = NULL,
        heartbeat_at = NULL,
        updated_at = now()
    WHERE status = 'RUNNING'
      AND COALESCE(heartbeat_at, started_at) < now() - (stale_after_seconds * interval '1 second');
    GET DIAGNOSTICS affected = ROW_COUNT;
    RETURN affected;
END;
$$;

REVOKE ALL ON FUNCTION public.recover_stale_background_jobs(INTEGER) FROM PUBLIC;

CREATE OR REPLACE FUNCTION public.enqueue_portfolio_snapshot_on_estate_change()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    target_organization UUID;
    target_portfolio UUID;
    snapshot_key TEXT;
BEGIN
    IF TG_OP <> 'INSERT' AND OLD.portfolio_id IS NOT NULL THEN
        target_organization := OLD.organization_id;
        target_portfolio := OLD.portfolio_id;
        snapshot_key := format('portfolio-snapshot:%s:%s', target_portfolio, CURRENT_DATE);
        INSERT INTO public.jobs (
            id, organization_id, requested_by_user_id, job_type, status, idempotency_key,
            payload, input_version, progress, available_at
        ) VALUES (
            gen_random_uuid(), target_organization, NULL, 'portfolio_snapshot', 'PENDING', snapshot_key,
            jsonb_build_object('portfolio_id', target_portfolio::text),
            'portfolio-snapshot-v1', 0, now()
        )
        ON CONFLICT (organization_id, job_type, idempotency_key) WHERE idempotency_key IS NOT NULL
        DO UPDATE SET
            rerun_requested = public.jobs.status = 'RUNNING',
            status = CASE WHEN public.jobs.status = 'RUNNING' THEN public.jobs.status ELSE 'PENDING' END,
            payload = EXCLUDED.payload,
            input_version = EXCLUDED.input_version,
            progress = CASE WHEN public.jobs.status = 'RUNNING' THEN public.jobs.progress ELSE 0 END,
            result = CASE WHEN public.jobs.status = 'RUNNING' THEN public.jobs.result ELSE NULL END,
            result_reference = CASE WHEN public.jobs.status = 'RUNNING' THEN public.jobs.result_reference ELSE NULL END,
            error = CASE WHEN public.jobs.status = 'RUNNING' THEN public.jobs.error ELSE NULL END,
            attempt_count = CASE WHEN public.jobs.status = 'RUNNING' THEN public.jobs.attempt_count ELSE 0 END,
            started_at = CASE WHEN public.jobs.status = 'RUNNING' THEN public.jobs.started_at ELSE NULL END,
            completed_at = CASE WHEN public.jobs.status = 'RUNNING' THEN public.jobs.completed_at ELSE NULL END,
            available_at = CASE WHEN public.jobs.status = 'RUNNING' THEN public.jobs.available_at ELSE now() END,
            updated_at = now();
    END IF;

    IF TG_OP <> 'DELETE' AND NEW.portfolio_id IS NOT NULL
       AND (TG_OP <> 'UPDATE' OR OLD.portfolio_id IS DISTINCT FROM NEW.portfolio_id) THEN
        target_organization := NEW.organization_id;
        target_portfolio := NEW.portfolio_id;
        snapshot_key := format('portfolio-snapshot:%s:%s', target_portfolio, CURRENT_DATE);
        INSERT INTO public.jobs (
            id, organization_id, requested_by_user_id, job_type, status, idempotency_key,
            payload, input_version, progress, available_at
        ) VALUES (
            gen_random_uuid(), target_organization, NULL, 'portfolio_snapshot', 'PENDING', snapshot_key,
            jsonb_build_object('portfolio_id', target_portfolio::text),
            'portfolio-snapshot-v1', 0, now()
        )
        ON CONFLICT (organization_id, job_type, idempotency_key) WHERE idempotency_key IS NOT NULL
        DO UPDATE SET
            rerun_requested = public.jobs.status = 'RUNNING',
            status = CASE WHEN public.jobs.status = 'RUNNING' THEN public.jobs.status ELSE 'PENDING' END,
            payload = EXCLUDED.payload,
            input_version = EXCLUDED.input_version,
            progress = CASE WHEN public.jobs.status = 'RUNNING' THEN public.jobs.progress ELSE 0 END,
            result = CASE WHEN public.jobs.status = 'RUNNING' THEN public.jobs.result ELSE NULL END,
            result_reference = CASE WHEN public.jobs.status = 'RUNNING' THEN public.jobs.result_reference ELSE NULL END,
            error = CASE WHEN public.jobs.status = 'RUNNING' THEN public.jobs.error ELSE NULL END,
            attempt_count = CASE WHEN public.jobs.status = 'RUNNING' THEN public.jobs.attempt_count ELSE 0 END,
            started_at = CASE WHEN public.jobs.status = 'RUNNING' THEN public.jobs.started_at ELSE NULL END,
            completed_at = CASE WHEN public.jobs.status = 'RUNNING' THEN public.jobs.completed_at ELSE NULL END,
            available_at = CASE WHEN public.jobs.status = 'RUNNING' THEN public.jobs.available_at ELSE now() END,
            updated_at = now();
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;
