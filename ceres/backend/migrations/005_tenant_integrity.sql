-- Preserve tenant teardown integrity. An organization delete cascades to its
-- estates; at that point the organization no longer exists, so no heatmap
-- refresh may be queued for it.

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

        -- During ON DELETE CASCADE from organizations, the parent has already
        -- gone. Skip derived work for a tenant that is being removed.
        IF NOT EXISTS (SELECT 1 FROM public.organizations WHERE id = target_organization) THEN
            RETURN OLD;
        END IF;
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
