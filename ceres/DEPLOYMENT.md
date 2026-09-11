# Tupan production deployment

Tupan deploys as a modular monolith: one FastAPI API service, one Python
worker service, and PostgreSQL with PostGIS and pgvector. The desktop/client
communicates only with the API over HTTPS.

```text
Desktop client -- HTTPS --> Railway API (FastAPI)
                              |             \
                              |              -> OpenAI (optional interpretation)
                              v
                   PostgreSQL + PostGIS + pgvector
                              ^
Railway Worker ---------------+
```

Redis is not required: the durable PostgreSQL job table, transactionally
coalesced heatmap work, `SKIP LOCKED` claiming, and bounded retries already
meet the current queue requirements.

## Container image

Build from the `ceres` directory:

```powershell
docker build -f docker/Dockerfile -t tupan-api:local .
docker run --rm -p 8000:8000 --env-file .env tupan-api:local
```

The image is non-root, has `libgomp1` for XGBoost/scikit-learn, uses a pinned
Python base image and direct runtime dependency versions, emits logs to stderr,
does not copy `.env` files, and terminates Uvicorn gracefully. It deliberately
does not persist Chroma data, logs, or any other local file state.

The worker uses the same image with this command:

```text
python -m backend.worker
```

## Railway services

1. Create a PostgreSQL service that permits `postgis` and `vector` extensions.
2. Create an API service from this repository with root directory `ceres`.
   Railway reads `railway.toml`, builds `docker/Dockerfile`, and checks
   `GET /health`.
3. Create a second service from the same source/image. Override its start
   command to `python -m backend.worker`, disable the HTTP health check for that
   worker service in Railway, and do not expose it publicly. The `railway.toml`
   health check belongs only to the API service.4. Give the worker a dedicated database role when the database provider permits
   it. The role may execute the queue claim/recovery functions but every job
   handler remains tenant-scoped through RLS context.
5. Configure the API public domain and use that exact HTTPS API URL in the
   desktop production build.

Apply the migrations in order from a secure administrative environment (not
from the desktop or API startup):

```powershell
python -m backend.migrate
python -m backend.migrate --apply
```

The current complete sequence targets Supabase PostgreSQL (`008` requires
`auth.users`). The explicit runner records checksums and applies pending files
in one transaction. Existing installations without its migration ledger need
baseline review, not blind replay. `009` revokes Supabase browser-role grants
on Tupan tables and privileged worker functions. Keep the administrative
migration connection separate from non-BYPASSRLS production runtime roles.

After migration `004`, grant only the worker role access to the replaced claim
function. Never grant it to `PUBLIC` or the desktop-facing database role.

## Required Railway variables

Set these in Railway’s encrypted service-variable UI, never in Git or desktop
environment files:

| Variable | API | Worker | Notes |
| --- | --- | --- | --- |
| `TUPAN_ENV` | required | no | `production`; fails fast on insecure cookies, wildcard/implicit CORS, or mock/legacy data |
| `DATABASE_URL` | required | no | API/control-plane PostgreSQL URL |
| `WORKER_DATABASE_URL` | no | required | worker-only PostgreSQL URL |
| `OPENAI_API_KEY` | optional | no | enables evidence-bound interpretation |
| `OPENAI_MODEL` | optional | no | defaults to `gpt-4o-mini` |
| `AUTH_COOKIE_SECURE` | `true` | no | required for HTTPS |
| `AUTH_COOKIE_SAME_SITE` | `none` or `lax` | no | `none` only for a separately hosted client, and requires secure cookies |
| `AUTH_COOKIE_DOMAIN` | optional | no | set only when an intentional shared parent domain is used |
| `API_CORS_ORIGINS` | required | no | exact comma-separated desktop/web origins; never `*` |
| `API_ALLOW_LEGACY_GLOBAL_DATA` | `false` | no | must remain disabled in production |
| `API_ALLOW_MOCK_DATA` | `false` | no | must remain disabled in production |
| `API_TRUST_PROXY_HEADERS` | `true` | no | only because Railway terminates the public proxy |
| `AUTH_RATE_LIMIT_PER_MINUTE` | recommended | no | defaults to `10` per process/client address |
| `AI_RATE_LIMIT_PER_MINUTE` | recommended | no | defaults to `30` per process/client address |
| `TUPAN_API_VERSION` | recommended | no | API compatibility header, e.g. `1.0.0` |
| `TUPAN_MINIMUM_CLIENT_VERSION` | optional | no | set only after a supported-client release exists |
| `LOG_LEVEL` | `INFO` | `INFO` | JSON logs to stderr |
| `WORKER_LOG_LEVEL` | no | `INFO` | worker JSON logs to stderr |

Railway supplies `PORT`; the image binds Uvicorn to `0.0.0.0:$PORT` without
reload mode.

## Health and readiness

- `GET /health` is liveness only and is safe for Railway’s health check.
- `GET /ready` verifies a PostgreSQL query; it returns `503` when the source of
  truth is unavailable.
- Versioned equivalents exist at `/api/v1/health` and `/api/v1/ready`.

## Model artifacts

No trained AVM artifact is currently present in the repository. Therefore the
container will correctly return the existing `model_artifact_missing` response
for AVM until a versioned model artifact and its metadata are supplied to the
runtime at the configured `AVM_MODEL_PATH` and `AVM_MODEL_METADATA_PATH`.

Do not train on boot or during a request. Publish a reviewed immutable model
artifact in the release image or retrieve it from a controlled object store in
an explicit release/bootstrap step. The main container filesystem is ephemeral.

## Rollout order

1. Provision extension-capable PostgreSQL and apply migrations.
2. Deploy API with `/health`; verify `/ready` after database variables are set.
3. Deploy the worker; confirm a heatmap job is claimed and has structured logs.
4. Build the desktop with the API URL and perform the production smoke suite in
   `PRODUCTION_READINESS.md`.
5. Enable `TUPAN_MINIMUM_CLIENT_VERSION` only after the matching desktop build
   has been distributed.
