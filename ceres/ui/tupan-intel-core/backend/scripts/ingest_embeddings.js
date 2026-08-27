#!/usr/bin/env node
// Simple bulk importer for embeddings from a JSON file (array of {entity_type,entity_id,vector,text}).
// Usage: INGEST_FILE=embeds.json node ingest_embeddings.js

const fs = require('fs');
const { Pool } = require('pg');

async function main() {
  const file = process.env.INGEST_FILE;
  if (!file) {
    console.error('Set INGEST_FILE env to the JSON file to ingest (array of objects)');
    process.exit(1);
  }
  const raw = fs.readFileSync(file, 'utf8');
  const items = JSON.parse(raw);
  const pool = new Pool({ connectionString: process.env.DATABASE_URL });
  const batchSize = 200;
  const client = await pool.connect();
  try {
    for (let i = 0; i < items.length; i += batchSize) {
      const batch = items.slice(i, i + batchSize);
      const values = [];
      const parts = batch.map((it, idx) => {
        const id = it.id || `embed-${Date.now()}-${i + idx}`;
        const start = idx * 5 + 1;
        // id, entity_type, entity_id, vector, text, created_date
        values.push(id, it.entity_type || null, it.entity_id || null, it.vector || null, it.text || null);
        return `($${start}, $${start + 1}, $${start + 2}, $${start + 3}, $${start + 4}, now())`;
      });
      const sql = `INSERT INTO embeddings (id,entity_type,entity_id,vector,text,created_date) VALUES ${parts.join(',')}`;
      await client.query(sql, values);
      console.log(`Inserted batch ${i}..${i + batch.length - 1}`);
    }
    console.log('Ingestion complete. Run: ANALYZE embeddings; and then create index via migration or create_embeddings_index.js');
  } finally {
    client.release();
    await pool.end();
  }
}

main().catch(e => { console.error(e); process.exit(1); });
