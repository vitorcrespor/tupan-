# Tupan HTTP API

The API is a thin FastAPI transport layer over the existing `radar`, `predict`, and
`train` modules. It does not reimplement market heat, H3, portfolio scoring,
forecasting, or agent workflows.

For the complete two-process local setup, configuration, and troubleshooting,
see the [root local-development guide](../README.md). The actual API entry
point is `backend.api.main:app`; the older backend folders beneath `ui/` are
not used by this service.

Install the combined project and API dependencies from the `ceres` directory:

```powershell
.\.venv-local\Scripts\python.exe -m pip install -r requirements.txt
.\.venv-local\Scripts\python.exe -m uvicorn backend.api.main:app --reload --host 127.0.0.1 --port 8000 --env-file .env
```

Interactive documentation is served at `http://127.0.0.1:8000/api/v1/docs`.

Configuration:

- `API_CORS_ORIGINS`: comma-separated frontend origins. Defaults include
  `http://127.0.0.1:5173`, `http://localhost:5173`, and the preview origin on
  port 4173.
- `API_ALLOW_MOCK_DATA`: defaults to `false`; set to `true` only in development.
- `VECTOR_DB`: local Chroma persistence used by the existing property backend.
- `OPENAI_API_KEY` / `GOOGLE_API_KEY`: provider credentials required only by
  the existing provider-backed property, enrichment, and agent workflows.
- `AVM_MODEL_PATH`: optional path to the persisted XGBoost price model. Defaults
  to `train/artifacts/avm_price.json`.
- `AVM_MODEL_METADATA_PATH`: optional path to the matching feature-schema
  metadata. Defaults beside the model as `avm_price.metadata.json`.

## Price AVM lifecycle

`POST /api/v1/properties/{property_id}/valuation` is inference only. It never
fits a model or runs Optuna; the process lazily loads and caches the configured
XGBoost artifact, prepares the recorded feature schema, and calls `predict()`.

Train and publish a replacement artifact through an explicit offline command:

```powershell
python -m train.train_avm path/to/training-properties.json --trials 100
```

The JSON array must contain valid `real_estate` records and a
`preictions.suggested_price` target (the domain model retains that legacy field
spelling). Publish the model JSON and matching metadata JSON together; the API
returns a structured 503 if either is absent or incompatible. Restart API
workers after publishing a replacement so their process-level model cache loads
the new artifact pair.

## Property forecasting

`POST /api/v1/forecast` is deliberately separate from AVM valuation. It adapts
the existing XGBoost quantile time-series implementation and returns a
property's P10/P50/P90 terminal-price forecast at `time_span_days`; its P50 is
also translated into `expected_growth_pct` relative to the persisted current
price. The response separates `historical` from `forecast`: the existing model
does not expose observed input points, so `historical` is currently empty and
`forecast` contains one explicitly predicted horizon point.

There is no existing regional market-metric forecasting model or persisted
time-series model artifact in this repository. Consequently, market trend
charts remain connected only to real historical metric data, and the endpoint
returns a structured 503 when the legacy forecast model cannot run. It does
not synthesize a forecast or substitute AVM output.
