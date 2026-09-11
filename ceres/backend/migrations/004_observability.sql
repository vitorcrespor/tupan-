-- Add queue-time observability to the dedicated worker claim function.
-- Apply after 003_background_jobs.sql. Re-grant execution only to the
-- backend worker database role after this migration; PUBLIC stays revoked.

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
    created_at TIMESTAMPTZ
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
              job.payload, job.input_version, job.attempt_count, job.max_attempts,
              job.created_at;
$$;

REVOKE ALL ON FUNCTION public.claim_next_background_job() FROM PUBLIC;

-- Example (replace tupan_worker with the provisioned worker-only role):
-- GRANT EXECUTE ON FUNCTION public.claim_next_background_job() TO tupan_worker;
