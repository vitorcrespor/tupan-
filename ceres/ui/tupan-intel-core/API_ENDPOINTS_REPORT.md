# API & Endpoint Report — tupan-intel-core

Date: 2026-08-15

Overview
- The frontend currently uses a local/mock client in [src/api/appClient.js](src/api/appClient.js#L1-L400). To replace mocked data with Postgres + pgvector, the backend should expose a REST/HTTP API that mirrors the entity methods the frontend expects.
- I added a REST-fallback implementation in `appClient` that will call `VITE_API_URL` if set; otherwise the existing mock/localStorage behavior remains.

Environment variables
- `VITE_API_URL` — (recommended) base URL of your backend (e.g. `http://localhost:4000`). When set, the client will call the REST endpoints instead of local seeds.
- `VITE_AI_API_URL` — optional LLM provider base (used historically as a hint; merged into `VITE_API_URL` usage).
- `VITE_GOOGLE_MAPS_API_KEY` — used for maps config via `appClient.functions.invoke('mapsKey')`.
- `VITE_ENABLE_CHART_EXPANSION` — UI feature flag read in `src/lib/featureFlags.js`.

Frontend usage -> Backend endpoints mapping
These are the endpoints the frontend expects (I've grouped them by responsibility). Implement these on your backend and point `VITE_API_URL` to it.

Auth
- POST /api/auth/login                        — body: { email, password }
- POST /api/auth/register                     — body: { email, password, ... }
- GET  /api/auth/me                           — returns current user
- POST /api/auth/verify                       — OTP verify
- POST /api/auth/resend                       — resend OTP
- POST /api/auth/reset-request                — request reset
- POST /api/auth/reset                        — perform reset
- GET  /api/auth/provider/:provider           — redirects to OAuth provider
- GET  /api/auth/logout                       — perform logout

Entities (CRUD + extras)
For each entity implement standard CRUD plus the list/filter/bulk endpoints used by the client. Note: implemented routes in this repo use hyphenated plural paths (e.g. `/api/market-regions`).

- Properties
	- GET    /api/properties                  — query: ?sort=&limit=&q=
	- POST   /api/properties                  — create property
	- POST   /api/properties/bulk             — bulk create
	- POST   /api/properties/filter           — body: { query, sort, limit }
	- GET    /api/properties/:id              — fetch one
	- PUT    /api/properties/:id              — update
	- DELETE /api/properties/:id              — delete

- MarketRegions (implemented as `/api/market-regions`)
	- GET    /api/market-regions
	- POST   /api/market-regions
	- POST   /api/market-regions/bulk
	- POST   /api/market-regions/filter
	- GET    /api/market-regions/:id
	- PUT    /api/market-regions/:id
	- DELETE /api/market-regions/:id

- Users (implemented as `/api/users`)
	- GET    /api/users
	- POST   /api/users
	- POST   /api/users/filter
	- GET    /api/users/:id
	- PUT    /api/users/:id
	- DELETE /api/users/:id

- SavedSearches (implemented as `/api/saved-searches`)
	- GET    /api/saved-searches
	- POST   /api/saved-searches
	- POST   /api/saved-searches/filter
	- GET    /api/saved-searches/:id
	- PUT    /api/saved-searches/:id
	- DELETE /api/saved-searches/:id

- PropertyNotes (implemented as `/api/property-notes`)
	- GET    /api/property-notes?property_id=... or /api/property-notes?sort=&limit=
	- POST   /api/property-notes
	- POST   /api/property-notes/filter
	- GET    /api/property-notes/:id
	- PUT    /api/property-notes/:id
	- DELETE /api/property-notes/:id

- DistrictBoundaries (implemented as `/api/district-boundaries`)
	- GET    /api/district-boundaries
	- POST   /api/district-boundaries
	- POST   /api/district-boundaries/filter
	- GET    /api/district-boundaries/:id
	- PUT    /api/district-boundaries/:id
	- DELETE /api/district-boundaries/:id

Functions & utilities
- POST /api/functions/:name                  — generic function invocation (mapsKey, getMapsConfig)

Files & extraction
- POST /api/files/upload                     — multipart form upload, returns { file_url }
- POST /api/files/extract                    — body: { file_url, json_schema } -> returns extracted data

LLM / Embeddings / Search
- POST /api/llm/invoke                       — body: { prompt } -> returns model output (text or structured)
- POST /api/embeddings                       — body: { entity_type, entity_id, vector, text } -> store embedding in pgvector (POST /api/embeddings)
- POST /api/embeddings/search                — body: { vector, top_k } -> returns nearest items using pgvector similarity (POST /api/embeddings/search)

Suggested DB schema (high level)
- properties (id PK, title, address, city, neighborhood, latitude, longitude, property_type, bedrooms, bathrooms, parking_spaces, area_m2, price, suggested_price, price_per_m2, price_deviation, valuation_confidence, valuation_class, comparable_count, days_on_market, market_heat, liquidity_score, luxury_score, leisure_score, location_score, leverage_score, property_age, status, created_date, updated_date)
- market_regions (id PK, name, city, avg_price_per_m2, market_heat, demand_score, liquidity_score, created_date)
- users (id PK, full_name, email, role, password_hash, created_date)
- saved_searches (id PK, user_id FK, name, filters JSON, created_date)
- property_notes (id PK, property_id FK, user_id FK, note TEXT, created_date)
- district_boundaries (id PK, name, geojson JSON, created_date)
- embeddings (id PK, entity_type, entity_id, vector vector(1536), text, created_date) — requires pgvector extension

Frontend file references (where client calls appear)
- [src/api/appClient.js](src/api/appClient.js#L1-L400) — mock client + REST fallback
- [src/lib/useTupanData.js](src/lib/useTupanData.js#L1-L40) — loads properties and market regions
- [src/lib/useMapBoundaries.js](src/lib/useMapBoundaries.js#L1-L60) — calls functions.invoke('getMapsConfig') and loads district boundaries
- [src/lib/AuthContext.jsx](src/lib/AuthContext.jsx#L1-L120) — uses `auth.me()` and auth helpers
- [src/pages/DataManagement.jsx](src/pages/DataManagement.jsx#L1-L200) — creates, deletes properties and calls integrations for file upload/extract
- [src/pages/IntelligenceAgent.jsx](src/pages/IntelligenceAgent.jsx#L1-L120) — calls `integrations.Core.InvokeLLM`
- [src/pages/ReportBuilder.jsx](src/pages/ReportBuilder.jsx#L1-L120) — calls `InvokeLLM` for report text
- [src/pages/TeamManagement.jsx](src/pages/TeamManagement.jsx#L1-L120) — lists and updates users
- [src/components/tupan/Heatmap3D.jsx](src/components/tupan/Heatmap3D.jsx#L1-L80) — requests mapsKey function

Recommended implementation notes
- Expose a single base: `VITE_API_URL` (e.g. `http://localhost:4000`). Frontend `appClient` will switch to REST automatically when set.
- Implement pagination and filtering on list endpoints to avoid sending huge payloads to the client.
- Use `pgvector` for embeddings and `ivfflat`/`hnsw` indexes for efficient similarity search.
- Secure auth endpoints (JWT or session) and return consistent user objects that match the mock shape used in the frontend (`id`, `full_name`, `email`, `role`).

Quick run & dev notes
1. Backend stack suggestion: Node.js + Express + pg (node-postgres) + pgvector extension. Alternatively use Python (FastAPI) + asyncpg + pgvector.
2. Create migrations (sql or using a migration tool) to add tables and `CREATE EXTENSION IF NOT EXISTS vector;`.
3. Start backend locally and set `.env` or Vite env: `VITE_API_URL=http://localhost:4000` and optionally `VITE_GOOGLE_MAPS_API_KEY=...`.

Example curl (list properties)
```bash
curl "${VITE_API_URL:-http://localhost:4000}/api/properties?sort=-created_date&limit=200"
```

Next steps I can take for you (choose one):
- Scaffold a minimal Express backend with the above endpoints and SQL schema, plus migrations and seed script.
- Implement only the LLM/embeddings endpoints (pgvector + embedding ingestion + search).
- Patch the rest of the frontend to add types/guards and validate server responses.

Tell me which of the above to scaffold first and I'll generate the code and apply it to the repo.

**Setup & Run (concise)**

- Prerequisites:
	- Node 18+ (or 16+), npm/yarn
	- PostgreSQL 14+ with `pgvector` extension (or Docker)

- Quick Postgres setup (local):
	1. Create DB: `createdb tupan` or in psql: `CREATE DATABASE tupan;`.
 2. Connect and enable pgvector:
		```sql
		CREATE EXTENSION IF NOT EXISTS vector;
		```

- Minimal migration SQL (example for `properties`):
	```sql
	CREATE TABLE properties (
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
	-- embeddings table (pgvector)
	CREATE TABLE embeddings (
		id TEXT PRIMARY KEY,
		entity_type TEXT,
		entity_id TEXT,
		vector vector(1536),
		text TEXT,
		created_date TIMESTAMP WITH TIME ZONE DEFAULT now()
	);
	```

- Backend scaffold (recommended stack):
	- Node + Express + `pg` (node-postgres) + `pgvector` client or `ivfflat` index.
	- Provide endpoints under `/api/*` matching the report.

- Env vars (backend & frontend):
	- `VITE_API_URL` — base URL for frontend to call (e.g. `http://localhost:4000`).
	- `VITE_GOOGLE_MAPS_API_KEY` — maps key.
	- Backend: `DATABASE_URL=postgres://user:pass@host:5432/tupan`, `PORT=4000`.

- Dev run (example):
	1. Start Postgres (or Docker compose).
	2. Run migrations to create tables and extension.
	3. In `backend/`:
		 ```bash
		 npm install
		 npm run dev   # starts Express server on $PORT
		 ```
	4. In frontend project root:
		 ```bash
		 VITE_API_URL=http://localhost:4000 npm run dev
		 ```

- Test examples:
	- List properties: `curl "$VITE_API_URL/api/properties?limit=20"`
	- Invoke LLM: `curl -X POST $VITE_API_URL/api/llm/invoke -d '{"prompt":"hi"}' -H 'Content-Type: application/json'`

- Security & production notes (short):
	- Use HTTPS and secure cookies or JWT for auth.
	- Rate-limit LLM and file endpoints; validate uploads.
	- Use proper DB migrations (Flyway, Alembic, or node-pg-migrate) and backup strategies.

	Current implementation status (2026-08-15)
	- Backends scaffolded: two implementations present in the repo:
		- `backend/` — Node.js + Express implementation with routes under `backend/routes/*` matching the report (hyphenated plural paths). Includes Joi/Celebrate request validation, JWT auth, and LLM proxy with timeouts/retries/circuit-breaker.
		- `backend-fastapi/` — FastAPI implementation under `backend-fastapi/app/` with Pydantic `schemas.py`, async DB helpers, and the same set of entity routers. LLM proxy hardened with retries/timeout and a simple circuit breaker.
	- Embeddings support:
		- `backend/migrations/001_init.sql` creates `embeddings` with `vector(1536)`.
		- `backend/migrations/002_create_embeddings_index.sql` added (ivfflat example).
		- Ingestion helper: `backend/scripts/ingest_embeddings.js` (batch importer) and `backend/scripts/create_embeddings_index.js`.
	- Dev infra & tests:
		- `docker-compose.yml` to run Postgres + both backends.
		- `backend/Dockerfile` and `backend-fastapi/Dockerfile` added.
		- Basic CI workflow: `.github/workflows/ci.yml` runs `docker-compose` and `scripts/smoke_test.js`.
		- Smoke test: `scripts/smoke_test.js`.
	- Logging & monitoring:
		- Express: optional `backend/logger.js` (winston) and request logging hook.
		- FastAPI: simple logging initializer at `backend-fastapi/app/logging.py`.
	- What's pending / manual review:
		- Security review: tighten CORS, TLS, secrets management, dependency audit, rate-limit tuning, and audit of endpoints for exposure. (Not applied automatically.)
		- Production readiness: consider rotating secrets, using managed DB credentials, and adding centralized logging/metrics.

	If you'd like, I can: run the repo smoke tests now (Docker Compose), or produce a short security checklist and automatically apply low-risk hardening (CORS tightening, stricter rate-limits, and env-var guidance).

**I made these additions here; tell me if you want me to scaffold the backend now (Express + migrations + seed).**
