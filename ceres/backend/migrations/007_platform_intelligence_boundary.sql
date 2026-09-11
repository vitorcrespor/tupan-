-- Platform intelligence is calculated outside tenant request paths.  This
-- role can access only the columns required for aggregation/training, never
-- identifiers, addresses, titles, portfolios, users or organization ids.
-- Operators provision LOGIN and a secret separately; the migration creates a
-- NOLOGIN principal so policies can be installed reproducibly.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tupan_platform_intelligence') THEN
        CREATE ROLE tupan_platform_intelligence
            NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS;
    END IF;
END;
$$;

GRANT USAGE ON SCHEMA public TO tupan_platform_intelligence;
GRANT SELECT (status, location, asking_price, price_per_m2, area_m2, days_on_market, city, area,
              property_type, rooms, bathrooms, parking_spaces, age_years, exclusive, attributes,
              last_sale_price)
    ON public.estates TO tupan_platform_intelligence;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.heatmap_aggregates TO tupan_platform_intelligence;
GRANT SELECT, INSERT, UPDATE ON public.market_observations TO tupan_platform_intelligence;

DROP POLICY IF EXISTS estates_platform_intelligence_source_policy ON public.estates;
CREATE POLICY estates_platform_intelligence_source_policy ON public.estates
    FOR SELECT TO tupan_platform_intelligence
    USING (
        (status = 'active' AND location IS NOT NULL)
        OR (status = 'sold' AND last_sale_price IS NOT NULL AND last_sale_price > 0)
    );

DROP POLICY IF EXISTS heatmap_platform_intelligence_publish_policy ON public.heatmap_aggregates;
CREATE POLICY heatmap_platform_intelligence_publish_policy ON public.heatmap_aggregates
    FOR ALL TO tupan_platform_intelligence
    USING (scope = 'platform' AND organization_id IS NULL)
    WITH CHECK (scope = 'platform' AND organization_id IS NULL);

DROP POLICY IF EXISTS market_platform_intelligence_publish_policy ON public.market_observations;
CREATE POLICY market_platform_intelligence_publish_policy ON public.market_observations
    FOR ALL TO tupan_platform_intelligence
    USING (scope = 'platform' AND organization_id IS NULL)
    WITH CHECK (scope = 'platform' AND organization_id IS NULL);

-- One platform snapshot per H3 cell/version. Tenant snapshots are retired:
-- the public map must read only platform aggregates and estate mutations must
-- never enqueue an organization-specific heatmap calculation.
CREATE UNIQUE INDEX IF NOT EXISTS heatmap_aggregate_platform_version_uq
    ON public.heatmap_aggregates (h3_index, h3_resolution, period_start, period_end, input_version)
    WHERE scope = 'platform';

DROP TRIGGER IF EXISTS estates_enqueue_heatmap_refresh ON public.estates;
DROP FUNCTION IF EXISTS public.enqueue_estate_heatmap_refresh();

UPDATE public.jobs
SET status = 'FAILED',
    completed_at = COALESCE(completed_at, now()),
    error = jsonb_build_object(
        'code', 'tenant_heatmap_retired',
        'message', 'Tenant heatmap computation was replaced by the platform intelligence refresh.'
    ),
    updated_at = now()
WHERE job_type = 'heatmap_precompute' AND status = 'PENDING';
