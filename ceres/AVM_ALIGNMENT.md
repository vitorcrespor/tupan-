# Ceres AVM alignment

This document records the production boundary for the research-aligned AVM
described in `CERES_AVM_State_of_the_Art_2026(1).md`.

## Current status

The existing `train/avm.py` artifact remains the serving-compatible legacy
path. It is not silently replaced because its historical target is an asking /
estimate field. The new path is an isolated candidate trainer:

```powershell
python -m backend.platform_intelligence train-transaction-avm --n-estimators 1800
```

It writes `train/artifacts/avm_transaction_v2.json` and matching metadata only
after a valid dataset is available. With no eligible observations it returns a
`not_ready` scorecard and does not create an artifact.

### First local ITBI candidate

The first offline candidate was trained from the curated
`data/ITBI_Campinas_2021_2026_LIMPO (1).xlsx` workbook with:

```powershell
cd ceres
python -m train.train_itbi_transaction_avm --enrich-google --n-estimators 600
```

The trainer retained 59,017 residential, onerous, non-outlier observations
with positive constructed area and transaction value (including the source's
partial 2026 period). The optional Google
enrichment geocodes each normalized Campinas neighborhood once and derives
latitude/longitude plus H3 cells for the neighborhood centroid. The workbook
does not contain property addresses or exact coordinates, so this is a
neighborhood-level location feature; Google Places/neighbour-distance
features were not fabricated or applied.

The resulting pair is still a `candidate` artifact (35,410 train / 11,803
calibration / 11,804 out-of-time test rows). Its out-of-time scorecard is
MAE R$204,596, MdAPE 33.41%, and conformal coverage 79.45% at the 80% target
level (median interval width 156.21%). These values are evidence for review,
not a promotion decision. The cache at
`data/enrichment/itbi_campinas_google_geocodes.json` contains only provider
responses and no API key.

## Training contract

`backend/migrations/010_valuation_observations.sql` is the global, trusted
observation table. A row is eligible only when all of the following hold:

- `verified = true` and `training_allowed = true`;
- the target is an explicit `sale_price_brl`;
- `transaction_nature = arm_length`;
- `valuation_time`, `available_at`, and `feature_as_of` are timezone-aware;
- every supplied feature has `source_id`, `source_version`, and
  `available_at` lineage that is not newer than the valuation event;
- the observation has a stable pseudonymous property/transaction key for
  entity and listing-cluster isolation.

Asking prices, `suggested_price`, `estimated_price`, `last_sale_price`, price
per square metre, leverage, luxury/leisure scores, raw addresses, tenant IDs,
and other target-derived fields are not accepted as model features or labels.
Coordinates are retained as numeric features; H3 cells are deterministic
derived features. An address may be used by an upstream entity-resolution
process, never as a learned categorical feature.

## Candidate model and validation

The candidate uses a global XGBoost regressor on `log(sale_price_brl)` with
explicit numeric/categorical schema, missing numeric values represented as
`NaN`, and category vocabularies learned from the training window only.

The split is chronological and keeps a property/listing cluster together:

1. training window;
2. calibration window;
3. untouched out-of-time test window.

The module also provides expanding rolling folds and H3 spatial holdouts for
promotion review. The scorecard reports MAE, MdAPE, P90 APE, within 5/10/20%,
median ratio, COD, and PRD. No random train/test split is used by this path.

## Uncertainty and confidence inputs

The candidate fits a split-conformal expansion on the calibration window and
stores interval coverage and median width for the untouched test window. This
is an evidence interval, not a probability of correctness.
`train/valuation_uncertainty.py` also exposes:

- completeness and source-freshness quality evidence;
- thin/contradictory comparable support detection;
- conservative local residual correction using out-of-fold comparable
  residuals only.

The product confidence policy must combine interval width/coverage, data
quality, comparable support, out-of-distribution checks, freshness, and model
agreement. It must abstain or show degraded confidence when critical evidence
is missing; it must not turn a single AVM score into a fabricated probability.

## Promotion gate

Promotion is intentionally manual and requires a reviewed scorecard with:

- untouched temporal test results;
- spatial-block results;
- interval coverage and width at the chosen level;
- data-quality exclusion counts;
- no property/listing-cluster leakage;
- comparison with the legacy artifact and a simple baseline;
- reproducible source/version metadata and model checksum.

Until those gates pass, `promotion_status` remains `candidate` and serving
continues to use the existing artifact. This is deliberate: a new AVM should
not become authoritative merely because it can fit a table.

## Serving integration

`backend.services.avm_runtime.AvmRuntime` checks the transaction artifact pair
before invoking the legacy model. A candidate artifact is ignored. When the
metadata has an explicit `promotion_status` of `production` or `promoted`, the
runtime maps the authorized estate projection to the versioned transaction
feature contract and returns the point estimate plus the split-conformal
`lower_bound`, `upper_bound`, interval level, calibration sample count and
out-of-time coverage. The analysis API and `PropertyDetail` present that range
only when `uncertainty_status=calibrated`.

This output is an evidence interval, not a calibrated probability that the
estimate is correct. With no promoted transaction artifact, the legacy AVM
continues to serve its point estimate and reports `not_calibrated`; no bounds
or confidence percentage are fabricated.

The promoted model and metadata are cached per API worker. Publish the pair
atomically and restart API workers to load a replacement model version.
