-- Create pgvector extension and base tables
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS properties (
  id TEXT PRIMARY KEY,
  title TEXT,
  address TEXT,
  city TEXT,
  neighborhood TEXT,
  latitude DOUBLE PRECISION,
  longitude DOUBLE PRECISION,
  price BIGINT,
  price_per_m2 INTEGER,
  created_date TIMESTAMP WITH TIME ZONE DEFAULT now(),
  updated_date TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS market_regions (
  id TEXT PRIMARY KEY,
  name TEXT,
  city TEXT,
  average_price_per_m2 INTEGER,
  market_heat INTEGER,
  demand_score INTEGER,
  liquidity_score INTEGER,
  created_date TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  full_name TEXT,
  email TEXT UNIQUE,
  role TEXT,
  password_hash TEXT,
  created_date TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE IF NOT EXISTS saved_searches (
  id TEXT PRIMARY KEY,
  user_id TEXT REFERENCES users(id),
  name TEXT,
  filters JSONB,
  created_date TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE IF NOT EXISTS property_notes (
  id TEXT PRIMARY KEY,
  property_id TEXT REFERENCES properties(id),
  user_id TEXT REFERENCES users(id),
  note TEXT,
  created_date TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE IF NOT EXISTS district_boundaries (
  id TEXT PRIMARY KEY,
  name TEXT,
  geojson JSONB,
  created_date TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE TABLE IF NOT EXISTS embeddings (
  id TEXT PRIMARY KEY,
  entity_type TEXT,
  entity_id TEXT,
  vector vector(1536),
  text TEXT,
  created_date TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Create simple index for embeddings similarity (adapt as needed)
-- CREATE INDEX IF NOT EXISTS embeddings_vector_idx ON embeddings USING ivfflat (vector) WITH (lists = 100);

-- Useful indexes to improve query performance
CREATE INDEX IF NOT EXISTS properties_created_date_idx ON properties (created_date DESC);
CREATE INDEX IF NOT EXISTS properties_neighborhood_idx ON properties (neighborhood);
CREATE INDEX IF NOT EXISTS properties_price_per_m2_idx ON properties (price_per_m2);
CREATE INDEX IF NOT EXISTS market_regions_created_date_idx ON market_regions (created_date DESC);
