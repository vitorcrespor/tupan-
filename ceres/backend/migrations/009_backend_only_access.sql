-- Tupan Desktop accesses data through FastAPI, not the Supabase Data API.
-- Supabase grants anon/authenticated access to new public tables/functions by
-- default. RLS alone does not protect the server-only identity/session tables.
-- Revoke client grants on Tupan objects only; leave Supabase-owned schemas and
-- grants to explicitly provisioned backend/platform roles unchanged.
DO $$
DECLARE
    table_name TEXT;
    client_role TEXT;
    function_name TEXT;
BEGIN
    FOREACH table_name IN ARRAY ARRAY[
        'organizations', 'cloud_users', 'organization_memberships', 'auth_sessions',
        'saved_searches', 'property_notes', 'district_boundaries', 'portfolios',
        'estates', 'market_observations', 'heatmap_aggregates', 'analysis_results',
        'notifications', 'jobs', 'conversations', 'conversation_messages',
        'semantic_embeddings'
    ] LOOP
        EXECUTE format('REVOKE ALL ON TABLE public.%I FROM PUBLIC', table_name);
        FOREACH client_role IN ARRAY ARRAY['anon', 'authenticated'] LOOP
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = client_role) THEN
                EXECUTE format('REVOKE ALL ON TABLE public.%I FROM %I', table_name, client_role);
            END IF;
        END LOOP;
    END LOOP;

    FOREACH function_name IN ARRAY ARRAY[
        'public.claim_next_background_job()',
        'public.recover_stale_background_jobs(integer)'
    ] LOOP
        EXECUTE format('REVOKE ALL ON FUNCTION %s FROM PUBLIC', function_name);
        FOREACH client_role IN ARRAY ARRAY['anon', 'authenticated'] LOOP
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = client_role) THEN
                EXECUTE format('REVOKE ALL ON FUNCTION %s FROM %I', function_name, client_role);
            END IF;
        END LOOP;
    END LOOP;
END;
$$;
