# Tupan / Ceres local development

The supported integrated runtime has two independently started processes:

- FastAPI: `backend.api.main:app`, served on `http://127.0.0.1:8000`.
- React/Vite: `ui/tupan-intel-core`, served on `http://127.0.0.1:5173`.

The `ui/tupan-intel-core/backend` and `ui/tupan-intel-core/backend-fastapi`
directories are older standalone backends. They are not part of this integrated
local workflow.

## Requirements

- Python 3.13.3 is available in this workspace; use a compatible Python version
  supported by the packages in `requirements.txt`.
- Node.js LTS with npm.
- Valid OpenAI and Google API credentials for provider-backed property search,
  geocoding, and AI interpretation. The health endpoint itself does not
  require provider credentials or loaded data.

## 1. Start the API

From the `ceres` directory, create the local settings file only if it does not
already exist, then review and fill in the required keys and paths:

```powershell
Set-Location 'C:\Users\Usuario\OneDrive\Área de Trabalho\tupan\ceres'
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
New-Item -ItemType Directory -Force -Path logs | Out-Null
```

Create a fresh virtual environment, then install the combined API, ML,
geospatial, and agent dependencies. The existing `.venv` in this workspace
references a missing Python 3.12 interpreter, so the commands deliberately use
`.venv-local` instead of modifying it:

```powershell
py -3.13 -m venv .venv-local
.\.venv-local\Scripts\python.exe -m pip install --upgrade pip
.\.venv-local\Scripts\python.exe -m pip install -r requirements.txt
```

Start the real FastAPI entry point. `--env-file .env` makes the API and its
lazy-loaded existing services read the local configuration consistently:

```powershell
.\.venv-local\Scripts\python.exe -m uvicorn backend.api.main:app --reload --host 127.0.0.1 --port 8000 --env-file .env
```

The API is available at `http://127.0.0.1:8000/api/v1`, interactive API docs
at `http://127.0.0.1:8000/api/v1/docs`, and liveness check at
`http://127.0.0.1:8000/api/v1/health`.

Verify it from a second PowerShell terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

Expected result:

```json
{ "status": "ok" }
```

## 2. Start the frontend

Use a separate terminal. The frontend configuration belongs in its own
`.env.local`, not the API's root `.env`:

```powershell
Set-Location 'C:\Users\Usuario\OneDrive\Área de Trabalho\tupan\ceres\ui\tupan-intel-core'
if (-not (Test-Path .env.local)) { Copy-Item .env.example .env.local }
npm ci
npm run dev
```

`npm run dev` is explicitly configured for `http://127.0.0.1:5173`. Its
`strictPort` setting intentionally fails instead of silently selecting another
port, so the configured API CORS origin always matches. The production preview
command remains separate:

```powershell
npm run build
npm run preview
```

`npm run preview` serves `http://127.0.0.1:4173`; that origin is also allowed
by the API's default CORS configuration.

## Environment configuration

`./.env.example` documents backend-only values:

- `API_CORS_ORIGINS` includes the actual Vite development origin
  (`http://127.0.0.1:5173`) plus its `localhost` equivalent and preview origins.
- `VECTOR_DB` points to the local Chroma persistence directory used by the
  existing ingestion and property-query modules.
- `OPENAI_API_KEY` enables the existing LlamaIndex/OpenAI embedding runtime and
  the backend-only, evidence-bound AI interpretation endpoint;
  `GOOGLE_API_KEY` enables Google Maps enrichment.
- `AI_REQUEST_TIMEOUT_SECONDS` and `AI_MAX_EVIDENCE_BYTES` bound the
  deterministic-evidence and provider work for `/api/v1/agent/chat`.
- `AVM_MODEL_PATH` and `AVM_MODEL_METADATA_PATH` optionally override the
  persisted XGBoost artifacts. Valuation requests only load/predict; they do
  not train a model.
- `LOG_PATH`, `TOOL_LOG_PATH`, `LOG_PATH_MOD`, and `HASH_LOG_PATH` remain
  legacy ingestion/runtime paths. The production AI interpretation endpoint
  does not read or write them.

`ui/tupan-intel-core/.env.example` documents browser-safe Vite variables:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

Only expose browser-restricted provider credentials with a `VITE_` prefix.
Never put OpenAI, Gemini server, database, or vector-store credentials in a
frontend environment file.

## Runtime data and common setup errors

- **Port 5173 or 8000 is in use:** stop the process using that port. Vite is
  intentionally strict on 5173; do not change only the frontend port without
  also adding its exact origin to `API_CORS_ORIGINS`.
- **Browser reports a network or CORS error:** confirm the health endpoint
  responds, confirm `VITE_API_BASE_URL` ends in `/api/v1`, then restart Vite
  after editing `.env.local`. Keep the API on `127.0.0.1` to match the supplied
  frontend configuration.
- **A property, search, or market route returns 503:** check `VECTOR_DB` and
  that the existing Chroma collection named `properties` has been populated.
  The health route is deliberately dependency-free, while domain routes lazily
  initialize their own existing persistence/provider code.
- **Agent, geocoding, or semantic search is unavailable:** supply the relevant
  non-empty provider key in the root `.env`, then restart Uvicorn.
- **Valuation returns a model-artifact error:** train/publish the AVM through
  the explicit offline `python -m train.train_avm ...` workflow, then set both
  artifact paths together and restart the API worker. A normal page load never
  retrains XGBoost.
- **Python environment fails to start:** recreate the virtual environment with
  a compatible Python version and reinstall from `requirements.txt`; do not
  mix globally installed packages with the project environment.

The frontend can run by itself for layout work, and the API can run by itself
for contract/docs work. Widgets that require the other process present their
own connection error state rather than preventing the rest of the interface
from rendering.

## Cloud control plane (authentication and tenant workspace data)

The desktop now authenticates through the canonical FastAPI app with an opaque
HttpOnly session cookie. Before using sign-in, saved searches, notes, or team
management, provision Supabase PostgreSQL and apply the explicit migrations
from `ceres` with an administrative connection:

```powershell
python -m backend.migrate          # Read-only preview of pending migrations
python -m backend.migrate --apply  # Atomic application; safe to repeat
```

The runner loads `ceres/.env`, using `DATABASE_URL` or the local
`DATABASE_API_URL` fallback. It records SHA-256 checksums in the private
`tupan_internal.schema_migrations` ledger and refuses to silently adopt an
existing, untracked schema. Migration `008` requires Supabase's `auth.users`;
`009` prevents direct browser access to Tupan tables and privileged queue RPCs.
Never re-run the raw SQL files blindly. No migration runs during API startup.
Migration credentials must remain backend-only; production API/worker roles
should be separate, least-privileged roles without `BYPASSRLS`.

Optional live checks use temporary data and a temporary role, all rolled back:

```powershell
$env:TUPAN_RUN_DATABASE_TESTS = '1'
python -m unittest backend.tests.test_database_integration -q
Remove-Item Env:TUPAN_RUN_DATABASE_TESTS
```

Set the connection URL in `ceres/.env`. Supabase Session Pooler uses port 5432
and supports IPv4; require TLS (`sslmode=require`) and URL-encode the password.
API keys are not PostgreSQL passwords. Use `AUTH_COOKIE_SECURE=false` only for
local HTTP; every HTTPS deployment must set it to `true`. The frontend never
stores a session token or a demo administrator in `localStorage`.

See [DESKTOP_CLOUD_BOUNDARY.md](DESKTOP_CLOUD_BOUNDARY.md) for the canonical
ownership boundary and the legacy Chroma tenant-migration constraint.
See [SUPABASE_MIGRATION.md](SUPABASE_MIGRATION.md) for the staged Auth v2 validation and cutover gate.
## Production data migration

`backend/migrations/002_production_data_platform.sql` adds the additive
PostgreSQL source-of-truth schema for estates, portfolios, market observations,
heatmap aggregates, analysis results, notifications, jobs, conversations and
semantic embeddings. It requires a PostgreSQL deployment with both **PostGIS**
and **pgvector** installed. Apply migration `001` first.

The new tenant-scoped API is available under `/api/v1/estates`,
`/api/v1/portfolios`, and `/api/v1/jobs`. It derives organization context only
from the authenticated server session and enforces both query predicates and
PostgreSQL RLS. Composite foreign keys also reject a portfolio, analysis, notification, conversation, saved-search, or note reference from another organization. See [PERSISTENCE_MIGRATION.md](PERSISTENCE_MIGRATION.md) for
the complete inventory, classification and no-data-loss migration sequence.

## Platform intelligence preparation

Heatmaps, platform market observations and the shared AVM are not calculated by
an authenticated desktop request. A restricted `tupan_platform_intelligence`
role reads only the aggregate/training source columns directly from PostgreSQL;
it cannot read tenant estate IDs, titles, addresses, organization IDs, users or
portfolios. The separate `valuation_observations` table contains only
pseudonymous property/transaction keys needed for entity-isolated validation.
Before serving a release — and after an authorized data ingestion —
run the trusted preparation command:

```powershell
python -m backend.platform_intelligence refresh-heatmap
python -m backend.platform_intelligence train-avm --trials 100
python -m backend.platform_intelligence train-transaction-avm --n-estimators 1800
```

The heatmap command publishes only `scope = platform` cells. The compatibility
AVM command trains one shared artifact using observed `last_sale_price` labels
from all eligible sold estates; it never runs during valuation. The
`train-transaction-avm` command is the research-aligned candidate: it reads
only verified, arm's-length `sale_price_brl` observations with point-in-time
lineage, uses temporal/entity-isolated validation and split-conformal interval
calibration, and writes a separate candidate artifact. It does not overwrite
the legacy model or auto-promote. With an empty database, do not run either
command: the API returns an empty heatmap and reports the missing AVM artifact
normally.

See [AVM_ALIGNMENT.md](AVM_ALIGNMENT.md) for the data contract, validation,
uncertainty evidence, and promotion gates.

## Concurrent production analysis

Tenant-scoped request-time orchestration is available after migrations through:

- `GET /api/v1/estates/{estate_id}/comparison`
- `GET /api/v1/estates/{estate_id}/analysis`
- `GET /api/v1/portfolios/{portfolio_id}/overview`
- `GET /api/v1/market/heatmap`
- `POST /api/v1/agent/chat`

The estate and portfolio endpoints load the authorized root entity first, then
fan out only independent PostGIS/SQL/AVM work. Each response includes branch
latencies and component status, so an unavailable market or AVM dependency does
not make unrelated data disappear. Heatmaps read precomputed aggregates and are
not recalculated during an HTTP request. See [CONCURRENT_REQUESTS.md](CONCURRENT_REQUESTS.md)
for timeout, cancellation, tenant-context, AVM, and AI-boundary details.
See [AI_INTERPRETATION.md](AI_INTERPRETATION.md) for the tool and provider
boundary.

## Background worker

Run durable work in a separate backend process after applying migration `003`.
For local-only development, `WORKER_DATABASE_URL` may equal `DATABASE_URL`:

```powershell
$env:WORKER_DATABASE_URL = $env:DATABASE_URL
.\.venv-local\Scripts\python.exe -m backend.worker
```

The initial registered job is `heatmap_precompute`; it creates idempotent H3 /
PostGIS aggregates that `/api/v1/market/heatmap` can serve without recalculating
the map. Production must use a dedicated worker-only credential and never
expose it to the desktop. See [BACKGROUND_JOBS.md](BACKGROUND_JOBS.md) for
retry, freshness, cache, and tenant-isolation policy.
