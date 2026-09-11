# Concurrent request-time analysis

`backend.services.analysis_orchestrator.AnalysisOrchestrator` is the only
request-time fan-out/fan-in coordinator. It does not contain pricing, spatial,
portfolio, or AI formulas; those remain in PostgreSQL/PostGIS queries and the
existing persisted AVM implementation.

## Execution policy

| Capability | Required sequential work | Concurrent branches | Join / partial-failure policy |
| --- | --- | --- | --- |
| Heatmap | Authenticate and query precomputed `heatmap_aggregates` | None | One fast PostGIS/JSONB read. Aggregation belongs to a background job, never this request. |
| Estate comparison | Authenticate, resolve tenant, load estate | PostGIS comparables; SQL local statistics; market observations; precomputed H3/location metrics | Each branch may degrade independently. The authorized estate is still returned with component status and timings. |
| Estate analysis | Same authorized estate read | Existing persisted AVM (thread-isolated); comparables; local statistics; market context; location metrics | AVM absence/incompatible features appears as degraded valuation, while deterministic peer/context results stay available. |
| Portfolio overview | Authenticate, resolve tenant, load portfolio | Valuation summary; geographic concentration; pricing statistics; property distribution; market exposure | Every branch is a tenant-filtered aggregate. A failed widget does not remove the portfolio response. |

The response `timing` field has total request latency and status/duration for
every branch. `success` means a result was returned, `degraded` records a
bounded timeout/dependency failure, and `skipped` is reserved for a deliberately
disabled optional feature.

## Timeouts and cancellation

- `ANALYSIS_REQUEST_TIMEOUT_SECONDS` defaults to `12` seconds and bounds the
  whole analysis request.
- `ANALYSIS_BRANCH_TIMEOUT_SECONDS` defaults to `5` seconds for database and
  network branches.
- `ANALYSIS_AVM_TIMEOUT_SECONDS` defaults to `3` seconds for one model
  inference.
- A whole-request timeout returns `504 request_timeout`.
- A branch timeout returns a `degraded` component inside an otherwise usable
  response.
- Client/request cancellation cancels every pending coroutine branch. XGBoost
  is run through `asyncio.to_thread`; a native prediction already executing in
  that worker cannot be forcibly stopped, but the API coroutine is cancelled
  and the worker result is discarded.

## AVM decision

`train.avm.predict_price` uses a process-cached trained artifact and runs only
feature preparation plus `model.predict()`. It never calls training/Optuna.
The repository currently has no default artifact at
`train/artifacts/avm_price.json` or matching metadata, so an honest production
benchmark cannot yet be run. Until that artifact is published, inference is
kept request-time but isolated in a thread to protect the asyncio event loop;
it is **not** made a worker job solely because it is model code.

When a real artifact and representative authorized estate are available, use
the returned `valuation.inference_ms` and `timing` values under load to compare
the existing serial route with the fan-out endpoint. If inference consumes a
material proportion of the request deadline or causes worker-pool saturation,
move only bulk/revaluation workloads to durable jobs. Single-estate interactive
analysis should remain request-time when it meets the observed latency budget.

## Tenant and AI boundaries

Every branch receives the immutable `TenantContext` created from the opaque
server session. Each repository transaction sets PostgreSQL
`app.organization_id` and includes an organization predicate, with RLS as the
second barrier. Branches have no shared tenant-mutating state.

The existing agent is deliberately not called as an optional explanation yet:
it still uses global legacy tools and cannot prove that its retrieval inputs are
tenant-authorized. Add an AI summary only after it accepts the structured,
already-authorized analysis result from this orchestrator. It must never query
an estate/portfolio by a client-supplied organization id.
