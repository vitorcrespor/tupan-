-- Tupan Cloud control plane. Apply with a database role that can create tables.
-- Domain-property migration deliberately remains separate: existing Chroma records
-- do not carry organization ownership and must not be auto-assigned.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS organizations (
    id UUID PRIMARY KEY,
    name TEXT NOT NULL CHECK (char_length(name) BETWEEN 1 AND 160),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS cloud_users (
    id UUID PRIMARY KEY,
    email TEXT NOT NULL UNIQUE CHECK (email = lower(email)),
    full_name TEXT,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS organization_memberships (
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES cloud_users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('admin', 'user')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (organization_id, user_id)
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES cloud_users(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    token_hash BYTEA NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS auth_sessions_expiry_idx ON auth_sessions (expires_at);
CREATE INDEX IF NOT EXISTS auth_sessions_identity_idx ON auth_sessions (user_id, organization_id);

CREATE TABLE IF NOT EXISTS saved_searches (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES cloud_users(id) ON DELETE CASCADE,
    name TEXT NOT NULL CHECK (char_length(name) BETWEEN 1 AND 160),
    filters JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS saved_searches_scope_idx ON saved_searches (organization_id, user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS property_notes (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    property_id TEXT NOT NULL,
    user_id UUID NOT NULL REFERENCES cloud_users(id) ON DELETE CASCADE,
    note TEXT NOT NULL CHECK (char_length(note) BETWEEN 1 AND 10000),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS property_notes_scope_idx ON property_notes (organization_id, property_id, created_at DESC);

CREATE TABLE IF NOT EXISTS district_boundaries (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    geojson JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS district_boundaries_scope_idx ON district_boundaries (organization_id, name);

-- Future canonical domain tables must include organization_id and enforce a
-- foreign key to organizations. Do not expose the global legacy Chroma
-- collection to cloud tenants until the ownership migration is complete.