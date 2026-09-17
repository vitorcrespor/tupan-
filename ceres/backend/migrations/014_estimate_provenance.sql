-- Forward-only provenance. Existing estimates retain unknown lineage.
ALTER TABLE public.estates ADD COLUMN IF NOT EXISTS estimate_provenance JSONB;

CREATE OR REPLACE FUNCTION public.track_estimate_provenance()
RETURNS trigger LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
DECLARE
    input_snapshot JSONB;
    input_version TEXT;
BEGIN
    input_snapshot := to_jsonb(NEW) - ARRAY[
        'estimated_price', 'estimate_provenance', 'updated_at', 'created_at',
        'portfolio_id', 'title', 'summary', 'external_id', 'source_name'
    ];
    input_version := 'estate-input-v1:' || md5(input_snapshot::text);
    IF NEW.estimated_price IS NULL THEN
        NEW.estimate_provenance := NULL;
    ELSIF TG_OP = 'INSERT' THEN
        NEW.estimate_provenance := jsonb_build_object(
            'source', 'recorded', 'recorded_at', statement_timestamp(),
            'model_version', NULL, 'input_version', input_version,
            'status', 'recorded');
    ELSIF NEW.estimated_price IS DISTINCT FROM OLD.estimated_price THEN
        -- A changed value must never inherit a previous model attribution.
        NEW.estimate_provenance := jsonb_build_object(
            'source', 'recorded', 'recorded_at', statement_timestamp(),
            'model_version', NULL, 'input_version', input_version,
            'status', 'recorded');
    ELSE
        -- Client writes cannot replace lineage through arbitrary attributes.
        NEW.estimate_provenance := OLD.estimate_provenance;
        IF NEW.estimate_provenance IS NOT NULL
           AND NEW.estimate_provenance->>'input_version' IS DISTINCT FROM input_version THEN
            NEW.estimate_provenance := jsonb_set(NEW.estimate_provenance, '{status}', '"inputs_changed"');
        END IF;
    END IF;
    RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION public.track_estimate_provenance() FROM PUBLIC;
DROP TRIGGER IF EXISTS estates_estimate_provenance ON public.estates;
CREATE TRIGGER estates_estimate_provenance
BEFORE INSERT OR UPDATE ON public.estates
FOR EACH ROW EXECUTE FUNCTION public.track_estimate_provenance();
