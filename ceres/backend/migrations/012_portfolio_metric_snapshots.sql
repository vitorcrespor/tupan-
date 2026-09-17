-- Durable, tenant-scoped portfolio observations for factual history charts.
-- A row describes one portfolio on one observed day.  It is not a forecast and
-- is never reconstructed from a later portfolio state.

CREATE TABLE IF NOT EXISTS public.portfolio_metric_snapshots (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    portfolio_id UUID NOT NULL REFERENCES public.portfolios(id) ON DELETE CASCADE,
    observed_on DATE NOT NULL,
    active_estate_count INTEGER NOT NULL CHECK (active_estate_count >= 0),
    asking_price_count INTEGER NOT NULL CHECK (asking_price_count >= 0),
    estimated_count INTEGER NOT NULL CHECK (estimated_count >= 0),
    days_on_market_count INTEGER NOT NULL CHECK (days_on_market_count >= 0),
    listing_age_count INTEGER NOT NULL CHECK (listing_age_count >= 0),
    portfolio_value NUMERIC(18, 2),
    average_days_on_market DOUBLE PRECISION,
    average_listing_age_days DOUBLE PRECISION,
    average_price_gap DOUBLE PRECISION,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (organization_id, portfolio_id, observed_on),
    CHECK (portfolio_value IS NULL OR portfolio_value >= 0),
    CHECK (average_days_on_market IS NULL OR average_days_on_market >= 0),
    CHECK (average_listing_age_days IS NULL OR average_listing_age_days >= 0)
);

CREATE INDEX IF NOT EXISTS portfolio_metric_snapshots_history_idx
    ON public.portfolio_metric_snapshots (organization_id, portfolio_id, observed_on DESC);

ALTER TABLE public.portfolio_metric_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.portfolio_metric_snapshots FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS portfolio_metric_snapshots_tenant_policy ON public.portfolio_metric_snapshots;
CREATE POLICY portfolio_metric_snapshots_tenant_policy ON public.portfolio_metric_snapshots
    USING (organization_id = current_setting('app.organization_id', true)::uuid)
    WITH CHECK (organization_id = current_setting('app.organization_id', true)::uuid);

REVOKE ALL ON TABLE public.portfolio_metric_snapshots FROM PUBLIC;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        REVOKE ALL ON TABLE public.portfolio_metric_snapshots FROM anon;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        REVOKE ALL ON TABLE public.portfolio_metric_snapshots FROM authenticated;
    END IF;
END;
$$;

-- Any estate mutation coalesces into at most one snapshot job per portfolio
-- per calendar day. A worker captures the state after commit under the job's
-- originating tenant context. Updating a row cannot create duplicate history.
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
            jsonb_build_object('portfolio_id', target_portfolio::text, 'observed_on', CURRENT_DATE::text),
            'portfolio-snapshot-v1', 0, now()
        )
        ON CONFLICT (organization_id, job_type, idempotency_key) WHERE idempotency_key IS NOT NULL
        DO UPDATE SET status = 'PENDING', payload = EXCLUDED.payload, input_version = EXCLUDED.input_version,
                      progress = 0, result = NULL, result_reference = NULL, error = NULL,
                      completed_at = NULL, available_at = now(), updated_at = now()
        WHERE public.jobs.status <> 'RUNNING';
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
            jsonb_build_object('portfolio_id', target_portfolio::text, 'observed_on', CURRENT_DATE::text),
            'portfolio-snapshot-v1', 0, now()
        )
        ON CONFLICT (organization_id, job_type, idempotency_key) WHERE idempotency_key IS NOT NULL
        DO UPDATE SET status = 'PENDING', payload = EXCLUDED.payload, input_version = EXCLUDED.input_version,
                      progress = 0, result = NULL, result_reference = NULL, error = NULL,
                      completed_at = NULL, available_at = now(), updated_at = now()
        WHERE public.jobs.status <> 'RUNNING';
    END IF;

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS estates_enqueue_portfolio_snapshot ON public.estates;
CREATE TRIGGER estates_enqueue_portfolio_snapshot
AFTER INSERT OR UPDATE OR DELETE ON public.estates
FOR EACH ROW EXECUTE FUNCTION public.enqueue_portfolio_snapshot_on_estate_change();

-- Establish one truthful baseline after the migration. It records the state
-- observed on the migration day only; no prior dates are fabricated.
INSERT INTO public.jobs (
    id, organization_id, requested_by_user_id, job_type, status, idempotency_key,
    payload, input_version, progress, available_at
)
SELECT gen_random_uuid(), p.organization_id, NULL, 'portfolio_snapshot', 'PENDING',
       format('portfolio-snapshot:%s:%s', p.id, CURRENT_DATE),
       jsonb_build_object('portfolio_id', p.id::text, 'observed_on', CURRENT_DATE::text),
       'portfolio-snapshot-v1', 0, now()
FROM public.portfolios p
ON CONFLICT (organization_id, job_type, idempotency_key) WHERE idempotency_key IS NOT NULL
DO NOTHING;
