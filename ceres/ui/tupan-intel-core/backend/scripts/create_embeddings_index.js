#!/usr/bin/env node
const { Client } = require('pg');

async function main() {
  const client = new Client({ connectionString: process.env.DATABASE_URL });
  await client.connect();
  try {
    console.log('Creating ivfflat index on embeddings.vector (if supported)...');
    await client.query('CREATE INDEX IF NOT EXISTS embeddings_vector_ivfflat_idx ON embeddings USING ivfflat (vector) WITH (lists = 100)');
    console.log('Index command executed. If using ivfflat, run: ANALYZE embeddings; after bulk load.');
  } catch (e) {
    console.error('Index creation failed:', e.message);
  } finally {
    await client.end();
  }
}

main().catch((e) => { console.error(e); process.exit(1); });
