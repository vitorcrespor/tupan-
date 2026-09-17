-- Shared, aggregate-only survival artifact for active-listing liquidity.
-- It contains no organization, estate, address, or customer-level records.
-- The trusted platform worker writes it offline; tenant request paths can only
-- read the newest ``scope = platform`` artifact and score already-authorized
-- estate rows locally in the backend process.

CREATE TABLE IF NOT EXISTS public.liquidity_survival_models (
    id UUID PRIMARY KEY,
    scope TEXT NOT NULL DEFAULT 'platform' CHECK (scope = 'platform'),
    model_version TEXT NOT NULL,
    trained_as_of DATE NOT NULL,
    artifact JSONB NOT NULL,
    source_observation_count INTEGER NOT NULL CHECK (source_observation_count >= 0),
    event_count INTEGER NOT NULL CHECK (event_count >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (event_count <= source_observation_count)
);

CREATE INDEX IF NOT EXISTS liquidity_survival_models_latest_idx
    ON public.liquidity_survival_models (created_at DESC)
    WHERE scope = 'platform';

ALTER TABLE public.liquidity_survival_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.liquidity_survival_models FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS liquidity_survival_models_backend_read_policy ON public.liquidity_survival_models;
CREATE POLICY liquidity_survival_models_backend_read_policy ON public.liquidity_survival_models
    FOR SELECT
    USING (scope = 'platform');

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tupan_platform_intelligence') THEN
        GRANT SELECT, INSERT, UPDATE, DELETE ON public.liquidity_survival_models TO tupan_platform_intelligence;

        DROP POLICY IF EXISTS liquidity_survival_models_platform_publish_policy ON public.liquidity_survival_models;
        CREATE POLICY liquidity_survival_models_platform_publish_policy ON public.liquidity_survival_models
            FOR ALL TO tupan_platform_intelligence
            USING (scope = 'platform')
            WITH CHECK (scope = 'platform');

        -- The platform worker receives only the duration/event and aggregate
        -- strata inputs needed for survival analysis.  It never receives IDs,
        -- portfolios, organizations, users, addresses, or geometry.
        GRANT SELECT (status, property_type, city, area, asking_price, price_per_m2,
                      days_on_market, listed_since, last_sale_date, attributes)
            ON public.estates TO tupan_platform_intelligence;

        DROP POLICY IF EXISTS estates_platform_intelligence_source_policy ON public.estates;
        CREATE POLICY estates_platform_intelligence_source_policy ON public.estates
            FOR SELECT TO tupan_platform_intelligence
            USING (
                status = 'active'
                OR (status = 'sold' AND last_sale_price IS NOT NULL AND last_sale_price > 0)
            );
    END IF;
END;
$$;

REVOKE ALL ON TABLE public.liquidity_survival_models FROM PUBLIC;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        REVOKE ALL ON TABLE public.liquidity_survival_models FROM anon;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        REVOKE ALL ON TABLE public.liquidity_survival_models FROM authenticated;
    END IF;
END;
$$;
