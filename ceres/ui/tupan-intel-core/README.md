# Tupan Intel Core frontend

This React/Vite dashboard uses the integrated FastAPI service at
`backend.api.main:app`. It has no Base44 runtime or SDK dependency.

## Run locally

Start the FastAPI service first by following the [root local-development
guide](../../README.md). Then, from this directory:

```powershell
if (-not (Test-Path .env.local)) { Copy-Item .env.example .env.local }
npm ci
npm run dev
```

The Vite development server is explicitly configured at
`http://127.0.0.1:5173`. It uses `VITE_API_BASE_URL` from `.env.local`; the
provided value is `http://127.0.0.1:8000/api/v1`. Restart Vite after changing
that variable.

## Browser-safe environment variables

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
# VITE_GOOGLE_MAPS_API_KEY=
# VITE_GOOGLE_MAPS_MAP_ID=
# VITE_ENABLE_CHART_EXPANSION=true
```

Do not add server secrets such as `OPENAI_API_KEY`, `GOOGLE_API_KEY`, vector
store paths, or AVM artifact paths to this file. Frontend API modules make the
HTTP requests; React components do not hardcode backend URLs.

Without a Google Maps browser key, map components retain their local fallback
state. A missing/unavailable backend is reported by the individual data region
that requested it, so the rest of the dashboard remains usable.

## Production build

```powershell
npm run typecheck
npm run lint
npm run test:ui
npm run build
npm run preview
```

`test:ui` uses the installed Playwright package and the system browser selected
by `PLAYWRIGHT_CHANNEL` when set (for example, `msedge` on Windows). The demo
snapshot test is skipped unless `DEMO_SNAPSHOT_PATH` points to an explicit test
fixture; it never reads production data implicitly.

The preview server is `http://127.0.0.1:4173`. Deploy the generated `dist/`
directory to a static host with SPA routing enabled, and configure its origin
in the deployed API's `API_CORS_ORIGINS`.
