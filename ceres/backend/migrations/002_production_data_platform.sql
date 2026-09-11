-- Tupan production data platform: PostgreSQL + PostGIS + pgvector.
-- This migration is additive. Legacy Chroma, Excel, JSONL and model artifacts
-- remain readable during parity verification and are not removed here.

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS vector;

-- The application stores only these roles. Authorization is resolved from the
-- server-side session; clients never select an organization or effective role.
DO $$ BEGIN
    CREATE TYPE membership_role AS ENUM ('admin', 'user');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE estate_status AS ENUM ('active', 'sold', 'off_market', 'archived');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE job_status AS ENUM ('queued', 'running', 'succeeded', 'failed', 'cancelled');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS portfolios (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name TEXT NOT NULL CHECK (char_length(name) BETWEEN 1 AND 160),
    description TEXT,
    target_commission NUMERIC(7, 6),
    created_by_user_id UUID REFERENCES cloud_users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (organization_id, name)
);
CREATE INDEX IF NOT EXISTS portfolios_tenant_idx ON portfolios (organization_id, created_at DESC);

CREATE TABLE IF NOT EXISTS estates (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    portfolio_id UUID REFERENCES portfolios(id) ON DELETE SET NULL,
    external_id TEXT,
    source_name TEXT,
    status estate_status NOT NULL DEFAULT 'active',
    title TEXT,
    summary TEXT,
    property_type TEXT,
    exclusive BOOLEAN,
    asking_price NUMERIC(16, 2),
    last_sale_price NUMERIC(16, 2),
    estimated_price NUMERIC(16, 2),
    area_m2 NUMERIC(12, 2),
    price_per_m2 NUMERIC(16, 2),
    rooms SMALLINT,
    bathrooms SMALLINT,
    parking_spaces SMALLINT,
    age_years SMALLINT,
    days_on_market NUMERIC(12, 2),
    listed_since DATE,
    last_sale_date DATE,
    address TEXT,
    city TEXT,
    area TEXT,
    state TEXT,
    postal_code TEXT,
    location GEOGRAPHY(POINT, 4326),
    attributes JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT estates_positive_price CHECK (asking_price IS NULL OR asking_price >= 0),
    CONSTRAINT estates_positive_area CHECK (area_m2 IS NULL OR area_m2 > 0),
    CONSTRAINT estates_coordinate_consistency CHECK (
        location IS NULL OR ST_SRID(location::geometry) = 4326
    )
);
CREATE INDEX IF NOT EXISTS estates_tenant_idx ON estates (organization_id, status, created_at DESC);
CREATE INDEX IF NOT EXISTS estates_portfolio_tenant_idx ON estates (organization_id, portfolio_id);
CREATE INDEX IF NOT EXISTS estates_location_gix ON estates USING GIST (location);
CREATE UNIQUE INDEX IF NOT EXISTS estates_source_identity_uq
    ON estates (organization_id, source_name, external_id)
    WHERE source_name IS NOT NULL AND external_id IS NOT NULL;

-- Market data may be tenant-scoped or explicitly platform-scoped. Platform
-- observations are not owned by any customer organization and are exposed only
-- through deliberate repository methods, never through a client supplied id.
CREATE TABLE IF NOT EXISTS market_observations (
    id UUID PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    scope TEXT NOT NULL DEFAULT 'tenant' CHECK (scope IN ('tenant', 'platform')),
    observed_on DATE NOT NULL,
    metric TEXT NOT NULL,
    value NUMERIC(18, 6) NOT NULL,
    unit TEXT,
    property_type TEXT,
    city TEXT,
    area TEXT,
    h3_index TEXT,
    geography GEOGRAPHY(GEOMETRY, 4326),
    source_name TEXT NOT NULL,
    source_reference TEXT,
    dimensions JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK ((scope = 'tenant' AND organization_id IS NOT NULL) OR (scope = 'platform' AND organization_id IS NULL))
);
CREATE INDEX IF NOT EXISTS market_observations_tenant_idx
    ON market_observations (organization_id, metric, observed_on DESC);
CREATE INDEX IF NOT EXISTS market_observations_platform_idx
    ON market_observations (metric, city, area, observed_on DESC) WHERE scope = 'platform';
CREATE INDEX IF NOT EXISTS market_observations_geography_gix ON market_observations USING GIST (geography);

CREATE TABLE IF NOT EXISTS heatmap_aggregates (
    id UUID PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    scope TEXT NOT NULL DEFAULT 'tenant' CHECK (scope IN ('tenant', 'platform')),
    h3_index TEXT NOT NULL,
    h3_resolution SMALLINT NOT NULL CHECK (h3_resolution BETWEEN 0 AND 15),
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    city TEXT,
    area TEXT,
    boundary GEOGRAPHY(POLYGON, 4326),
    center GEOGRAPHY(POINT, 4326),
    metrics JSONB NOT NULL,
    input_version TEXT NOT NULL,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (period_end >= period_start),
    CHECK ((scope = 'tenant' AND organization_id IS NOT NULL) OR (scope = 'platform' AND organization_id IS NULL))
);
CREATE UNIQUE INDEX IF NOT EXISTS heatmap_aggregate_version_uq
    ON heatmap_aggregates (organization_id, h3_index, h3_resolution, period_start, period_end, input_version)
    WHERE scope = 'tenant';
CREATE INDEX IF NOT EXISTS heatmap_aggregates_scope_idx
    ON heatmap_aggregates (organization_id, h3_resolution, period_end DESC);
CREATE INDEX IF NOT EXISTS heatmap_aggregates_boundary_gix ON heatmap_aggregates USING GIST (boundary);

CREATE TABLE IF NOT EXISTS analysis_results (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    estate_id UUID REFERENCES estates(id) ON DELETE CASCADE,
    portfolio_id UUID REFERENCES portfolios(id) ON DELETE CASCADE,
    analysis_type TEXT NOT NULL,
    algorithm_version TEXT,
    input_version TEXT,
    result JSONB NOT NULL,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by_user_id UUID REFERENCES cloud_users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS analysis_results_tenant_idx ON analysis_results (organization_id, analysis_type, created_at DESC);
CREATE INDEX IF NOT EXISTS analysis_results_estate_idx ON analysis_results (organization_id, estate_id, created_at DESC);

CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES cloud_users(id) ON DELETE CASCADE,
    analysis_result_id UUID REFERENCES analysis_results(id) ON DELETE SET NULL,
    notification_type TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS notifications_tenant_user_idx ON notifications (organization_id, user_id, read_at, created_at DESC);

CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    requested_by_user_id UUID REFERENCES cloud_users(id) ON DELETE SET NULL,
    job_type TEXT NOT NULL,
    status job_status NOT NULL DEFAULT 'queued',
    idempotency_key TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    result JSONB,
    error JSONB,
    input_version TEXT,
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    available_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS jobs_tenant_idempotency_uq
    ON jobs (organization_id, job_type, idempotency_key)
    WHERE idempotency_key IS NOT NULL;
CREATE INDEX IF NOT EXISTS jobs_claim_idx ON jobs (status, available_at, created_at) WHERE status = 'queued';
CREATE INDEX IF NOT EXISTS jobs_tenant_idx ON jobs (organization_id, created_at DESC);

CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID REFERENCES cloud_users(id) ON DELETE SET NULL,
    title TEXT,
    context JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS conversations_tenant_user_idx ON conversations (organization_id, user_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS conversation_messages (
    id UUID PRIMARY KEY,
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'tool', 'system')),
    content JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS conversation_messages_tenant_idx ON conversation_messages (organization_id, conversation_id, created_at);

-- pgvector is exclusively for semantic similarity. Business, pricing and
-- geographic fields remain in their proper relational/PostGIS columns.
CREATE TABLE IF NOT EXISTS semantic_embeddings (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    entity_type TEXT NOT NULL,
    entity_id UUID NOT NULL,
    embedding vector(1536) NOT NULL,
    embedding_model TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (organization_id, entity_type, entity_id, embedding_model)
);
CREATE INDEX IF NOT EXISTS semantic_embeddings_tenant_entity_idx
    ON semantic_embeddings (organization_id, entity_type, entity_id);
-- Add a tuned HNSW/IVFFlat index after embedding volume and production query
-- patterns are known; do not use pgvector as a general property datastore.

-- Tenant-composite foreign keys prevent cross-organization relationships even
-- if an application query accidentally provides a valid foreign UUID.
ALTER TABLE portfolios
    ADD CONSTRAINT portfolios_id_organization_uq UNIQUE (id, organization_id);
ALTER TABLE estates
    ADD CONSTRAINT estates_id_organization_uq UNIQUE (id, organization_id);
ALTER TABLE analysis_results
    ADD CONSTRAINT analysis_results_id_organization_uq UNIQUE (id, organization_id);
ALTER TABLE conversations
    ADD CONSTRAINT conversations_id_organization_uq UNIQUE (id, organization_id);

ALTER TABLE estates
    ADD CONSTRAINT estates_portfolio_same_tenant_fkey
    FOREIGN KEY (portfolio_id, organization_id)
    REFERENCES portfolios (id, organization_id) ON DELETE SET NULL (portfolio_id);
ALTER TABLE analysis_results
    ADD CONSTRAINT analysis_results_estate_same_tenant_fkey
    FOREIGN KEY (estate_id, organization_id)
    REFERENCES estates (id, organization_id) ON DELETE CASCADE;
ALTER TABLE analysis_results
    ADD CONSTRAINT analysis_results_portfolio_same_tenant_fkey
    FOREIGN KEY (portfolio_id, organization_id)
    REFERENCES portfolios (id, organization_id) ON DELETE CASCADE;
ALTER TABLE notifications
    ADD CONSTRAINT notifications_analysis_same_tenant_fkey
    FOREIGN KEY (analysis_result_id, organization_id)
    REFERENCES analysis_results (id, organization_id) ON DELETE SET NULL (analysis_result_id);
ALTER TABLE conversation_messages
    ADD CONSTRAINT messages_conversation_same_tenant_fkey
    FOREIGN KEY (conversation_id, organization_id)
    REFERENCES conversations (id, organization_id) ON DELETE CASCADE;
-- Database-level defence in depth. Repositories set app.organization_id inside
-- each transaction. With RLS enabled, an omitted tenant WHERE clause cannot
-- accidentally reveal tenant data.
ALTER TABLE portfolios ENABLE ROW LEVEL SECURITY;
ALTER TABLE estates ENABLE ROW LEVEL SECURITY;
ALTER TABLE market_observations ENABLE ROW LEVEL SECURITY;
ALTER TABLE heatmap_aggregates ENABLE ROW LEVEL SECURITY;
ALTER TABLE analysis_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE semantic_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolios FORCE ROW LEVEL SECURITY;
ALTER TABLE estates FORCE ROW LEVEL SECURITY;
ALTER TABLE market_observations FORCE ROW LEVEL SECURITY;
ALTER TABLE heatmap_aggregates FORCE ROW LEVEL SECURITY;
ALTER TABLE analysis_results FORCE ROW LEVEL SECURITY;
ALTER TABLE notifications FORCE ROW LEVEL SECURITY;
ALTER TABLE jobs FORCE ROW LEVEL SECURITY;
ALTER TABLE conversations FORCE ROW LEVEL SECURITY;
ALTER TABLE conversation_messages FORCE ROW LEVEL SECURITY;
ALTER TABLE semantic_embeddings FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS portfolios_tenant_policy ON portfolios;
CREATE POLICY portfolios_tenant_policy ON portfolios
    USING (organization_id = current_setting('app.organization_id', true)::uuid)
    WITH CHECK (organization_id = current_setting('app.organization_id', true)::uuid);

DROP POLICY IF EXISTS estates_tenant_policy ON estates;
CREATE POLICY estates_tenant_policy ON estates
    USING (organization_id = current_setting('app.organization_id', true)::uuid)
    WITH CHECK (organization_id = current_setting('app.organization_id', true)::uuid);

-- Platform market data is explicitly shared, while tenant records remain RLS scoped.
DROP POLICY IF EXISTS market_observations_tenant_policy ON market_observations;
CREATE POLICY market_observations_tenant_policy ON market_observations
    USING (scope = 'platform' OR organization_id = current_setting('app.organization_id', true)::uuid)
    WITH CHECK (scope = 'tenant' AND organization_id = current_setting('app.organization_id', true)::uuid);

DROP POLICY IF EXISTS heatmap_aggregates_tenant_policy ON heatmap_aggregates;
CREATE POLICY heatmap_aggregates_tenant_policy ON heatmap_aggregates
    USING (scope = 'platform' OR organization_id = current_setting('app.organization_id', true)::uuid)
    WITH CHECK (scope = 'tenant' AND organization_id = current_setting('app.organization_id', true)::uuid);

DROP POLICY IF EXISTS analysis_results_tenant_policy ON analysis_results;
CREATE POLICY analysis_results_tenant_policy ON analysis_results
    USING (organization_id = current_setting('app.organization_id', true)::uuid)
    WITH CHECK (organization_id = current_setting('app.organization_id', true)::uuid);

DROP POLICY IF EXISTS notifications_tenant_policy ON notifications;
CREATE POLICY notifications_tenant_policy ON notifications
    USING (organization_id = current_setting('app.organization_id', true)::uuid)
    WITH CHECK (organization_id = current_setting('app.organization_id', true)::uuid);

DROP POLICY IF EXISTS jobs_tenant_policy ON jobs;
CREATE POLICY jobs_tenant_policy ON jobs
    USING (organization_id = current_setting('app.organization_id', true)::uuid)
    WITH CHECK (organization_id = current_setting('app.organization_id', true)::uuid);

DROP POLICY IF EXISTS conversations_tenant_policy ON conversations;
CREATE POLICY conversations_tenant_policy ON conversations
    USING (organization_id = current_setting('app.organization_id', true)::uuid)
    WITH CHECK (organization_id = current_setting('app.organization_id', true)::uuid);

DROP POLICY IF EXISTS conversation_messages_tenant_policy ON conversation_messages;
CREATE POLICY conversation_messages_tenant_policy ON conversation_messages
    USING (organization_id = current_setting('app.organization_id', true)::uuid)
    WITH CHECK (organization_id = current_setting('app.organization_id', true)::uuid);

DROP POLICY IF EXISTS semantic_embeddings_tenant_policy ON semantic_embeddings;
CREATE POLICY semantic_embeddings_tenant_policy ON semantic_embeddings
    USING (organization_id = current_setting('app.organization_id', true)::uuid)
    WITH CHECK (organization_id = current_setting('app.organization_id', true)::uuid);

-- The database role used by the API must not have BYPASSRLS. Background worker
-- transactions set the originating job's organization id before any query.