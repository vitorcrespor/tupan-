# Tupan Backend (minimal scaffold)

This is a minimal Express + Postgres scaffold to serve the frontend at `VITE_API_URL`.

Prereqs
- Node 16+ / 18+
- PostgreSQL 14+ with `pgvector` extension (or Docker image that provides it)

Quick start
1. Copy `.env.example` to `.env` and set `DATABASE_URL` and optionally `LLM_API_URL`/`LLM_API_KEY`.
2. Install dependencies:

```bash
cd backend
npm install
```

3. Run migrations and seed (requires `psql` available and `DATABASE_URL` set):

```bash
npm run migrate
npm run seed
```

4. Start server:

```bash
npm run dev
```

Endpoints
- `GET /api/properties` — list properties
- `POST /api/properties` — create property
- `POST /api/properties/bulk` — bulk create
- `POST /api/properties/filter` — filter
- `POST /api/llm/invoke` — invoke LLM (proxies to `LLM_API_URL` if set; otherwise stub)
- `POST /api/auth/login`, `POST /api/auth/register`, `GET /api/auth/me` — minimal auth stubs

Notes
- This scaffold is intentionally minimal. Harden auth, validation, and error handling before production.
- To implement embeddings search, populate `embeddings.vector` using your embedder and create an index suited to your pgvector setup.
 - To implement embeddings search, populate `embeddings.vector` using your embedder and create an index suited to your pgvector setup. Example (pgvector/ivfflat):

```sql
CREATE INDEX IF NOT EXISTS embeddings_vector_idx ON embeddings USING ivfflat (vector) WITH (lists = 100);
```
