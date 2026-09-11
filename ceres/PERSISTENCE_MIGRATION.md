# Production Persistence Inventory and Migration Rules

## Current persistence mechanisms

| Current mechanism | Locations | Classification | Production disposition |
| --- | --- | --- | --- |
| Chroma persistent collection | `radar/config.py`, `backend/services/property.py`, `VECTOR_DB` | VECTOR DATA **and** legacy property DATABASE DATA | Read-only migration source. Replace structured property records with PostgreSQL estates; move embeddings only to pgvector after parity checks. |
| Excel / CSV workbooks | `data/*.xlsx`, `radar/menu/menu.py`, `mock_db/sql_transport.py` | IMPORT/EXPORT FILE | Input/export only. Import through durable jobs and persist validated rows to PostgreSQL. |
| JSONL agent, tool and trace logs | `logs/*.jsonl` via root `.env` | CACHE / operational log | Keep only for diagnostics during transition; durable conversations and results go to PostgreSQL. |
| JSON parameter / hash files | `logs/*parameters.json`, `logs/ingestion-hashes.json` | CACHE / operational metadata | Replace with job/result records where shared or audit-relevant. |
| Chroma documents and metadata | property document payloads | VECTOR DATA + serialized legacy objects | Migration source only; never add new production structured state here. |
| Browser `localStorage` | theme and voice persona frontend preferences | CLIENT STATE | Retain only non-sensitive local preferences. Auth/business data has been removed. |
| FastAPI `lru_cache` | dependencies and AVM artifact loader | CACHE | Process-local optimization, never source of truth or tenant context. |
| AVM XGBoost JSON + metadata | `train/artifacts/*.json`, configured model paths | MODEL ARTIFACT | Keep as immutable/versioned deployment artifact; store artifact/version references in analysis results, not model bytes in PostgreSQL. |
| Uploaded workbooks | property import endpoint / Data Management | IMPORT/EXPORT FILE | Temporary object/file storage only; processing is a tenant-scoped job. |
| Retired Node/FastAPI PostgreSQL scaffolds | `ui/tupan-intel-core/backend*` | DATABASE DATA (retired) | Do not deploy; migrate data only through controlled scripts. |
| SQLite | repository scan | none found | Do not introduce it for shared production data. |

## Target ownership

- **PostgreSQL**: authoritative structured data, tenant metadata, jobs, conversations, analysis, notifications and auditable references.
- **PostGIS**: estate locations, market/heat geometries and spatial indexes/queries.
- **pgvector**: embeddings in `semantic_embeddings` only. Never store price, rooms, coordinates or other filterable domain fields in embeddings.
- **Model artifact store**: immutable XGBoost/GBoost model files and metadata, referenced by version.
- **Client**: only non-sensitive preference state and visual/request state.

## Migration sequence

1. Apply `001_cloud_control_plane.sql`, then `002_production_data_platform.sql` and `003_background_jobs.sql`, then `004_observability.sql`, to a Postgres instance that has PostGIS and pgvector installed.
2. Deploy FastAPI/worker using an application role without `BYPASSRLS`.
3. Backfill organizations only through an explicit ownership mapping; do not auto-assign legacy Chroma records.
4. Backfill `estates`, validate count/checksum/geographic coordinate parity, then shadow-read from PostgreSQL.
5. Recompute or import `market_observations` and `heatmap_aggregates` as versioned data; verify result parity.
6. Backfill embeddings into pgvector from authorized tenant records only.
7. Switch reads/writes by feature flag after parity checks and rollback observability exist.
8. Retire Chroma/legacy JSONL only after verified read and operational parity.
## Tenant and worker invariants

- The FastAPI principal creates `TenantContext` from its opaque server session;
  no API request schema accepts `organization_id` as authority.
- `TenantDataRepository` sets `app.organization_id` with `set_config(..., true)`
  inside each database transaction. RLS and explicit predicates both apply.
- An estate may be moved only after the target portfolio is found in the same
  tenant transaction. A guessed portfolio ID therefore resolves as not found.
- `jobs` records the submitting organization and user. A durable worker must
  load a job from its trusted scheduler/queue, then start a fresh tenant-scoped
  transaction from that stored context. It never inherits request globals or
  desktop process state.
- Agent/LLM services must retrieve their input through tenant repositories;
  they receive already-authorized records and no client-selected tenant scope.