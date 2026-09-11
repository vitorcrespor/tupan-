# Tupan desktop/client production build

The current desktop client is a Vite/React application. No Electron, Tauri, or
other native-shell configuration is present in this repository, so this guide
packages the existing client build without introducing a replacement framework.

If a native shell is selected later, it should load this same built client with
context isolation enabled and must not add backend secrets, Node integration,
or direct database access. That shell is a separate packaging decision, not a
backend deployment prerequisite.

## Build configuration

Create a production-only `.env.local` in `ui/tupan-intel-core`:

```dotenv
VITE_TUPAN_API_URL=https://YOUR-RAILWAY-API-DOMAIN/api/v1
VITE_TUPAN_CLIENT_VERSION=1.0.0
```

`VITE_*` values are embedded in the build and are public by definition. Never
place any of the following in this file, a bundled asset, or a desktop binary:

- `OPENAI_API_KEY` or any provider server key;
- `DATABASE_URL`, `WORKER_DATABASE_URL`, Supabase service credentials, or JWT
  signing secrets;
- AVM artifact storage credentials;
- any unrestricted tenant or administrator token.

Build and verify:

```powershell
Set-Location 'C:\Users\Usuario\OneDrive\Área de Trabalho\tupan\ceres\ui\tupan-intel-core'
npm ci
npm run typecheck
npm run lint
npm run build
```

The generated `dist/` directory is a deployable client artifact. It continues
to use the centralized `src/api/client.js` layer: network errors, timeout
errors, JSON API errors, and HTTP errors are represented by `ApiError`; React
components do not use raw `fetch` calls.

## Authentication and secure storage

The client does not keep a bearer token in JavaScript storage. The API issues
an HttpOnly session cookie with `credentials: 'include'`, so the browser/native
webview owns secure cookie storage. Local storage is limited to non-sensitive
preferences such as theme and voice settings.

For a client and API hosted on different sites, configure the API with:

```dotenv
AUTH_COOKIE_SECURE=true
AUTH_COOKIE_SAME_SITE=none
API_CORS_ORIGINS=https://THE-CLIENT-ORIGIN
```

`SameSite=None` requires HTTPS. Use `lax` only where the client and API share a
same-site deployment compatible with it. A future native wrapper must verify
its webview cookie policy before release; `file://` pages and arbitrary custom
schemes are not assumed to work with remote secure cookies.

## Client/API compatibility

Every request sends `X-Tupan-Client-Version`. The API returns
`X-Tupan-API-Version` and may return `426 client_upgrade_required` when
`TUPAN_MINIMUM_CLIENT_VERSION` has advanced. Keep the initial production API
minimum empty until version `1.0.0` is distributed.

## Release checks

1. Confirm built assets contain the intended HTTPS API URL only.
2. Search the build and environment files for banned secret names.
3. Require `npm run typecheck`, `npm run lint`, `npm run build`, and
   `npm audit --omit=dev --audit-level=high` to pass or have formally approved
   remediation records. The current repository does not yet meet this gate.
4. Verify login/session/logout against production using an allowed origin.
5. Disconnect the network during a query and confirm the existing per-widget
   error states remain usable.
6. Verify `426`, `401`, `403`, `422`, `429`, `503`, and `504` surface as useful
   client API errors without clearing unrelated page state.