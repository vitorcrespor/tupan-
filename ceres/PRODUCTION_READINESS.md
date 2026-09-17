# Tupan production-readiness checklist

Status reflects the current repository, not an unperformed Railway deployment.

## Implemented controls

- Canonical FastAPI app and PostgreSQL worker have separate process entrypoints.
- API liveness (`/health`) is dependency-free; readiness (`/ready`) performs a
  PostgreSQL query.
- PostgreSQL/PostGIS/pgvector migrations, RLS context, explicit tenant query
  predicates, and tenant-scoped job handler context are present.
- Analysis fan-out has bounded timeouts and records branch status/latency.
- AVM inference stays off the event loop and never trains during an HTTP call.
- The AI service only receives bounded verified evidence and returns validated
  structured output with authorized evidence references.
- The worker uses PostgreSQL idempotency keys, `SKIP LOCKED`, bounded retries,
  stale-job recovery, and structured job/queue timing events.
- API and worker logs are JSON stdout/stderr events with request/job IDs,
  operation, latency, and status. They omit bodies, cookies, provider prompts,
  SQL, and database credentials.
- Sensitive login/register and AI routes have a bounded process-local rate
  limit. A Railway edge/WAF rate limit is still required before multi-replica
  scale-out.

## Security audit

| Area | Current assessment | Required release action |
| --- | --- | --- |
| Authentication | Opaque HttpOnly, server-hashed sessions | Set secure cookie variables and test real HTTPS login/logout. |
| Authorization | Server-derived tenant context and role checks | Keep legacy global routes disabled; execute cross-tenant suite on PostgreSQL. |
| Tenant isolation | RLS context plus organization predicates | Apply migrations and verify database roles do not have `BYPASSRLS`. |
| SQL injection | Repository SQL uses asyncpg placeholders; dynamic update columns are whitelisted | Keep new queries parameterized; prohibit user-provided SQL/identifiers. |
| Input validation | FastAPI/Pydantic bounds request and AI tool inputs | Add coverage whenever a new external route/tool is added. |
| AI boundaries | Tool inputs/limits, authorized evidence, prompt boundary, structured output validation | Keep provider keys backend-only; do not add arbitrary tool execution. |
| Sensitive logging | Structured events intentionally omit payloads/secrets | Configure log retention/access in Railway; review application exceptions before adding logs. |
| Timeouts | Analysis and AI have bounded request/branch deadlines | Set production values based on measured traffic; alert on 504/503 rates. |
| Rate limiting | Local sensitive-route limiter exists | Configure Railway/edge limits before horizontal scaling; do not treat process memory as global protection. |
| Dependencies | Direct Python runtime versions are pinned; no transitive hash lock exists yet | Generate and commit a hash-locked Linux dependency lock, run `pip-audit` in that clean environment, and remediate findings before sign-off. |

## Validation performed in this workspace

- `python -m unittest discover -s backend/tests -p "test*.py"` passed:
  **110 tests**, with 3 environment/integration-dependent skips.
- `GET /health` returned `200 {"status":"ok"}` and `/ready` correctly
  returned `503` without a configured database. Both emitted structured request
  logs with request IDs.
- Frontend `npm run typecheck`, `npm run lint`, and `npm run build` passed.
  PDF dependencies are loaded on demand and the production build no longer
  reports chunks above 500 kB.
- Frontend `npm run test:ui` passed **13 tests**, with 1 intentionally skipped
  demo-data snapshot that requires an external fixture.
- `npm audit --omit=dev` reports **2 moderate** React Router 6 advisories.
  The client-only application does not use Router SSR hydration, routes are
  application-owned, and a direct Router 7 upgrade regressed tested browser
  interactions. Keep this as a tracked dependency migration rather than
  accepting an unvalidated major upgrade.
- A local Docker image build could not be completed because the local Docker
  Desktop Linux daemon was unavailable. Build and smoke-test the image in
  Railway staging or Linux CI before production promotion.
- `pip-audit` is not installed in this workspace, and the host interpreter has
  unrelated OpenTelemetry package conflicts. Run Python vulnerability scanning
  inside a fresh container/virtual environment created from the final lock.
## Required test matrix

Run these against an isolated production-like PostgreSQL database, then a
Railway staging environment. Existing unit coverage does not substitute for
these integration/failure tests.

| Scenario | Expected result |
| --- | --- |
| Login/session/logout | HttpOnly cookie is issued, honored, and revoked; no token appears in local storage. |
| Estate comparison/analysis | Authorized data returns component timing; one degraded branch does not erase others. |
| AVM | Published artifact predicts; absent/incompatible artifact returns a controlled error without retraining. |
| Portfolio overview/heatmap | Tenant data only; heatmap reads precomputed cells and does not recompute synchronously. |
| AI | Outage returns controlled 503; prompt injection does not create unauthorized tool access or numeric calculations. |
| Concurrent users | Independent tenants retain RLS isolation under simultaneous estate/portfolio calls. |
| Cross-tenant identifiers | Every estate, portfolio, job, note, and trace returns 404/denial, never another tenant’s data. |
| Worker restart/failure | RUNNING jobs are recovered with bounded attempts; idempotency prevents duplicate aggregate rows. |
| Database outage | `/ready` becomes 503; `/health` stays 200; API errors remain structured. |
| API restart | Uvicorn receives SIGTERM, stops accepting work, and releases connections cleanly. |
| Queue retry | Retryable failure returns to PENDING with backoff; permanent failure ends FAILED. |
| Notifications | Not yet implemented as a production flow; add an idempotency-key test before enabling delivery. |
| Network interruption | Client surfaces `NETWORK_ERROR`, `API_TIMEOUT`, cancellation, and server errors per widget. |

## Production blockers still requiring external state

1. Provision a PostGIS + pgvector capable Railway PostgreSQL service, preview
   the migration plan, and apply every pending migration in checksum order.
2. Configure production secrets and exact CORS/cookie origins in Railway.
3. Review and explicitly promote an immutable AVM artifact plus metadata. The
   tracked transaction artifact is candidate-only and is intentionally not
   used by request-time inference.
4. Keep the passing frontend typecheck/build gates in release CI. The remaining
   two moderate `react-router` 6 advisories are recorded exceptions: this is a
   client-only SPA (the SSR hydration advisory is not reachable), and navigation
   targets are application-owned routes. A Router 7 upgrade was tested and
   reverted after browser interaction regressions; migrate it as a dedicated,
   fully validated change rather than forcing it into a security patch.
5. Generate a hash-locked Python dependency set, scan it in a clean Linux
   environment, and build/smoke-test the Docker image in staging.
6. Execute the staging matrix above, including real OpenAI and PostgreSQL outage
   tests, then record latency/error SLOs.
7. Add an edge/WAF rate limit and dependency-vulnerability checks to release CI.
8. Implement notification delivery and its idempotency tests before claiming
   notification production readiness.

## Architecture decision

There is no demonstrated reason to introduce Kafka, Kubernetes, or
microservices. The current modular monolith—with FastAPI request orchestration,
PostgreSQL/PostGIS/pgvector, and a dedicated PostgreSQL-backed worker—is the
smallest understandable architecture that fits current workloads. Revisit that
decision only with measured queue backlog, multi-region, or independent-team
deployment requirements.
