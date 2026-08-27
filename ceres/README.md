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
  geocoding, and agent routes. The health endpoint itself does not require
  provider credentials or loaded data.

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
- `OPENAI_API_KEY` enables the existing LlamaIndex/OpenAI embedding runtime;
  `GOOGLE_API_KEY` enables the existing Gemini agent and Google Maps enrichment.
- `AVM_MODEL_PATH` and `AVM_MODEL_METADATA_PATH` optionally override the
  persisted XGBoost artifacts. Valuation requests only load/predict; they do
  not train a model.
- `LOG_PATH`, `TOOL_LOG_PATH`, `LOG_PATH_MOD`, `AGENT_TRACE_PATH`, and
  `HASH_LOG_PATH` are writable locations used by the existing agent/ingestion
  code.

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
