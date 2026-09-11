-- Close the same row-level security boundary around the remaining
-- organization-owned control-plane data. Authentication itself remains a
-- server-only operation; these policies apply after the route has resolved a
-- session and set app.organization_id for the transaction.

ALTER TABLE saved_searches ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_searches FORCE ROW LEVEL SECURITY;
ALTER TABLE property_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE property_notes FORCE ROW LEVEL SECURITY;
ALTER TABLE district_boundaries ENABLE ROW LEVEL SECURITY;
ALTER TABLE district_boundaries FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS saved_searches_tenant_policy ON saved_searches;
CREATE POLICY saved_searches_tenant_policy ON saved_searches
    USING (organization_id = current_setting('app.organization_id', true)::uuid)
    WITH CHECK (organization_id = current_setting('app.organization_id', true)::uuid);

DROP POLICY IF EXISTS property_notes_tenant_policy ON property_notes;
CREATE POLICY property_notes_tenant_policy ON property_notes
    USING (organization_id = current_setting('app.organization_id', true)::uuid)
    WITH CHECK (organization_id = current_setting('app.organization_id', true)::uuid);

DROP POLICY IF EXISTS district_boundaries_tenant_policy ON district_boundaries;
CREATE POLICY district_boundaries_tenant_policy ON district_boundaries
    USING (organization_id = current_setting('app.organization_id', true)::uuid)
    WITH CHECK (organization_id = current_setting('app.organization_id', true)::uuid);

-- A user-associated record must belong to an existing membership in the same
-- organization. These composite keys block cross-tenant references even if a
-- future repository implementation accidentally submits two valid UUIDs from
-- different organizations.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'auth_sessions_membership_same_tenant_fkey') THEN
        ALTER TABLE auth_sessions
            ADD CONSTRAINT auth_sessions_membership_same_tenant_fkey
            FOREIGN KEY (organization_id, user_id)
            REFERENCES organization_memberships (organization_id, user_id)
            ON DELETE CASCADE;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'saved_searches_membership_same_tenant_fkey') THEN
        ALTER TABLE saved_searches
            ADD CONSTRAINT saved_searches_membership_same_tenant_fkey
            FOREIGN KEY (organization_id, user_id)
            REFERENCES organization_memberships (organization_id, user_id)
            ON DELETE CASCADE;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'property_notes_membership_same_tenant_fkey') THEN
        ALTER TABLE property_notes
            ADD CONSTRAINT property_notes_membership_same_tenant_fkey
            FOREIGN KEY (organization_id, user_id)
            REFERENCES organization_memberships (organization_id, user_id)
            ON DELETE CASCADE;
    END IF;
END;
$$;
