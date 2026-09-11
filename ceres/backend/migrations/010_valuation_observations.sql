-- Research-aligned, global AVM observation contract.
-- This table contains only pseudonymous property/transaction features needed
-- by the trusted platform training process. It is not tenant request data.

CREATE TABLE IF NOT EXISTS public.valuation_observations (
    observation_id UUID PRIMARY KEY,
    property_id TEXT NOT NULL,
    transaction_id TEXT NOT NULL UNIQUE,
    listing_cluster_id TEXT,
    valuation_time TIMESTAMPTZ NOT NULL,
    available_at TIMESTAMPTZ NOT NULL,
    feature_as_of TIMESTAMPTZ NOT NULL,
    source_id TEXT NOT NULL,
    source_version TEXT NOT NULL,
    target_kind TEXT NOT NULL CHECK (target_kind IN ('transaction', 'asking')),
    transaction_nature TEXT,
    price_brl NUMERIC(16, 2) NOT NULL CHECK (price_brl > 0),
    features JSONB NOT NULL DEFAULT '{}'::jsonb,
    feature_lineage JSONB NOT NULL DEFAULT '{}'::jsonb,
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    training_allowed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT valuation_observation_temporal_features
        CHECK (feature_as_of <= valuation_time),
    CONSTRAINT valuation_observation_transaction_label
        CHECK (target_kind <> 'transaction' OR transaction_nature = 'arm_length')
);

CREATE INDEX IF NOT EXISTS valuation_observations_time_idx
    ON public.valuation_observations (target_kind, valuation_time, available_at);
CREATE INDEX IF NOT EXISTS valuation_observations_property_idx
    ON public.valuation_observations (property_id, listing_cluster_id, valuation_time);

REVOKE ALL ON TABLE public.valuation_observations FROM PUBLIC;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'anon') THEN
        REVOKE ALL ON TABLE public.valuation_observations FROM anon;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        REVOKE ALL ON TABLE public.valuation_observations FROM authenticated;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tupan_platform_intelligence') THEN
        GRANT SELECT ON TABLE public.valuation_observations TO tupan_platform_intelligence;
    END IF;
END;
$$;
