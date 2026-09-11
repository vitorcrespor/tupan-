# Retired backend scaffold

> **Do not deploy or add features here.** Tupan's canonical backend is `ceres/backend/api/main.py`, served as `backend.api.main:app` under `/api/v1`. This directory is retained solely to support a controlled data migration from its old schema.

# Tupan FastAPI scaffold

Minimal FastAPI communication base for `tupan-intel-core` frontend.

Requirements

- Python 3.10+
- PostgreSQL 14+ with `pgvector` extension

Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Setup DB

- Create DB and enable pgvector:

```sql
CREATE DATABASE tupan;
\c tupan
CREATE EXTENSION IF NOT EXISTS vector;
```

- Run migrations:

```bash
psql $DATABASE_URL -f migrations/001_init.sql
```

Run

```bash
export DATABASE_URL=postgresql://postgres:password@localhost:5432/tupan
export LLM_API_URL=
uvicorn backend-fastapi.app.main:app --reload --port 4001
```

Run migrations and seed (requires `psql`):

```bash
psql $DATABASE_URL -f migrations/001_init.sql
psql $DATABASE_URL -f seed/seed.sql
```

Notes

- `LLM_API_URL` can point to an external LLM endpoint the `POST /api/llm/invoke` route proxies to.
- This scaffold is intentionally small; add authentication, validation, and remaining entity routes as needed.
 - To enable efficient vector similarity, create an index once you've populated embeddings. Example (pgvector/ivfflat):

```sql
-- Adjust lists to suit data size and pgvector tuning
CREATE INDEX IF NOT EXISTS embeddings_vector_idx ON embeddings USING ivfflat (vector) WITH (lists = 100);
```
