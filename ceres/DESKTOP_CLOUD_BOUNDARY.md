# Tupan Desktop / Cloud Boundary

## Canonical runtime

```
Tupan Desktop (React/Vite)
  UI, maps, charts, navigation, interaction state, status/progress presentation
       │ HTTPS + JSON + HttpOnly session cookie
       ▼
Tupan Cloud API (FastAPI /api/v1)
  transport, authentication, tenant authorization, orchestration
       ▼
Application services
  property, market, portfolio, forecast, agent, control plane
       ▼
PostgreSQL / PostGIS / pgvector · model artifacts · provider APIs
       │
       └── durable worker process for imports, heatmaps, notifications and reports
```

`backend.api.main:app` is the only canonical HTTP entry point. The historical
`ui/tupan-intel-core/backend` (Node) and `ui/tupan-intel-core/backend-fastapi`
applications are not deployment targets and must not receive new work.

## Desktop responsibilities

The desktop may contain only:

- React UI, chart and map rendering, navigation, accessibility and local view state;
- non-sensitive preferences such as theme and panel state;
- an HTTP API client, request cancellation/timeouts and progress/error presentation;
- optional browser-restricted map credentials (`VITE_GOOGLE_MAPS_API_KEY`).

The desktop must never contain or decide:

- OpenAI/Gemini keys, PostgreSQL credentials, JWT/signing material, Supabase service credentials, model artifact paths, or vector-store credentials;
- authorization or organization ownership decisions;
- server-side AVM, comparison, market, portfolio, H3, forecast, notification, or LLM tool logic;
- durable job execution or data ingestion that depends on the desktop remaining open.

## Identity and workspace data

The canonical API now owns `/api/v1/auth` and `/api/v1/workspace`.

- Password hashes use server-side `scrypt` with a unique random salt.
- Login issues an opaque random session whose SHA-256 digest is stored in PostgreSQL.
- The browser receives the session only as `HttpOnly`, `SameSite=Lax` cookie scoped to `/api/v1`; JavaScript cannot read or set a token.
- Every workspace query derives `user_id` and `organization_id` from that server session. The client never submits either authorization field.
- PostgreSQL migration: `backend/migrations/001_cloud_control_plane.sql`.

Set `AUTH_COOKIE_SECURE=true` for every HTTPS environment. It is `false` only
for local `http://127.0.0.1` development.

## Canonical contracts added

| Area | Routes | Ownership |
| --- | --- | --- |
| Session | `POST /auth/register`, `POST /auth/login`, `GET /auth/session`, `POST /auth/logout` | Cloud control plane |
| Team | `GET/PATCH/DELETE /workspace/members` | organization-scoped backend authorization |
| Saved searches | `GET/POST/DELETE /workspace/saved-searches` | user + organization-scoped PostgreSQL |
| Notes | `GET/POST /workspace/properties/{id}/notes` | organization-scoped PostgreSQL |
| Boundaries | `GET /workspace/district-boundaries` | organization-scoped PostgreSQL |

All routes live under `/api/v1` in production. The FastAPI process is the only
process allowed to access the database and model/provider credentials.

## Deliberate migration boundary

The legacy Chroma property collection has **no organization identifier**. It is
therefore not safe to represent it as tenant-isolated cloud data. Existing
property/market/portfolio/AVM endpoints remain adapters over the existing domain
code while their records are migrated into canonical PostgreSQL/PostGIS tables.
Do not auto-assign all historical Chroma records to the first organization.

Until that migration lands:

1. tenant-scoped control-plane data is already production-safe;
2. legacy property analytics must remain explicitly marked as transitional;
3. production authorization must not claim the global Chroma collection is
   organization-isolated;
4. the desktop must not revive a local-data fallback when a cloud route fails.

## Background execution boundary

The desktop never owns durable work. FastAPI submits work with an organization
id, actor id, input version and idempotency key; a separately started worker
persists state in PostgreSQL and updates a job record. Suitable jobs are workbook
imports, H3 heat aggregation, bulk geocoding, notification evaluation, report
generation, model training, and large embedding runs. Quick read-only AVM
inference and user-requested agent explanations remain request-time services.

## Deployment rules

- Deploy FastAPI behind HTTPS and set `AUTH_COOKIE_SECURE=true`.
- Grant the API/worker database user only application permissions; keep migration
  privileges in a separate deployment role.
- Keep all secrets in server-side environment/secret management, never in any
  `VITE_*` variable.
- Start workers independently from the desktop. A closed desktop must never
  cancel an import, notification evaluation, or model training run.