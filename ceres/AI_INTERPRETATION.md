# Tupan AI interpretation boundary

`POST /api/v1/agent/chat` is an interpretation endpoint, not a calculator,
database proxy, or autonomous agent runtime.

```text
Desktop selection + question
        |
        v
FastAPI session authentication
        |
        v
TenantContext (server-derived)
        |
        v
AiOrchestrator
        |
        +-- estate analysis (one shared AVM/comparables/market/location fan-out)
        +-- portfolio overview (when selected)
        +-- precomputed heatmap read (when selected)
        |
        v
bounded, JSON-safe verified evidence
        |
        v
OpenAI interpretation client
        |
        v
validated structured explanation
```

The AI package is under `backend/services/ai/`:

- `client.py` owns the backend-only OpenAI call.
- `orchestrator.py` plans independent deterministic work and joins its output.
- `tools/analysis_tools.py` contains the only available tools, with input and
  result limits.
- `prompts/` defines the evidence-bound provider prompt.
- `schemas.py` validates provider output before it can leave FastAPI.

## Controls

- Tenant identity comes solely from the authenticated session. The desktop may
  provide an estate or portfolio identifier but never an organization ID.
- Tools call existing tenant-scoped application orchestration only. They do not
  receive a connection, SQL interface, filesystem handle, secret, or an
  authorization decision.
- Estate tool views share one request-local analysis task, so AVM, comparable,
  market, and location branches run once and are reused.
- Portfolio and heatmap work fan out with estate work only when independently
  requested. Heatmaps remain a fast read of precomputed aggregates.
- Provider requests use a bounded deadline, bounded evidence payload, and a
  zero-temperature JSON response. The backend validates the response schema
  and requires every evidence-backed answer and insight to cite an authorized
  evidence key.
- Missing or degraded deterministic branches are represented as warnings; no
  raw exception, database result, credential, or trace prompt is sent to the
  desktop. Diagnostic traces are process-local, tenant-scoped metadata only.

`OPENAI_API_KEY` and `OPENAI_MODEL` are root backend environment values. They
must never be copied into `ui/tupan-intel-core/.env*` or sent by the desktop.
