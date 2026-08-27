-- Create a vector index for the embeddings table. Run this AFTER loading vectors and running ANALYZE.
-- Adjust the index type to your pgvector version (ivfflat or hnsw). Example below uses ivfflat.

CREATE INDEX IF NOT EXISTS embeddings_vector_ivfflat_idx ON embeddings USING ivfflat (vector) WITH (lists = 100);

-- If you prefer HNSW (pgvector 0.6+), use an index like:
-- CREATE INDEX IF NOT EXISTS embeddings_vector_hnsw_idx ON embeddings USING hnsw (vector) WITH (m = 16, ef_construction = 200);

-- Note: For ivfflat you must run "ANALYZE embeddings;" after populating vectors and you may need to tune "lists".
