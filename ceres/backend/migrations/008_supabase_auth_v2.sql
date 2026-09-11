-- Supabase Auth v2 bridge. Apply only to a Supabase PostgreSQL project after
-- migrations 001–007. This is additive: the legacy hash stays readable only
-- until the verified final cutover can remove it without breaking v1 users.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'auth')
        OR to_regclass('auth.users') IS NULL THEN
        RAISE EXCEPTION 'Migration 008 requires a Supabase project with auth.users.';
    END IF;
END;
$$;

ALTER TABLE cloud_users
    ADD COLUMN IF NOT EXISTS supabase_user_id UUID;

ALTER TABLE cloud_users
    ALTER COLUMN password_hash DROP NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'cloud_users_supabase_user_id_key'
    ) THEN
        ALTER TABLE cloud_users
            ADD CONSTRAINT cloud_users_supabase_user_id_key UNIQUE (supabase_user_id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'cloud_users_supabase_identity_fkey'
    ) THEN
        ALTER TABLE cloud_users
            ADD CONSTRAINT cloud_users_supabase_identity_fkey
            FOREIGN KEY (supabase_user_id)
            REFERENCES auth.users(id)
            ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'cloud_users_identity_source_check'
    ) THEN
        ALTER TABLE cloud_users
            ADD CONSTRAINT cloud_users_identity_source_check
            CHECK (supabase_user_id IS NOT NULL OR password_hash IS NOT NULL);
    END IF;
END;
$$;

CREATE INDEX IF NOT EXISTS cloud_users_supabase_user_idx
    ON cloud_users (supabase_user_id)
    WHERE supabase_user_id IS NOT NULL;

COMMENT ON COLUMN cloud_users.supabase_user_id IS
    'Verified Supabase Auth identity. Tupan authorization remains in organization_memberships.';
COMMENT ON COLUMN cloud_users.password_hash IS
    'Legacy validation-period field. Drop only after all active accounts are linked and v1 is removed.';
