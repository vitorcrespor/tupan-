-- The trusted platform-intelligence process may ingest verified, global AVM
-- observations. Desktop clients, PostgREST roles and tenant request paths keep
-- having no access to this training-only table.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'tupan_platform_intelligence') THEN
        GRANT INSERT, UPDATE ON TABLE public.valuation_observations
            TO tupan_platform_intelligence;
    END IF;
END;
$$;
