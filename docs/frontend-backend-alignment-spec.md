# CERES: remaining information-alignment specification

Original audit date: 2026-09-14. The initial section was specification-only;
the implementation update immediately below records the subsequently approved
provider work.

> **Active-consumer reconciliation — 2026-09-16.** The remaining actionable
> wiring has now been closed without filling unsupported metrics:
>
> - Overview forwards the shared top-bar liquidity horizon to
>   `/market/published-metrics` and presents the persisted liquidity series in
>   its metric tray. The query/cache key already includes that horizon, so a
>   selector change cannot reuse a curve from another horizon.
> - Estate catalog rows receive `market_heat` through one tenant-bounded SQL
>   page read joined to the latest global H3 publication. Property analysis and
>   pair comparison reuse the same published aggregate normalizer. React only
>   formats the nullable `0–100` value; it never calculates heat.
> - PropertyDetail now presents the H3 heat beside inventory and publication
>   provenance. Properties, ListingCard and Compare consume the same typed
>   estate field. Missing/invalid-unit publications remain `null`.
> - F08 is connected with an intentional split in lineage: fresh estate
>   analysis classifies only a calibrated promoted AVM interval; catalog stored
>   estimates without persisted calibrated bounds return
>   `INSUFFICIENT_CONFIDENCE`. The local transaction XGBoost artifact is still
>   `candidate`, so it is not promoted merely to populate the UI.
>
> After this pass, the unresolved items in this document are provider/data
> prerequisites rather than missing active UI/API links: F04 has no validated
> temporal forecast artifact; B13/F05/F06/F13/F14 acquire history only from
> future factual publications/snapshots; the promoted AVM range awaits model
> review. Per product direction, 4L and notifications are deferred and are not
> alignment blockers for this cycle.

> **Implementation update — global market heat, 2026-09-14.** The original
> audit below remains the evidence record. Since it was written, its F01/M03/M32
> gap has been addressed with a serving-safe publication provider:
>
> - `backend.services.market_heat.calculate_market_heat` computes a
>   resolution-specific, aggregate-only market-heat score from global active
>   listing inventory and global dated sales. It keeps the legacy
>   spatial-intensity × observed-momentum idea, but has no portfolio input,
>   estate identifier or mutable request state.
> - A cell receives `market_heat` only with at least three recent and three
>   reference-window sales in that same cell. Insufficient evidence remains
>   `null` and is labelled `insufficient_observed_sale_support`; it is never
>   converted into zero or a forecast.
> - `PlatformIntelligenceService.refresh_heatmaps` reads global sources once
>   and publishes each requested H3 level independently. The CLI accepts
>   repeated `--h3-resolution` flags, supports 0–15, and replacement is scoped
>   by `(scope, h3_resolution, input_version)`, preserving other levels and
>   unrelated platform publications.
> - The existing `/market/heatmap` contract already carries normalized
>   `market_heat`, `price_growth` and `sales_velocity`; `MarketMap`,
>   `RegionPanel`, `MarketIntelligence` and portfolio exposure now consume
>   these fields without React-side metric arithmetic. The map and intelligence
>   controls share a user-selectable grid preference (7–10 are the practical
>   interactive choices). An unpublished resolution correctly renders the
>   existing empty state.
>
> This is not a claim that a real snapshot has been published or that demand,
> forecasts, historical heat series, or notification providers now
> exist. Publication remains an explicit offline operation until a periodic
> job is configured and verified against the production data population.

> **Implementation update — listing liquidity survival contract, 2026-09-15.**
> `liquidity_score` is no longer an alias for demand or inverse DOM. Migration
> `011_liquidity_survival.sql` creates an aggregate-only, global
> Kaplan–Meier artifact trained offline from eligible active (right-censored)
> and sold (event) listings. For an active estate at listing age `a` and the
> horizon `T` selected in the shared top bar, the API computes
> `100 × [1 − S(a + T | X, M) / S(a | X, M)]`. The selector maps `30d`,
> `60d`, `90d`, `6m`, and `12m` to explicit days; `custom` returns an
> unscored state until a numeric custom horizon exists. Publication remains
> pending until migration `011` is applied and
> `python -m backend.platform_intelligence publish-liquidity-model` has enough
> eligible observed support. No H3 regional liquidity aggregate is claimed.

> **Implementation update — portfolio-owned liquidity, 2026-09-15.** The
> portfolio overview now evaluates liquidity from that portfolio's own active
> listings (right-censored) and sold listings (events), never from a similar
> property set or the cross-tenant global artifact. The existing header
> horizon is forwarded to `/portfolios/{id}/overview`; the response reports
> support, event count and a typed unavailable state when the portfolio's own
> history is insufficient. It never substitutes market-wide sales to fill a
> small portfolio.

> **Implementation update — published-market snapshot adapter, 2026-09-15.**
> `AnalysisOrchestrator.published_market_metrics` now first returns dated
> `market_observations` when they exist. Only when that provider has no rows,
> it projects the already-published, global H3 aggregate snapshot through
> `market_snapshot_observations` into the same typed market-metrics contract.
> The read-only adapter exposes the current supported values (`price_m2`,
> `asking_price`, `dom`, `active_listings`, `market_heat`, `price_growth` and
> `sales_velocity`) with their units and snapshot date. It neither reads tenant
> estates nor recomputes heat, writes a synthetic observation, or substitutes a
> current value for historical points. Exact H3 requests use that cell's stored
> resolution; city/global summaries use the documented canonical resolution 9.
> Each response selects one newest published input version before it reads cells,
> so a summary never combines metric values from separate publication versions.
> `heatmap_precompute` also now groups source records by H3 cell before it
> labels them, preventing conflicting place labels from yielding duplicate cell
> rows. Dated history remains intentionally partial until actual dated market
> publications are available.

> **Implementation update — training-data importer, 2026-09-15.** A local,
> operator-only `import-itbi-campinas-observations` command now maps the
> curated Campinas ITBI workbook through its already-present neighborhood
> geocode cache into the training-only `valuation_observations` contract. It
> validates the full source before it opens a write transaction, writes in
> bounded batches inside that one transaction, uses deterministic transaction
> identity, and never calls Google, creates tenant estates, serves raw
> observations, or promotes an AVM. Running it without `--apply` is a
> read-only coverage preview. **This is ingestion capability, not a claim that
> production has been loaded or that the candidate has been promoted.**

> **Implementation update — scope and history semantics, 2026-09-14.** The
> first non-provider corrections in section 8A are now connected without
> inventing data:
>
> - `useMarketAnalytics` no longer silently defaults an omitted market scope
>   to São Paulo. Overview, market intelligence, trends and ReportBuilder pass
>   the shared selected city/area when present; otherwise the API is asked for
>   its explicit global platform scope.
> - `useTupanData` accepts that same city and H3 resolution, so its authorized
>   tenant-estate catalog and the independent published-cell request describe
>   the same visible city when a city is selected.
> - `metricHistoryToChartSeries` now retains valid dated points whose values
>   are unavailable, together with their reason. Chart consumers draw those
>   points as gaps and show the empty state only when no usable observation is
>   present; a missing publication is not made to look continuous.
>
> **Implementation update — ReportBuilder summary, 2026-09-14.** The approved
> `GET /analytics/report-summary` provider now resolves the tenant only from
> the authenticated server context and applies the same city/area/active
> predicate to its complete aggregate population and bounded recent-estate
> list. It reports coverage counts beside nullable averages, so missing m² or
> DOM values never become zero. Independent tenant aggregation and published
> `sales_velocity` retrieval fan out through `AnalysisOrchestrator` with the
> existing timeout, cancellation and branch-status rules. ReportBuilder now
> presents that typed response and no longer averages a first catalog page,
> ranks absent heat, or treats a recent list as “top” properties.

> Report AI is now connected through the general agent endpoint's dedicated
> `get_report_summary` tool. The desktop sends only the selected geography;
> `AuthorizedAiTools` calls the same server-owned report provider with the
> immutable tenant context. The model receives structured deterministic
> evidence, and evidence-reference validation rejects unsupported factual
> claims. The former AI-only São Paulo fallback was removed: an omitted city
> now means the explicit published global scope.

## 1. Verdict and verification boundary

**Alignment is not complete in either direction.** Core estate, comparison, portfolio, map and ReportBuilder contracts have been connected. Useful API outputs still lack presenters and several frontend metrics still lack production providers.

This audit inspected the actual dirty working tree: current APIs, schemas, repositories, service/model implementations, frontend adapters/pages, worker registration and local model metadata. Existing changes were preserved. It did not query the live database, authenticate through the preview, run training/publication/jobs or certify current deployment. No application tests/build were rerun for this documentation-only task.

Code existence, schema existence, a trained artifact and a validated production output are different claims. Market heat has legacy calculation code but no functioning current publication path. Future-price forecasting has experimental XGBoost code but unavailable default inference. Current-value AVM and conformal intervals already have a UI contract; inspected transaction artifacts are candidates, not promoted production models.

The prior `demo-portfolio-and-itbi-map.md` records 12 synthetic demo estates and a real partial ITBI transaction map. Backend storage does not make synthetic prices/structural facts verified observations. The academic candidate metadata reports candidate status, production_eligible=false, test MdAPE 35.31%, interval coverage 68.21%. The transaction-v2 metadata is also candidate. These are not customer-property confidence probabilities.

This specification supersedes historical unresolved rows in `frontend-backend-information-contract.md` where later code already implemented the connection. Do not redo estate UUID migration, selected-pair comparison, tenant portfolio scoping or the published-map adapter.

## 2. Classification

| Status | Meaning |
| --- | --- |
| CONNECTED | Provider/schema/API/consumer chain exists; population/deployment is separate. |
| EXPOSED_NOT_PRESENTED | Serving response field has no meaningful active analytical presenter. |
| PARTIAL | Some implementation/input/link exists, but not the complete serving or presentation path. |
| OFFLINE_ONLY | Calculator/artifact is outside current serving. |
| DERIVABLE | Existing facts support an authoritative backend calculation not yet exposed. |
| MISSING_PROVIDER | No valid current production provider for the expected information. |
| WRONG_SCOPE_OR_UNIT | Connected information has wrong population/geography/unit semantics. |
| INTERNAL_ONLY | Intentionally not a customer metric. |
| DEMO | Synthetic/illustrative, not verified analytical evidence. |

## 3. Completed connections to preserve

API paths are relative to `/api/v1`.

| Information | Provider/API | Frontend pair | Qualification |
| --- | --- | --- | --- |
| Estate facts, asking price, area, rooms, DOM, last sale | TenantDataRepository / EstateResponse / `/analytics/estates`, `/estates/{id}` | api/properties.js; Properties, PropertyDetail, Compare, EstateAnalysisWorkspace | Stored facts can be manual/demo. |
| Stored estimate and signed deviation | Domain estate serialization / estimated_price, stored_price_deviation_pct | Catalog, comparison, portfolio | Stored rather than fresh inference; incomplete model lineage. |
| Fresh AVM, BRL difference, deviation and estimated m² | AvmRuntime + valuation_metrics / `/estates/{id}/analysis` | api/analysis.js; PropertyDetail | Explicit partial failure/unavailable states. |
| Conformal bounds, level, calibration evidence | Promoted transaction predictor / analysis valuation and diagnostics | PropertyDetail range/model details | Presenter exists; validated promotion required, not confidence probability. |
| Completeness, quality, missing fields/reasons | estate_quality -> assess_data_quality -> analysis.data_quality | PropertyDetail details | Operational data quality, not AVM accuracy. |
| Comparable peers, eligible count, distance, median m², mean DOM | Comparable repository / analysis and comparison | PropertyDetail table/context | Same-organization peers, not universal corpus; distance is not similarity. |
| A/B factual differences | estate_comparison / `/analytics/estate-pair` | Compare | Backend arithmetic; unsupported score rows remain empty. |
| Portfolio asking totals, pricing, positions, concentration/type mix and own-history liquidity | Portfolio branches / `/portfolios/{id}/overview` | usePortfolioAnalytics, Portfolio, Overview | Authorized portfolio, explicit missing estimates; liquidity is portfolio-owned, not a global/comparable fallback. |
| H3 geometry and published listing inventory/m²/DOM | Platform publisher / `/market/heatmap` | MarketMap, RegionPanel, MarketIntelligence | Only published dataset/scope. |
| ITBI count, mean/median declared transaction price, period | academic_itbi.transaction_cells / platform heatmap | Map tooltip and transaction RegionPanel | Partial sample, not active listings/demand/AVM. |
| Dated published market observations | published_market_response / `/market/published-metrics` | useMarketAnalytics, market cards/history | Reader/normalizer exists; producer/data not guaranteed for every metric. |
| AI interpretation, evidence, warnings | AuthorizedAiTools / AiOrchestrator / `/agent/chat` | VoiceAgent, AiEvidence, AiBrief, AgentLog | Explains facts, cannot supply absent analytics. |

## 4. Backend -> frontend: outputs without complete pairs

Exposed does not mean non-null in today's database.

| ID | Backend provider / exact output | API and handoff | Status / missing link | Intended pair |
| --- | --- | --- | --- | --- |
| B01 | PORT valuation_summary.estimated_value | Portfolio overview -> portfolioToView.estimated_value | CONNECTED; presented as the registered estimated portfolio value with coverage | Stored-estimate total remains distinct from fresh AVM inference and is nullable when coverage is incomplete. |
| B02 | PORT pricing_statistics.median_price_per_m2 | Same -> adapter of same name | CONNECTED; existing portfolio metric presents the median explicitly | Mean and median retain distinct labels and units. |
| B03 | PORT market_exposure[].market_heat | Same -> market_exposure | CONNECTED; existing exposure table presents market heat when publication exists | A null cell remains an unavailable publication, not zero heat. |
| B04 | GEO indicators.liquidity | Offline exact-H3 Kaplan–Meier publisher -> heatmap/published-metrics -> marketCellToView -> RegionPanel/MarketIntelligence | CONNECTED_IN_CODE; production publication/support still determines availability | Score is `100 × [1 − S(T)]` for the selected horizon, based only on sold events and right-censored active listings in the exact cell/resolution. No neighboring-cell fallback; insufficient support stays null with a reason. |
| B05 | GEO metrics.average_asking_price | Heatmap -> average_asking_price -> RegionPanel | CONNECTED; regional asking price is labeled separately from transaction price | No client-side aggregation. |
| B06 | COMP local_statistics.average_asking_price, median_asking_price, average_price_per_m2 | Analysis -> LocalStatistics -> PropertyDetail | CONNECTED; detail shows these alongside median m² and mean DOM | They are comparable evidence, not universal market statistics. |
| B07 | AVM valuation.model_version / avm_diagnostics.model_version | Analysis -> typed fields -> PropertyDetail | CONNECTED; model version is visible in model details | Schema version remains a separate contract identifier. |
| B08 | AVM avm_diagnostics.out_of_time_median_width_pct | Analysis -> typed diagnostics -> PropertyDetail | CONNECTED when calibrated; presented as dataset-level validation detail | It is not a property-specific interval width. |
| B09 | GEO input_version, periods, scope/publication metadata | Heatmap/estate analysis -> typed LocationMetrics -> PropertyDetail | CONNECTED; compact provenance disclosure | `PublishedCell` and `LocationMetrics` preserve string/bool metadata at the boundary. |
| B10 | ITBI metrics.source_row_count, geocoded_row_count, partial_coverage | Heatmap nested metrics -> marketCellToView -> RegionPanel | CONNECTED; transaction count, source/geocoded counts and the partial-coverage warning are visible in the selected transaction cell | The ratio is labelled as coverage of the source and is not presented as citywide coverage or pure geocoding success. |
| B11 | MKT metric status/reason and point reason | PublishedMetric -> chart adapter -> MarketIntelligence/ReportBuilder | CONNECTED for historical presenters; dated unavailable points preserve gaps and the returned reason is visible below the series | Current-value cards intentionally show only the latest typed value/status rather than duplicating each historical reason. |
| B12 | GEO estate location_metrics.metrics including transactions | Estate analysis -> PropertyDetail | CONNECTED for decision-useful inventory/transaction evidence; remaining raw metrics are internal until a defined presentation need exists | Transaction count is labeled separately from inventory. |
| B13 | MKT H3-scoped published history | published-metrics?h3_index=... -> useMarketAnalytics -> MarketIntelligence | CONNECTED_FORWARD_ONLY; selected H3 receives its persisted dated points, while a multi-date line appears only after multiple real publications | It never substitutes city history for H3 history or invents prior points. |
| B14 | COMP property type, bathrooms, parking, stored estimate, locality and cosine similarity | ComparableService -> ComparableEstate/metadata -> PropertyDetail; pair score -> Compare | CONNECTED | Backend ranks the authorized candidate set using the versioned structural vector; missing-vector candidates remain explicit and the frontend does not recreate the score. |

### Existing algorithms outside the serving path

| ID | Calculator/output | Actual availability | Intended treatment |
| --- | --- | --- | --- |
| O01 | valuation_uncertainty.local_residual_correction: correction_log, lambda, effective_n, max_age_days, residual_dispersion, warnings | OFFLINE_ONLY; requires eligible timestamped out-of-fold residuals; not assembled by AvmRuntime | Support/warnings may enter valuation evidence after validated integration; adjustment math stays internal. |
| O02 | radar/data_base/metrics.calculate_market_heat: spatial_heat_L, momentum_growth_G, market_heat; leverage mutation | Legacy non-operational; requires sales/predictions and calls reindex on NumPy G | Existing heat KPI/map are ready destinations, but validate/repair and adapt to approved global publication first. |
| O03 | ForecastService/train.analytics: P10/P50/P90, future value, expected_growth_pct, horizon | PARTIAL; default analyze_tendency raises ForecastArtifactMissingError, route legacy-guarded; getPropertyForecast has no consuming import | Valid artifact inference/authorized request first, then future-price range. Distinct from current AVM. |
| O04 | calculate_portfolio_hhi, calculate_h3_clustering_coefficient, legacy portfolio stats | OFFLINE/LEGACY, not current PORT outputs | Adapt if useful; define type/count vs geography/value concentration and scale. |
| O05 | calculate_location, luxury_prediction, neighboring/similarity price, xg_learn blending | PARTIAL legacy paths, not serving 4L; similarity helper uses legacy search and unresolved real_estate symbol | Validate provider before 4L/reference UI; neighboors enrichment can remain training-only. |
| O06 | Training MAE/MdAPE/p90/tolerance rates/COD/PRD, coverage/width, promotion metadata | Real local research diagnostics | INTERNAL_ONLY/operator model readiness by default, never per-property confidence. |
| O07 | ForecastContext macro fields: Selic, mortgage, IPCA, income, employment, indices | Optional schema/passthrough, no established ingestion/serving feed | No new macro display without actual dated sources. |

## 5. Frontend -> backend: expectations without valid current sources

| ID | Expected information/field | Consumer | Status | Required authoritative source |
| --- | --- | --- | --- | --- |
| F01 | market_heat and history | Overview/map/market charts/property list/PropertyDetail/Compare | CONNECTED for current H3/city/global snapshots | The offline global publisher calculates heat from listing inventory plus dated sales. Estate catalog uses one page-level H3 join; detail and comparison normalize the same published aggregate. Multi-date history remains forward-only under F14. |
| F02 | demand_score | Former RegionPanel and MarketIntelligence field | REMOVED | It duplicated the canonical `market_heat` concept without an independent producer. The active API, adapters and UI now expose market heat only. |
| F03 | liquidity_score | Overview, Properties, Compare, PropertyDetail, Portfolio, Market Map, Market Intelligence | CONNECTED_IN_CODE | Estate liquidity uses the offline global artifact; portfolio liquidity uses only portfolio-owned histories; regional liquidity is precomputed per exact H3 cell/resolution from that cell's sold events plus censored active listings. All active consumers now use the shared selected horizon and preserve null/status/support. Production cells require a post-deploy refresh and adequate source support. |
| F04 | expected_growth_pct, regional/portfolio growth forecast | Properties side panel, Portfolio, dormant forecast client | PARTIAL | Valid forecast with horizon/reference then backend aggregation; historical growth is different. |
| F05 | price_growth current/history | Market charts, RegionPanel | CONNECTED for current H3/city/global snapshots; history PARTIAL | Observed sale-window price change is available only where both windows meet support requirements; no synthetic prior points are produced. |
| F06 | sales_velocity and history | Trend cards/intelligence/RegionPanel | CONNECTED for current H3/city/global snapshots; history PARTIAL | The provider uses eligible recent observed sales divided by the explicit 60-day window (sales/day). |
| F07 | valuation_confidence / portfolio confidence | Compare, Portfolio, estate adapter | MISSING_PROVIDER | Validated confidence policy if required. Existing conformal ranges and data quality are not probability of correctness. |
| F08 | valuation_class | Estate catalog and PropertyDetail valuation | CONNECTED_WITH_LINEAGE_GUARD | The backend alone classifies asking price as below/within/above a calibrated promoted AVM interval. Fresh analysis can carry that range. A stored catalog estimate has no persisted calibrated bounds today, so it truthfully yields `INSUFFICIENT_CONFIDENCE`; missing asking/estimate yields no classification. The frontend presents the returned class, central estimate, interval and signed deviation without ±5%/±10% rules. |
| F09 | luxury/leisure/location/leverage/profile_scores | PropertyDetail 4L, Compare radar | PARTIAL | Runnable validated 4L providers on real features; adapter deliberately emits null. |
| F10 | catalog comparable_count / similarity | Estate catalog, PropertyDetail, Compare | CONNECTED | Catalog count is computed in one tenant-scoped SQL read with the canonical 2.5 km rule (city/area fallback without coordinates). Detail candidates are ranked by a versioned backend cosine over structural fields; direct comparison uses the same producer. Null/status/eligible/scored/truncated metadata remain explicit. |
| F11 | average_listing_age_days | Portfolio selector | CONNECTED | `pricing_statistics.average_listing_age_days` is the mean of `CURRENT_DATE − listed_since` for dated active listings only. `listing_age_count` is returned alongside it; missing dates yield null rather than a DOM fallback. |
| F12 | sold_listing_count, stagnation_rate, hhi | Former dormant portfolio adapter placeholders | REMOVED_DORMANT | The active UI did not consume these values, so its synthetic null keys were removed rather than creating providers without a presentation need. Portfolio-owned sale events remain explicitly reported as liquidity support, not relabelled as total sold inventory. |
| F13 | Portfolio value/inventory/DOM/gap histories | Portfolio metric tabs/zoom | CONNECTED_FORWARD_ONLY | Event-coalesced, tenant-scoped daily snapshots persist active inventory, asking-value, mean DOM, listing age and mean price gap. The Portfolio metric tabs consume only persisted points and label them as observations. No pre-migration history or unchanged-calendar days are fabricated. Overview has no separate historical portfolio presenter. |
| F14 | Market histories generally | Trend metrics, Overview, intelligence/report | CONNECTED_FORWARD_ONLY | Every `refresh-heatmap` publication persists its calculated, unit-labelled observations. Resolution 9 is the canonical global/city/area source; every requested resolution persists exact-H3 history. No periods before the publisher was connected, or days without a publication, are fabricated. |
| F15 | Opportunities/unread notification feed | OpportunityNotifications | MISSING_PROVIDER | Authorized evaluation/persistence/read API and registered worker handler; bell currently honestly unavailable. |
| F16 | Report-wide KPIs/recent estates | ReportBuilder | CONNECTED | `GET /analytics/report-summary` owns complete active-tenant aggregates, explicit field coverage and a bounded recent list. No heat ranking is claimed. Report prose is grounded through the `get_report_summary` authorized AI tool. |
| F17 | Real property photos | ListingCard/catalog | DEMO | Authorized media source; illustrative assets are not property evidence. |
| F18 | Verified facts in demonstration portfolio | Portfolio/catalog/compare | DEMO | Synthetic pricing/structural facts must remain labeled/excluded from training; API-backed is not observed. |

## 6. Incorrect connections to fix first

1. Geography: **Corrected.** UI and controlled-AI market reads now forward the shared city/area explicitly or request the published global scope. No São Paulo fallback remains in these providers.
2. Units: **Corrected.** Sales velocity is expressed as `sales/day`/`vendas/dia`; no arbitrary monthly multiplier remains in the connected presenters.
3. Report arithmetic: **Corrected.** The backend owns complete-scope averages, coverage, inventory and a bounded recent list; the controlled AI report tool retrieves the same authorized summary rather than trusting browser-composed values.
4. History: **Corrected.** Dated unavailable points and their reasons remain in the chart data as gaps.
5. Model readiness: **Corrected where data exists.** PropertyDetail renders calibrated ranges plus model version and out-of-time validation evidence. Do not rebuild UI or disable promotion safeguards to force data. Candidate diagnostics are not production certification.
6. Stored estimate lineage: migration 014 adds server-owned provenance for future recorded estimates: recording timestamp, source, input fingerprint and nullable model version. Existing records remain unknown. Input edits mark known lineage for review; a changed estimate resets attribution. Estate/catalog, comparables, pair comparison and portfolio positions expose it; portfolio totals expose lineage/review counts. Frontend labels recorded values explicitly. **Migration pending; no production population claimed.** Current recording paths do not establish AVM model identity, so model version remains null. Fresh inference is still separate.
7. Types: **Corrected for location evidence.** LocationMetrics and its frontend contract now preserve scope, input version, dates and nonnumeric metrics. The abbreviated comparable row remains intentional for its compact table.
8. Period/filter scope: backend HeatmapQuery accepts date bounds but getMarketCells exposes city/area/resolution and rejects periodDays. Connect supported dates only if publications exist. Never emulate individual price/type filters with aggregate means.

## 7. Ownership and intentional internal-only data

Estate facts: tenant repository/provenance. Fresh valuation/range: promoted AvmRuntime. Comparable selection/stats: comparable repository. Portfolio totals/concentration/positions: portfolio analytics. Global heat/demand/momentum/history: approved global producer -> stored publication -> normalized market service. Spatial/sample metrics: platform publisher. Future quantiles: validated forecast provider. AI: interpretation. Frontend: formatting/interaction/visual geometry only.

Keep weights, encodings, feature vectors, training rows, Google enrichment payloads, residual samples, calibration internals and secrets internal. Data-quality observed_weight is bookkeeping; completeness/quality/reasons already explain it. Timing/job internals belong in diagnostics, not market KPI cards. Candidate validation can stay in operator reports. Every backend field does not need a customer card.

computePortfolioStats/computeMarketStats remain as dormant lib/analytics.js definitions; search found no consuming imports. They are not active production providers. No removal in this task.

## 8. Remaining implementation sequence

### A. Correct current links

Completed: unify UI/AI geography; fix velocity units; replace report population/null/pagination arithmetic with backend summaries; retain publication error/gap semantics; and ground report prose in a report-specific authorized AI tool. Contract tests cover scoped report output, cross-tenant SQL predicates, deterministic AI evidence and fan-out timing.

### B. Expose useful existing outputs

Selectively connect B01-B13 inside current portfolio/valuation/region/metric components. Show estimated total/coverage, median m², optional heat/liquidity, asking vs transaction prices, model version, sample/source context. H3 history only if populated. Preserve metric tabs/zoom and existing architecture.

### C. Complete real providers

Validate/adapt existing heat/forecast code, approved global inputs, artifacts/promotion and publication. Integrate 4L/local support only when dependencies work. Portfolio histories and notifications need actual producers, not scaffolding. No training/publication/migration is performed here.

### D. Verify real end-to-end evidence

Source population/unit/date -> provider -> schema -> API -> adapter -> rendered UI. Test tenant isolation, global aggregate-only access, unavailable models, partial branches, nulls and demo provenance. Fixtures prove handling, not source population. Mark a row complete only after serving and presentation verification.

Acceptance: one provider/provenance per displayed metric; useful outputs have presenters or intentional omissions; no heat/forecast/confidence success based on schema/model names; no client/AI replacement arithmetic, legacy authorization bypass or candidate promotion bypass.

## 9. Source evidence index

Repository-relative inspected locations:

- `ceres/backend/api/routes/analysis.py`, `api/schemas/analysis.py`, `api/schemas/published_metrics.py`: current contracts.
- `ceres/backend/repositories/tenant_data.py`: published_market_observations, comparable/local statistics, portfolio branches; platform_intelligence.py: global sources.
- `ceres/backend/services/analysis_orchestrator.py`, valuation_metrics.py, estate_comparison.py, estate_quality.py, avm_runtime.py, published_metrics.py: authority/normalization.
- `ceres/backend/services/platform_intelligence.py`, heatmap_precompute.py; `ceres/train/academic_itbi.py`: actual aggregate producers.
- `ceres/backend/services/market.py`, forecast.py; `ceres/train/analytics.py`, xg_learn.py; `ceres/radar/data_base/metrics.py`: legacy/experimental providers.
- `ceres/train/transaction_avm.py`, valuation_uncertainty.py, valuation_validation.py; artifacts academic_address_candidate.metadata.json and avm_transaction_v2.metadata.json: serving/promotion/diagnostics.
- `ceres/backend/services/ai/tools/analysis_tools.py`, ai/orchestrator.py; `ceres/backend/worker.py`: controlled evidence and empty default handler registry.
- `ceres/ui/tupan-intel-core/src/api`: properties, analysis, portfolio, market, forecast, agent adapters.
- Frontend lib: useMarketAnalytics, usePortfolioAnalytics, useTupanData, analytics.
- Frontend pages: Overview, Portfolio, Properties, PropertyDetail, Compare, MarketMap, MarketIntelligence, MarketTrends, ReportBuilder, DataManagement, VoiceAgent, AgentLog.
- Shared tupan components: RegionPanel, Map3D, ListingCard, OpportunityNotifications, AiEvidence, AiBrief, StatCard.

Verification: source/documentation review only. Prior test outcomes are not relabeled as current production verification.
