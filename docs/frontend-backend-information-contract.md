# CERES bidirectional information contract audit

> Current remaining-work specification (2026-09-14): [frontend-backend-alignment-spec.md](frontend-backend-alignment-spec.md). It separates connected paths, unused serving outputs, unsupported metrics, offline models and demo versus real data. Historical findings below are not all current; section 18 and this newer specification take precedence. The actionable active-route wiring is complete as of 2026-09-16; provider/data prerequisites and explicitly deferred 4L/notifications remain open. This document preserves the original audit as an evidence baseline.

Audit date: 2026-09-12. Scope: the current working tree, including existing uncommitted work. This is a source-level contract audit, not a certification of a deployed database, populated dataset, trained artifact, or external provider. The bounded reconciliation implementation and the serving-safe AVM uncertainty contract are recorded in section 18; deployment still requires a reviewed promoted artifact.

Sections 1–12 trace frontend demand toward providers. Sections 13–17 trace backend outputs toward existing presenters using the reverse-audit status vocabulary. Presenter connections are specifications, not UI changes applied in this audit. Section 18 records the subsequent reconciliation execution state; audit findings must not be marked resolved until corresponding implementation and verification are completed.

## 1. Executive finding

CERES has substantial frontend information demand, but its active desktop adapters still principally consume the legacy global property/market/portfolio contract. The newer PostgreSQL tenant-scoped estate, comparison, analysis, portfolio and platform-heatmap endpoints exist **without corresponding frontend clients**. These are not interchangeable response shapes.

> **Current implementation note (2026-09-14):** this audit records the
> pre-connection baseline. The current frontend now consumes the scoped
> estate/analysis/portfolio and published-heatmap adapters described below.
> Global market heat is provided by `backend.services.market_heat` as an
> offline, aggregate-only H3 publication. It is selectable at practical H3
> levels 7–10 in map/intelligence UI (publisher supports 0–15), but must be
> explicitly published before cells exist. Future forecasts and
> historical heat still have no new provider and remain
> unavailable rather than being fabricated.

> **Liquidity update, 2026-09-15.** Estate-level `liquidity_score` is served only from the
> aggregate global survival artifact introduced by migration `011`; it is not
> calculated in React and is not a heat/demand/DOM substitute. The desktop
> sends the existing shared top-bar period as an explicit day horizon. The API
> returns `available`, `model_unavailable`, `insufficient_evidence`,
> `missing_listing_duration`, `not_active`, or `horizon_not_selected` with a
> nullable score. The model is unavailable until the migration and offline
> publication command have succeeded. Portfolio liquidity is deliberately
> separate: it uses only that authorized portfolio's active listings and sold
> listings, with no global/similar-sale fallback, and reports support plus a
> typed unavailable state when its own history is inadequate.

> **Market-history update, 2026-09-15.** The offline `refresh-heatmap`
> publisher now projects each calculated publication into `market_observations`
> with deterministic identity. Resolution 9 is the sole global/city/area
> source; every selected resolution publishes exact-H3 observations. The
> existing `/market/published-metrics` contract consequently returns factual
> historical points after subsequent publications, never inferred calendar
> points.
>
> **Portfolio-history update, 2026-09-15.** Migration `012` introduces
> tenant-scoped `portfolio_metric_snapshots`. Estate changes enqueue one
> idempotent snapshot job per portfolio/day; the worker captures the then-current
> authorized state under the originating tenant context. The Portfolio metric
> tabs consume only these chronological observations for asking value, active
> inventory, mean DOM, listing age and mean price gap. Dates before this
> migration, and calendar days without an observation, remain absent.

> **Signed-growth and ITBI-coverage update, 2026-09-15.** The published-market
> snapshot adapter preserves observed negative `price_growth` percentages
> instead of discarding them through a generic non-negative numeric guard.
> Transaction cells now carry `source_row_count` and `geocoded_row_count`
> through the frontend adapter, and the regional presenter labels their ratio
> specifically as coverage of the imported source. It remains explicitly
> partial and is never presented as citywide market coverage.

> **Comparable-presentation update, 2026-09-15.** The existing comparable
> response fields for property type, bathrooms, parking, stored estimate and
> locality now remain in the frontend contract and are presented compactly in
> PropertyDetail. No similarity score is synthesized, and the registered
> estimate is labelled separately from the asking price.

> **Dormant portfolio-field update, 2026-09-15.** Unsupported null placeholders
> for total sold inventory, stagnation and HHI, plus the unreachable empty
> regional-growth branch, were removed from the active frontend adapter. The
> portfolio liquidity evidence continues to expose its eligible own-portfolio
> sale-event support, which is not relabelled as a total sold-estate count.

The highest-impact mismatches are:

1. `/properties`, `/portfolio/analytics`, `/market/cells`, `/market/regions/*`, `/metrics/*` and `/forecast` are guarded by `require_legacy_domain_access`. Access is disabled by default, and the production settings reject enabling legacy global data. Do not restore functionality by disabling this boundary.
2. `/estates`, `/estates/{id}/analysis`, `/estates/{id}/comparison`, `/portfolios/{id}/overview` and `/market/heatmap` are already registered, but analytical screens do not call them. Legacy address-hash property IDs are not PostgreSQL estate UUIDs.
3. Some information is lost even before changing endpoints: the list adapter drops structural attributes and 4L scores needed by listing cards and the comparison screen. Property notes also have incompatible request and response field names.
4. The global heatmap publisher currently produces only inventory, mean asking price, mean price/m² and mean DOM. It does **not** publish heat, demand, growth or velocity. Legacy `MarketService` imports `predict.market_heat` and `ui.controllers.analytics_controller`, neither of which is present in this repository's source tree.
5. The forecast response schema describes quantiles, but `train.analytics.analyze_tendency()` unconditionally raises in its default inference-only mode. A valid forecast cannot currently be obtained merely by configuring an artifact path.
6. The legacy AVM supplies point estimates without calibration. The transaction XGBoost now has a serving adapter for split-conformal prediction intervals, but it is activated only when its metadata is explicitly promoted; no probability-of-correctness is claimed and no candidate artifact is served.
7. The notification bell is a client-side top-three ranking of legacy below-estimate properties. It is not a read of the `notifications` table or a working notification worker. Its AI request uses `property_id` where the agent resolves `id`.
8. AI context transmission drops all but the first property, ignores portfolio/chart context, loses filter scope, and can reinterpret a neighborhood as a city. The active voice page drops response evidence/warnings/session metadata. Visible chat history is not model conversation memory.
9. Most compact metric histories are empty. The one historical producer averages listed prices per observation date, while the mini-chart labels its last **three records** as “Últimos 3 meses”. Historical inventory/DOM/velocity cannot be recovered from a current snapshot alone.
10. The overview actually renders a hardcoded 2024 desktop/mobile visitor chart. Stock estate photos are explicitly illustrative. Neither is a production property/market data source.

## 2. Method, status semantics, and coverage

Tracing starts at routed pages and their shared components, then follows `src/api`, hooks and adapters, registered FastAPI routes, response schemas, service implementations, SQL/repositories, training/inference code and background publishers. A declared schema/table is **not** evidence of an implemented calculation or populated source.

| Status | Meaning in this document |
| --- | --- |
| CONNECTED | Matching consumer, registered API and responsible implementation exist. Deployment/data availability is not implied. |
| AVAILABLE_NOT_CONNECTED | An existing output/implementation can supply the information, but the active consumer does not use it. Notes distinguish an already-exposed API from a code-only helper. |
| DERIVABLE | Existing backend fields support the specified calculation/filter, but the authoritative backend output is not implemented/exposed. Not permission to invent a new policy. |
| PARTIAL | Only part of the contract exists, a required source/pipeline is absent, or selection/metadata semantics are incomplete. |
| MISSING | No valid implemented provider for the expected value or behavior was found. A named schema or non-serving experiment alone does not satisfy it. |
| MOCKED | Hardcoded/demo data or an asserted result without a corresponding measurement. Static navigation labels and visual constants are not mocked metrics. |
| DUPLICATED | The same business quantity/policy is calculated or represented in multiple places, with possible divergence. |
| WRONG_PROVIDER | The active source has the wrong scope, entity identity, semantics, or responsibility for the displayed information. |

Each matrix row uses one primary status. Its notes can also describe secondary problems. Repeated uses share rows only where the exact fields and provider chain are the same. `—`, `null`, loading and errors are not themselves fabricated data; converting missing information to a measured zero is a separate issue.

### Routed coverage

| Route / surface | Components inspected | Information covered |
| --- | --- | --- |
| `/overview` | Overview, KpiCard, Panel, StatCard, SectionNav, AiBrief, ListingCard | Six summary metrics, mini-history/zoom, concentration, valuation distribution, featured estates, rules/insights |
| Overview market sections | Named `MarketTrendMetrics` export; embedded MarketIntelligence; ChartAreaInteractive | Historical price/inventory/DOM/velocity, region comparison, bar/scatter charts, demo visitors |
| `/properties`, `/properties/:id` | Properties, PropertyDetail, table columns, notes | Property facts, valuation, expected growth, 4L, comparables, status |
| `/compare` | Compare, property pickers, radar, difference highlights | All 17 comparison fields and derived winners/differences |
| `/market-trends` | Default `EstateAnalysisWorkspace` export | Estate catalog with illustrative photos, selected estate facts and AI handoff |
| `/market-map` | MarketMap, FiltersPanel, Map3D, Heatmap3D, RegionPanel, MapHeatLegend | H3 geometry, heat and ancillary cell metrics, filter scope, tooltips |
| `/portfolio` | Portfolio, shared metric/chart components | Portfolio totals, concentration, type mix, pricing lists, risk narrative |
| `/report-builder` | ReportBuilder | Region/period selection, local KPIs, top estates, history, AI summary, PDF |
| `/agent`, `/voice` | VoiceAgent, VoiceChatHistory, VoiceToolbar, PersonaPanel | Messages, selected context, evidence, speech, history and processing state |
| `/agent-log` | AgentLog | Session traces, tools, duration, warnings/errors, source labels |
| Global shell | TopBar, UserAdminMenu, InsightTray, AppContext, menus | User identity, period, saved context, opportunity bell |
| `/saved-searches`, `/data` | SavedSearches, DataManagement | Search definitions/results, estate CRUD, reference tables, imports |
| `/settings`, `/team-management` | Settings, TeamManagement | Identity, role, preferences, invitation and model status |
| Public/auth routes | Welcome, Menu, Login, Register, ForgotPassword, ResetPassword, AuthContext | Navigation/copy versus real authentication and unsupported recovery/social actions |

`/market-intelligence` redirects into overview; it is not a second independent active analytics implementation. `/agent` and `/voice` render VoiceAgent, **not** `IntelligenceAgent.jsx`. `computePortfolioStats`, `regionByName` and `useMapBoundaries` have no consuming imports in the current frontend. Generic UI samples/animation geometry are not production metrics.

## 3. Provider and endpoint map

Paths below are relative to `/api/v1` unless explicitly stated otherwise. API base selection is `VITE_TUPAN_API_URL || VITE_API_BASE_URL` in [client.js][F-client]. The authoritative registered app inspected is [backend/api/main.py][B-main]. Merely finding another server under `ui/` does not make its outputs part of this app.

| Provider ID | Existing implementation and underlying source | Registered output / current role | Authority decision for a connected contract |
| --- | --- | --- | --- |
| EST | [TenantDataRepository][B-repo], [Estate schemas][B-estate]; tenant-filtered `estates` and `portfolios`, authenticated organization | GET/POST `/estates`; GET/PATCH/DELETE `/estates/{id}`; PATCH `/estates/{id}/portfolio`; GET/POST `/portfolios`; GET `/portfolios/{id}` | Authoritative estate facts, entity IDs, ownership and portfolio membership. Stored `estimated_price` alone does not establish model provenance. |
| ANA | [AnalysisOrchestrator][B-analysis], [analysis routes/schemas][B-analysis-routes] | GET `/estates/{id}/analysis`; authorization before AVM/comparables/statistics/market/location fan-out; component timing/state | Authoritative assembly of estate analysis, not an independent second formula source. |
| AVM | [AvmRuntime][B-avm] → `train.avm.predict_price`, persisted schema-1 XGBoost artifact | `analysis.valuation`: point estimate, differences, m² values, inference time | Authoritative **fresh valuation** path. Normalize shared gap calculation in the domain layer; persist lineage if estimates are cached. |
| COMP | `TenantDataRepository.list_estate_comparables` / `estate_local_statistics` | GET `/estates/{id}/comparison`, also ANA and AI tools | Authoritative comparable selection/statistics. Currently same-organization active peers, same type, PostGIS radius or city/area fallback. Not a global comparable corpus, not an arbitrary A-vs-B comparison. |
| PORT | Five `TenantDataRepository.portfolio_*` queries composed by ANA | GET `/portfolios/{id}/overview` | Authoritative portfolio-derived outputs; active estate subset for that authorized portfolio. |
| GEO | [PlatformIntelligenceService][B-platform] → [platform repository][B-platform-repo] → `_aggregate_sources`; PostGIS/H3 | GET `/market/heatmap`; ANA `location_metrics`; stored `scope='platform'` aggregates | Authoritative shared geographic metrics from offline publication. HTTP callers read stored aggregates, not private raw global estates. |
| MKT | `estate_market_context`, `portfolio_market_exposure`; platform `market_observations` | Embedded in ANA/PORT; generic metric/value/unit/date/source rows | Authoritative published market observations. No implemented current producer populates heat/demand/growth/velocity or a complete historical market API. |
| OLD-P | [PropertyService][B-property] → `radar.config.collection` Chroma property documents | `/properties`, `/properties/search`, `/properties/{id}`, `/properties/{id}/valuation`, `/properties/import` | Legacy guarded compatibility, not tenant production authority. Requires `VECTOR_DB`; hash-based IDs differ from EST. |
| OLD-M | [MarketService][B-market] → legacy properties; missing `predict.market_heat` and `ui.controllers.analytics_controller` imports | `/market/overview`, `/market/cells`, `/market/regions/{h3}`, POST `/analytics/market-intelligence`, GET `/metrics`, `/metrics/{metric}/history` | Not a valid production market authority. Only the listed-price history implementation is present independently of those missing imports. |
| OLD-PORT | [PortfolioService][B-portfolio] → OLD-P collection | GET `/portfolio/analytics`; POST same path accepts supplied property objects | Existing formulas available to adapt, but current GET treats the whole collection as active, sold list empty. Not PORT-equivalent. |
| FC | [ForecastService][B-forecast] → [train.analytics.analyze_tendency][B-train-analytics] | POST `/forecast` (guarded) | Intended forecast authority, but inference always refuses today. No valid serving forecast provider yet. |
| AI | [AiOrchestrator][B-ai] + [AuthorizedAiTools][B-tools] + validated interpretation client | POST `/agent/chat`; GET `/agent/sessions/{session_id}/traces` | Interpretation over authorized deterministic evidence; not a provider of missing prices, rankings, confidence or arithmetic. Market metric tool still delegates to OLD-M. |
| WS | [ControlPlaneService][B-control] and [workspace routes/schemas][B-workspace] | `/workspace/members`, `/workspace/saved-searches`, `/workspace/properties/{id}/notes`, `/workspace/district-boundaries` | Authoritative workspace storage. Exact note/date fields must be adapted. |
| AUTH | ControlPlaneService; separate SupabaseControlPlaneService | v1 `/auth/register`, `/login`, `/session`, `/logout`; separate `/api/v2/auth/*` | Current desktop uses v1 cookie/session. Supabase v2 login is not a drop-in replacement for v1 data-route authentication. |
| JOB | [JobQueueRepository][B-jobs], [worker][B-worker], migrations | POST `/jobs`; GET `/jobs/{id}` | Durable state/claim/retry infrastructure exists. Default worker handler registry is **empty**; no actual notification/import/embedding/portfolio handlers are registered. |
| CAND | [transaction_avm][B-candidate], [valuation_data][B-data], [valuation_uncertainty][B-quality] | Offline `train_transaction_avm`; promoted artifacts are consumed by ANA | Candidate training remains offline; explicit promotion enables calibrated interval fields in ANA. It never silently replaces the legacy model and is not a confidence probability. |

The existing SQL schema includes `analysis_results`, `notifications`, `conversations`, `conversation_messages`, `semantic_embeddings`, `market_observations` and `valuation_observations`. Schema existence is recorded as partial support where no repository/service producer or read API exists.

## 4. Frontend information matrices

### A. Estate catalog, property detail, estate analysis and comparison

Sources: [properties adapter][F-properties], [Properties][F-properties-page], [PropertyDetail][F-detail], [Compare][F-compare], [EstateAnalysisWorkspace][F-trends], [ListingCard][F-listing].

| ID | Frontend feature | Required information / frontend field | Current API / call | Backend provider → field / underlying calculation | Status | Contract finding |
| --- | --- | --- | --- | --- | --- | --- |
| E01 | Lists, detail, compare selection, agent handoff | `id` | `getProperties`, `getProperty`, `searchProperties` → `/properties*` | OLD-P hash of normalized address; EST `id` UUID | WRONG_PROVIDER | Use authorized estate UUID end-to-end; do not assume `property-<hash>` resolves in EST/AI. Migration parity is unverified. |
| E02 | Title and address | `title`, `address`, `api_property.summary` | `/properties*` | OLD-P `location.address`, `summary`; EST `title`, `address`, `summary` | WRONG_PROVIDER | Title is reconstructed from address/summary, rather than EST title. EST fields already exposed. |
| E03 | Location labels | `city`, `neighborhood` | `/properties*` | OLD-P `location.city/area`; EST `city/area` | WRONG_PROVIDER | `neighborhood` maps to backend `area`. Missing values become `—` in adapter, not actual geography. |
| E04 | Property type | `property_type` | `/properties*` | OLD-P `kind`; EST `property_type` | WRONG_PROVIDER | Normalize values as well as name; current controls mix English and Portuguese type options. |
| E05 | Listed/current price | `price` | `/properties*` | OLD-P `pricing.asking_price`; EST `asking_price` | WRONG_PROVIDER | EST supplies this fact. Old valuation helper may fall back to last sale; that is not the same as a current asking price. |
| E06 | Listed price/m² | `price_per_m2` | `/properties*` | OLD-P `metrics.price_per_m2`; EST stored `price_per_m2`; ANA recomputes asking/area | DUPLICATED | Stored versus recomputed value can differ. Specify domain authority and denominator; retain null if price/area unavailable. |
| E07 | Persisted suggested price on cards/lists | `suggested_price` | `/properties*` | OLD-P `predictions.suggested_price`; EST `estimated_price` | WRONG_PROVIDER | This is a stored estimate, not proof that the current AVM ran. No model/date/provenance accompanies it in list contract. |
| E08 | Gap shown in table/card/workspace | `price_deviation` | Computed by `propertyToListItem` | `(asking-estimate)/estimate*100`; ANA `valuation.difference_percent` | DUPLICATED | Backend already calculates this for fresh analysis; keep one formula with explicit same-estimate lineage. |
| E09 | DOM in list/detail/compare | `days_on_market` | `/properties*` | OLD-P `dom_days`; EST `days_on_market` | WRONG_PROVIDER | Existing EST field can replace guarded source; do not equate DOM to listing age automatically. |
| E10 | List photos and estate catalog images | `photos` / default `PHOTOS` | None | Three hardcoded Unsplash assets in ListingCard | MOCKED | Marked “Imagem ilustrativa”; actual photo URL/media ownership/source metadata has no current dedicated contract. |
| E11 | Card/compare area | `area_m2` | List adapter | OLD-P `metrics.area_m2`; EST `area_m2` | AVAILABLE_NOT_CONNECTED | Value is returned by old API but dropped by list adapter; detail adapter maps it. |
| E12 | Compare bedrooms/bathrooms/parking | `bedrooms`, `bathrooms`, `parking_spaces` | List adapter | OLD-P `metrics.rooms/bathrooms/parking_spaces`; EST `rooms/bathrooms/parking_spaces` | AVAILABLE_NOT_CONNECTED | All three dropped from list objects. Detail mapping is separate. |
| E13 | Compare age | `property_age` | List adapter | OLD-P `age`; EST `age_years` | AVAILABLE_NOT_CONNECTED | Dropped by list adapter although detail maps it. |
| E14 | Detail structural facts | `area_m2`, `bedrooms`, `bathrooms`, `parking_spaces`, `property_age` | `getProperty` → detail adapter | OLD-P metrics/age; direct counterparts in EST | WRONG_PROVIDER | Old mapping is internally present but still depends on guarded non-tenant source. |
| E15 | Active/sold/off-market label/filter | `status` | Adapter literal `Unavailable`; detail local null | EST `status`: `active`, `sold`, `off_market`, `archived` | AVAILABLE_NOT_CONNECTED | Production fact exists. UI options `Active/Sold/Off Market` require explicit mapping. |
| E16 | Last transaction fact | `last_sale_price`, `sale_price` | `getProperty` | OLD-P pricing; EST `last_sale_price`, `last_sale_date` | PARTIAL | EST has last-sale fact/date, no equivalent independent `sale_price` response member. Do not alias without target semantics. |
| E17 | Fresh detail AVM value | `valuation.estimated_price`, fallback `suggested_price` | POST `/properties/{id}/valuation` | OLD-P → `train.avm.predict_price`; ANA `valuation.estimated_price` already exposed | WRONG_PROVIDER | Replace source with ANA while preserving explicit failure rather than disguising a stale stored price as fresh output. |
| E18 | Fresh AVM premium BRL and percentage | `valuationDifference`, `valuationDeviationPct`, fallback React arithmetic | Same valuation POST | Old response `difference`, `difference_percent`; ANA equivalents | DUPLICATED | Detail reads difference_percent, else deviation*100; one domain calculation should serve list/detail/compare/portfolio. |
| E19 | AVM availability | `model_available`, valuation errors | Same POST | OLD-P success flag; ANA `timing.components[name=avm].state/code/message` | PARTIAL | A branch can fail while other analysis succeeds. New component status must not be treated as a zero estimate. |
| E20 | AVM uncertainty evidence | `valuation.lower_bound,upper_bound,interval_level,calibration_sample_count,out_of_time_coverage,uncertainty_status` | GET `/estates/{id}/analysis` → analysis client → PropertyDetail range/model disclosure | Legacy serving returns `uncertainty_status=not_calibrated`; promoted transaction artifact returns a conformal range | PARTIAL | This is calibrated interval evidence, not a probability of correctness. The UI omits the range until a production/promoted artifact is present. |
| E21 | Over/under/fair classification | `valuation_class`; badges/filter labels | Literal `Unavailable`; color thresholds elsewhere | No authoritative class field; asking and estimate exist | DERIVABLE | Needs one explicit threshold/uncertainty policy. Zero threshold in portfolio vs ±5% in UI are not equivalent. Do not invent a new band in this audit. |
| E22 | Comparable count | `comparable_count` null; detail placeholder | No comparable call | COMP `local_statistics.comparable_count` | AVAILABLE_NOT_CONNECTED | Count covers all eligible radius peers; it may exceed limited returned `comparables.length`. |
| E23 | Comparable table/cards in detail | Peer identity, facts, prices, distance | Placeholder, no call | COMP `comparables[]`: `id,title,property_type,asking_price,estimated_price,area_m2,price_per_m2,rooms,bathrooms,parking_spaces,days_on_market,city,area,distance_meters` | AVAILABLE_NOT_CONNECTED | Existing authorized endpoint. Distances null under city/area fallback; not fabricated zero-distance peers. |
| E24 | Comparable summary/support | Count, mean/median price, mean/median m², mean DOM | No call | COMP `local_statistics.*`, SQL count/avg/percentile | AVAILABLE_NOT_CONNECTED | Not yet part of rendered detail. Source is active same-tenant listings, not verified sales. |
| E25 | Detail 4L radar | `profile_scores.{luxury,leisure,location,leverage}` | Detail adapter `profile.* *20` | OLD-P stored `four_metric` 0–5; EST optional `attributes.profile/four_metric` used by AVM | PARTIAL | Display unit conversion is fine; provenance and normalized typed EST output are missing. Attribute storage does not guarantee computed scores. |
| E26 | Compare 4L radar/rows | `luxury_score`, `leisure_score`, `location_score`, `leverage_score` | List objects | Detail uses nested `profile_scores`, list has neither shape | AVAILABLE_NOT_CONNECTED | Naming/adapter mismatch on top of E25. Do not substitute inferred scores. |
| E27 | Property heat and local inventory | `market_heat`, inventory placeholder | Property adapter null / detail placeholder | ANA `location_metrics.metrics.inventory`; heat not published by GEO | PARTIAL | Inventory can be connected as **cell** inventory; property heat must not be invented from a missing aggregate. |
| E28 | Property liquidity | `liquidity_score`, `liquidity_horizon_days`, `liquidity_status` | GET `/analytics/estates`, `/estates/{id}`, estate analysis and pair comparison | Global aggregate Kaplan–Meier listing-survival artifact; property score is computed only after the tenant-authorized estate read | IMPLEMENTED_PENDING_PUBLICATION | `100 × [1 − S(a+T|X,M)/S(a|X,M)]`; `T` comes from the shared header selector. Null/status is intentional until migration 011 and an adequately supported offline artifact exist. |
| E29 | Stored expected growth | `expected_growth_pct` | `/properties*`, fraction ×100 | OLD-P `predictions.expected_growth` | PARTIAL | Stored prediction has no model/horizon/date lineage; production EST has no typed equivalent. |
| E30 | Detail forward growth | `forecast.expected_growth_pct` | POST `/forecast` with 180 days | FC would compute `(p50/current-1)*100`, but inference always raises | MISSING | Not a working forecast. It must not be conflated with old stored expected growth. |
| E31 | Forecast interval/series/context | `forecast[]`, `historical[]`, `interval`, `context` typed but not used as full chart | Same POST | FC schema `value,p10,p90`, horizon, macro context; hypothetical historical array always empty | PARTIAL | Declared response only; no serving inference, historical producer or connected interval view. |
| E32 | Catalog totals/paging/search | `page.total`, returned `items`, text/type/area filters | `/properties` limit100; `/properties/search` limit100 | OLD-P pagination/search; EST list supports only limit/offset, returns bare array | PARTIAL | No drop-in production total/filter/semantic-search contract. Local filtering/search can report incomplete first-page results. |
| E33 | Compare two chosen properties | `a`, `b`, 17 SPEC fields | Two IDs found in first loaded list | EST can retrieve both; COMP endpoint returns one subject plus nearby peers | DERIVABLE | Need a thin authorized pairwise composition, not blindly relabel a nearby-peer response as selected B. |
| E34 | Compare difference/winner/highlights | `diff`, `aWins`, `topDiffs`, relative differences | `compareRow` and React `useMemo` | Operands exist for supported fields; no backend pairwise result | DERIVABLE | Business direction/ranking and zero-denominator policy live in React. Highlights tagged AI are deterministic. |
| E35 | EstateAnalysisWorkspace selected facts | `selectedEstate.price`, m², estimate, gap, raw summary | List `/properties`, then client selection | Same OLD-P fields; ANA response unconsumed | WRONG_PROVIDER | Page name suggests analysis, but it displays listing facts and sends chat; it does not retrieve deterministic estate analysis. |
| E36 | Stored analysis history | Existing/repeated estate AI analysis | Local component text/state only | `analysis_results` table exists, no current read/write service/API | PARTIAL | Reopening an estate is not retrieval of a stored authorized AnalysisResult. |

### B. Overview and portfolio

Sources: [Overview][F-overview], [Portfolio][F-portfolio], [portfolio adapter][F-portfolio-api], [analytics helpers][F-analytics].

| ID | Frontend feature | Required information / frontend field | Current API / call | Backend provider → field / underlying calculation | Status | Contract finding |
| --- | --- | --- | --- | --- | --- | --- |
| P01 | Portfolio scope | Selected portfolio identifier/membership | No `/portfolios` call; no portfolio_id on analytics | EST portfolios; PORT requires authorized portfolio ID | AVAILABLE_NOT_CONNECTED | “Meu portfólio” currently resolves to legacy collection, not a selected portfolio. |
| P02 | Total value / animated StatCard | `portfolio_value`, `ps.totalValue` | GET `/portfolio/analytics` | OLD-PORT sum current prices; PORT `valuation_summary.portfolio_value` sum asking of active estates | WRONG_PROVIDER | This is asking-value total, not freshly revalued NAV. Scope is wrong before formulas are considered. |
| P03 | Active inventory | `active_listing_count`, `ps.activeCount` | Same | OLD-PORT length of all collection properties; PORT `active_estate_count` status-filtered | WRONG_PROVIDER | Legacy GET treats all records as active. |
| P04 | Sold count | `sold_listing_count` | Same | OLD-PORT passes an empty sold list; EST stores sold status | DERIVABLE | Current returned zero is not a measured sold inventory. Count authorized sold estates in backend. |
| P05 | Mean/median asking price | `average_asking_price`, `median_asking_price` | Same | PORT `pricing_statistics.average_asking_price/median_asking_price` | WRONG_PROVIDER | Production calculation already exposed, unconnected. |
| P06 | Mean price/m² | `average_price_per_m2` | Same | PORT `pricing_statistics.average_price_per_m2` over non-null stored values | WRONG_PROVIDER | Preserve statistic identity; not total price/total area unless explicitly defined. |
| P07 | Mean DOM | `average_dom_days`, `ps.avgDom` | Same | PORT `pricing_statistics.average_days_on_market` | WRONG_PROVIDER | Note `average_dom_days` ↔ `average_days_on_market` rename. |
| P08 | Mean listing age | `average_listing_age_days`, `listing_age_count` | `/portfolios/{id}/overview` → `portfolioToView` → Portfolio metric tab | PORT `pricing_statistics` computes `CURRENT_DATE − listed_since` for dated active listings | CONNECTED | Missing dates remain excluded and yield null when no dated active listing exists; DOM is never used as a fallback. |
| P09 | Mean price deviation | `average_price_gap`, `ps.avgDeviation` | Same; UI ×100 | PORT `valuation_summary.average_price_gap`, SQL mean per-estate `(asking-estimated)/estimated` | DUPLICATED | Unweighted average of ratios, not total-value gap. Needs consistent units and valuation snapshot provenance. |
| P10 | Above/below estimate lists and counts | `above_estimate[]`, `below_estimate[]` | Same | OLD-PORT builds `property_id,title,region,kind,asking_price,estimated_price,price_gap,dom_days,expected_growth`; EST facts available | DERIVABLE | Existing helper can be adapted to authorized portfolio records. PORT does not currently expose these lists. |
| P11 | Overview fair-value slice | `ps.fair`, pie count | Literal `[]` →0 | No backend class count | MOCKED | An empty hardcoded class is not evidence of zero fair-value estates. Other slices use OLD-PORT's >0/<0 rules. |
| P12 | Geographic concentration chart | `regional_concentration[].region/property_count/portfolio_value/share` | Legacy analytics | PORT `geographic_concentration[].city/area/estate_count/portfolio_value/share`; SQL region asking values / total | WRONG_PROVIDER | Existing safe replacement; preserve city+area instead of merging identical area names across cities. |
| P13 | Top-two region concentration | `topConcentration` / `top2` | Independently computed in Overview and Portfolio | Sum of first two sorted concentration shares | DUPLICATED | Computed metric and risk threshold belong with PORT; chart rounding belongs to UI. |
| P14 | Type distribution pie | `property_type_mix[].kind/property_count` | Legacy analytics | PORT `property_distribution[].property_type/estate_count/share` | WRONG_PROVIDER | Legacy mix `share` is value share; new `share` is **count share**. Frontend pie currently uses counts. Do not alias share silently. |
| P15 | Region growth ranking | `regional_performance[].average_expected_growth`; bestGrowthRegion | Legacy analytics | OLD-PORT mean stored growth; PORT only market exposure observations | PARTIAL | No production regional forecast provider. Legacy helper discards negative values through nonnegative numeric normalization. |
| P16 | Portfolio own-history liquidity / mean confidence | `liquidity_summary.score`, support/event counts / confidence display | `/portfolios/{id}/overview` → `portfolioToView` → Portfolio metric tab | Portfolio-only Kaplan–Meier evaluation of active + sold portfolio records; no provider for confidence | PARTIAL | Liquidity is available only with adequate portfolio-owned history and the chosen header horizon. Mean confidence remains unsupported and is not inferred from liquidity or an AVM interval. |
| P17 | Valuation total and market exposure | `estimated_value`, per-region market price/heat/date (currently not used) | No PORT call | PORT valuation summary and `market_exposure[]` from platform observations | AVAILABLE_NOT_CONNECTED | Asking and estimated totals are separate. Exposure may be null without published observations. |
| P18 | Overview market heat and supporting market summary | `ms.avgHeat,avgDom,medianM2,totalInventory,avgGrowth,avgVelocity` | `getMarketCells` → `computeMarketStats` | Client average/median/sum of cell metrics; GEO supports only subset | DUPLICATED | Equal-cell averaging and null→0 differ from estate-weighted aggregation; no shared canonical market summary. |
| P19 | Latest market price/m² | `latestPricePerM2` / misleading `median-m2` ID | Price history, else `ms.medianM2` | OLD-M mean price/m² per listing observation date; fallback median of cell means | WRONG_PROVIDER | Two different statistics under one value. Price-series mean must not silently become a cross-cell median. |
| P20 | Featured/top estates | `featured` sorted by market_heat, first3 | Loaded property list | Adapter always sets property heat null | WRONG_PROVIDER | All rankings tie at0; first three listings are not proven strongest opportunities. |
| P21 | Overview alert text / Portfolio risk summary | `alerts`, evidence strings | Client top2>50, heat>70, above/below lists and growth | No notification evaluation; deterministic ingredients partly available | DERIVABLE | Existing thresholds and statements need a single domain policy, not LLM-generated arithmetic. |
| P22 | Portfolio HHI / stagnation (unused outputs) | No active visualization for these response fields | Legacy `hhi`, `stagnation_rate` | OLD-PORT HHI helper and DOM>90 fraction | AVAILABLE_NOT_CONNECTED | HHI helper defaults to property-kind count concentration on 0–10000 scale, not automatically geographic risk. Adapt only if needed. |

### C. Market intelligence, heatmaps, history and filters

Sources: [market adapter][F-market], [MarketMap][F-map], [MarketIntelligence][F-intelligence], [MarketTrends][F-trends], [FiltersPanel][F-filters], [RegionPanel][F-region], [map renderers][F-map3d].

| ID | Frontend feature | Required information / frontend field | Current API / call | Backend provider → field / underlying calculation | Status | Contract finding |
| --- | --- | --- | --- | --- | --- | --- |
| M01 | H3 cell identity/geography | `id,h3_index,h3_resolution,city,neighborhood,label` | `/market/cells`, `/market/regions/{h3}` | GEO `cells[].h3_index,h3_resolution,city,area` | AVAILABLE_NOT_CONNECTED | `id` currently synthesized from h3; new cell has periods/version too. Select a single publication rather than assuming h3 alone is unique across snapshots. |
| M02 | Polygon and center | `boundary: [lat,lng][]`, `center:[lat,lng]` | Same | GEO `boundary/center` GeoJSON in longitude/latitude order | AVAILABLE_NOT_CONNECTED | Requires geometry adapter, not URL-only switch. Deck.gl explicitly reverses legacy tuples; avoid double reversal. |
| M03 | Heat color, height, tooltip `/100` | `market_heat` | Same, OLD-M missing calculator | GEO does not publish heat; legacy `radar.data_base.metrics.calculate_market_heat` exists but is not connected/compatible | PARTIAL | Helper requires portfolio sales and predictions, mutates records and calls `.reindex` on a NumPy array. It is not a functioning production heat provider. |
| M04 | Demand score | Former `demand_score` | Removed from active API/UI | None | REMOVED | It duplicated market heat without an independent authoritative producer. `market_heat` is the sole published market-demand indicator. |
| M05 | Mean cell price/m² | `average_price_m2`; region `avg_price_per_m2`, `average_price_per_m2` | Same | GEO `metrics.average_price_m2`, mean non-null stored per-estate m² price | AVAILABLE_NOT_CONNECTED | Three frontend aliases of one quantity. Publisher does not fill missing stored m² using area. |
| M06 | Cell price growth | `price_growth_pct` / region `price_growth` | Same | Old `price_growth` schema; no operational production growth producer | PARTIAL | Could be derived only from comparable dated snapshots with a defined window/statistic; current publisher replaces all platform heatmap rows. Current snapshot insufficient. |
| M07 | Cell active inventory | `inventory` | Same | GEO `metrics.inventory`, count active geocoded estates per H3/city/area group | AVAILABLE_NOT_CONNECTED | Only geocoded active source records counted; not entire database inventory. |
| M08 | Mean cell DOM | `average_dom_days`, region `avg_dom` | Same | GEO `metrics.average_dom_days` | AVAILABLE_NOT_CONNECTED | Null when no usable DOM; not zero days. |
| M09 | Sales velocity | `sales_velocity`, label `/mês` | Same | No current sales-window/count/time denominator pipeline | MISSING | Do not infer from active count or inverse DOM. Definition and dated sales source needed. |
| M10 | Regional liquidity | `liquidity_score` placeholder | No producer | No current score pipeline | MISSING | Old alternate backend can store arbitrary values; that is not a derivation/provider. |
| M11 | Cell query metadata | `source`, `calculation` | Legacy LIVE/MOCK and EXISTING_MODEL/UNAVAILABLE | GEO `scope,input_version,calculated_at,period_start,period_end`; no same fields | PARTIAL | Provenance vocabularies differ. Global aggregate is deterministic DATA, not automatically trained MODEL output. |
| M12 | Publication freshness and scope | Currently mostly undisplayed | No new heatmap call | GEO publication timestamp, version and dates; MKT source/date/unit | AVAILABLE_NOT_CONNECTED | Use to distinguish stale/empty/unavailable, not invented “live” labels. |
| M13 | Heat legend/strength label | `heatLabel`, BANDS 45/60/75 | React constants in format.js and MapHeatLegend | No provider-owned band policy | DUPLICATED | Color choices stay frontend; analytical names/thresholds need consistent policy metadata. Null must remain unavailable, not “Fraco”. |
| M14 | Header map cell/inventory totals | `cells.length`, sum `inventory` | Client reduction of returned cells | GEO current returned snapshot cells | DERIVABLE | Can summarize same published/filter scope; avoid summing multiple versions/resolutions or calling returned-cell count city-wide coverage. |
| M15 | Market bar chart | `barData[].label/value` for chosen metric | Cell/region queries | Same producers M03–M09 | PARTIAL | Chart has no independent source. Available subset: mean m², inventory, mean DOM. |
| M16 | Scatter heat vs price, bubble inventory | `x=market_heat,y=average_price_m2,z=inventory` | Cell query | Heat absent, other two published by GEO | PARTIAL | No valid full point without heat. Pixel/bubble-size scaling remains frontend. |
| M17 | Selected A/B geographic comparison table | Price,growth,DOM,inventory,velocity,heat for each | Two `/market/regions/{h3}` calls | GEO stored cells can supply subset; no dedicated new region endpoint | PARTIAL | Reuse fetched cells from one version or expose bounded cell lookup. Do not recompute private/global raw data per user. |
| M18 | Historical price/m² | `values[].date,value`; `points[].period,value`; chart `label` | GET `/metrics/price_m2/history?city&area` | OLD-M averages `pricing.listed_prices / square_metrage` per recorded date | WRONG_PROVIDER | Guarded global Chroma history. This is asking-price observations, not transaction-price index, monthly series or forecast. |
| M19 | Historical series metadata | `metric,unit,aggregation,source,frequency` | Same | OLD-M returns metric,unit,aggregation,points,source; adapter sets frequency=null | PARTIAL | Frequency cannot be asserted monthly; sample coverage and observation counts per point are not supplied. |
| M20 | H3 history comparison chart | `primaryHistory`, `comparisonHistory` | Price history by selected cell's **neighborhood**, not h3 | OLD-M supports only city/area | WRONG_PROVIDER | Two cells in one neighborhood receive same history. While primary cell loads, area can be undefined and fetch all-city history. |
| M21 | Last-three-month mini-chart | `KpiThreeMonthSeries`, `series` | Parent series; `.slice(-3)` | Last three finite records, regardless dates | WRONG_PROVIDER | Three observations are not three months. Existing date slicing helper does not make records monthly. |
| M22 | Inventory trend / inventory variation KPI | `active_listings` history | `useMarketAnalytics` → `MarketTrendMetrics` | Persisted global/city/area publication history | CONNECTED_FORWARD_ONLY | Historical points exist only after the offline publisher runs; the chart preserves publication gaps. |
| M23 | DOM trend | `dom` history | Same | Persisted global/city/area publication history | CONNECTED_FORWARD_ONLY | DOM uses the publication's explicit `days` unit, not an inferred listing-age replacement. |
| M24 | Velocity trend | `sales_velocity` history/KPI | Same | Persisted global/city/area publication history | CONNECTED_FORWARD_ONLY | Unit remains `sales/day`; missing sale support remains a gap rather than zero. |
| M25 | Non-price market histories | heat and price-growth series | `useMarketAnalytics`; heat uses the Overview metric tab | Persisted market publications | PARTIAL | `market_heat` is visible through its metric tab; growth has a provider but no dedicated historical presenter yet. `demand_score` is intentionally removed. |
| M26 | Portfolio compact histories | value,active listings,DOM,listing age,average gap | Portfolio API adapter → Portfolio metric tabs | Tenant-scoped `portfolio_metric_snapshots` | CONNECTED_FORWARD_ONLY | Each point is an actual event-coalesced observation; the client does not fill dates between observations. |
| M27 | Zoom chart and tooltip | `displaySeries[].label/value`, formatter,displayValue | Portfolio metric tab → existing zoom | Same persisted parent series | CONNECTED | Zoom remains presentation-only and uses the exact compact-card observations. |
| M28 | City and neighborhood filters | `CITIES`, neighborhoods, city defaults | Static São Paulo catalog; not read from backend | Distinct authorized EST locations and published GEO dimensions are derivable | DERIVABLE | Static reference options need not be mock measurements, but cannot claim complete dataset coverage. |
| M29 | Type/status filters | `PROPERTY_TYPES`, kind options, status options | Old kind filter; status often local/disabled | EST typed facts available; production list has no such filters yet | PARTIAL | Normalize `kind/property_type` and enum values; add scoped server filters instead of first-page-only filtering. |
| M30 | Heatmap price/type/heat filters | `priceMin,priceMax,propertyType,heatMin` | OLD-M query names incl `heat_min=heatMin/100` | GEO query only resolution,city,area,period bounds | PARTIAL | Stored aggregates lack property-type/price strata. Cannot honestly post-filter aggregate mean to emulate property-level range filtering. |
| M31 | Period selection | TopBar `timePeriod`; map `filters.period`; trend horizon12/24/36 | Independent local states; no universal request propagation | GEO accepts explicit dates; old map accepts period_days; histories take city/area only | PARTIAL | TopBar state is not consumed by analytics queries. “custom” lacks actual date bounds; trend horizon just slices existing history. |
| M32 | H3 resolution/region aggregation | `h3_resolution=9`; H3 selector disabled in intelligence | Constant9; new endpoint supports0–15 | GEO stored resolutions only | PARTIAL | Accepting query resolution does not create published results at that resolution. |
| M33 | Macroeconomic context | Forecast `context.indicators` (not a dedicated active chart) | Declared forecast context | Legacy MarketContext fields; FC passthrough | PARTIAL | Selic, real/mortgage rates, credit/concessions/delinquency, IPCA, income, unemployment, IBC-Br, SINAPI, FIPEZAP are optional stored inputs; no current ingestion/read producer found. FC cannot currently return successfully. |

### D. AI, metric tray, notifications and observability

Sources: [agent adapter][F-agent], [VoiceAgent][F-voice], [AiBrief][F-brief], [OpportunityNotifications][F-notifications], [AppContext][F-context], [AgentLog][F-log], [agent schemas][B-agent-schema].

| ID | Frontend feature | Required information / frontend field | Current API / call | Backend provider → field / underlying calculation | Status | Contract finding |
| --- | --- | --- | --- | --- | --- | --- |
| A01 | Chat answer | `reply.message.content` | POST `/agent/chat` | AI validated `interpretation.answer` | CONNECTED | Requires configured provider and evidence. No-data explanation is legitimate; an answer is not proof that every selected metric was fetched. |
| A02 | Explanation citations/caveats/next step | `interpretation.answer_evidence_keys,insights[].statement/evidence_keys/caveat,follow_up`; `sources,warnings,actions` | Same | AI structured response | AVAILABLE_NOT_CONNECTED | VoiceAgent only displays message text. Available metadata cannot be inferred from prose after being discarded. |
| A03 | One selected estate context | `selected_property.id` | `agentContextFromItems` first exact-type `Property` | AI resolves id → authorized EST → shared ANA fan-out | PARTIAL | Correct backend path exists, but current frontend estate IDs are legacy hashes. Client prices are correctly not accepted as verified evidence. |
| A04 | Two or many estates | comparison/tray `contextItems[]` | `.find(type==='Property')` | Backend context has one `estate_id`, not pair/list | PARTIAL | Both frontend and backend contract need bounded multi-ID composition for comparison. Last/second estate silently lost today. |
| A05 | Portfolio context | `type:'Portfolio',data:{analytics}`; portfolio charts | Adapter ignores Portfolio/Chart | AI supports explicit `portfolio_id`; PORT already exists | AVAILABLE_NOT_CONNECTED | Send authorized portfolio ID/scope, not raw client aggregate as trusted evidence. Current data object has no ID. |
| A06 | Metric selector/tray identity | `metric`, `metric_key`, display id/label | Canonical allowlist + METRIC_CONTEXT_KEY with five mappings | AI metric validation exists; selected metric tool uses OLD-M | PARTIAL | `portfolio-value`, many Portfolio/Trend IDs unmapped; labels like “Preço/m²” are not canonical keys. A visible tray item does not imply backend context. |
| A07 | Correct provider for portfolio KPI explanation | `active-listings`, `avg-dom`, `avm-deviation` from portfolio | Mapped to global market metric key | AI `get_market_metric` → OLD-M intelligence | WRONG_PROVIDER | Same metric name is insufficient: portfolio scope needs PORT, not city/global analytics. |
| A08 | Region/H3/filter context | `Region.data`, market_filters, period | Adapter sends region name/neighborhood; market_filters={} | `resolved_heatmap` sets city=region if no city supplied | WRONG_PROVIDER | Neighborhood becomes city; selected H3/period/type/price constraints lost. Existing backend whitelists resolution/city/area/date/max_cells only. |
| A09 | Overview brief | `briefPrompt`, returned text | AiBrief sends text without context IDs | AI evidence gathering finds no authorized selection | WRONG_PROVIDER | Client-calculated numbers inside question are untrusted text, not VERIFIED_EVIDENCE; current prompt cannot substitute for a portfolio/market tool call. |
| A10 | Saved charts/AI briefs/tray items | `savedInsights[].type,data`, context badge/count | AppContext only | No persisted insight service; adapter ignores unsupported types | PARTIAL | Local saved-selection state is legitimate, but “send all” does not currently resolve all entries. Lowercase `property` from featured items is also ignored. |
| A11 | Conversation continuation | `turns[]`, session_id | VoiceAgent does not retain/pass returned session_id; only new question sent | AI uses session_id for traces, does not load conversation messages | MISSING | Visible scrollback is local history, not persistent context or model memory. Tables exist but no conversation persistence/read integration. |
| A12 | Voice transcript/audio | useSpeech transcript, speech.speak(answer), persona | Browser speech recognition/synthesis | Browser API; backend supplies only answer text | CONNECTED | A valid client capability, not a missing backend speech provider. Rates/voice selection/orb state stay frontend. |
| A13 | Orb processing and context-arrival pulse | thinking,speaking,contextArrival,count | Promise/UI state | Request lifecycle only | CONNECTED | Visual cue, not progress percentage or analytics evidence; no backend motion calculations needed. |
| A14 | Session selection in AgentLog | `recentTrace.sessionId,query,createdAt` | AppContext; only unused IntelligenceAgent sets it | AI returns session_id | AVAILABLE_NOT_CONNECTED | Active VoiceAgent does not set recentTrace, so log normally has no selected session from that flow. |
| A15 | Trace events | `event_type,status,summary,tool,duration_ms` | GET `/agent/sessions/{id}/traces` | AI process-local tenant/session trace store | PARTIAL | Conditional client is wired but active session selection is absent; no durability/multi-worker shared history. |
| A16 | Trace timestamp, tokens, total latency | `created_at`, Tokens `—`, `totalMs` | Event list | Store never adds event timestamps; no token usage returned; interpretation event includes entire request duration | PARTIAL | Summing parallel tool times plus full interpretation-request time double counts; “Tempo registrado” is not wall-clock API latency. |
| A17 | Operational/failure badge | `status`, errors from regex | AgentLog client | Tool state `degraded`, warnings; trace calls optional | PARTIAL | Regex only matches error/fail, not degraded. Merely having session ID is not provider-health evidence. |
| A18 | Opportunity candidates/rank | `opportunities`, index+1 | GET `/portfolio/analytics`; React gap<0 sort ascending top3 | OLD-PORT below_estimate operands | WRONG_PROVIDER | No notification service, no AI ranking. Backend should own candidate policy over authorized portfolio data; no new metric proposed. |
| A19 | Bell count | `opportunities.length` | Same | Local top3 length | WRONG_PROVIDER | Not unread count, total opportunity count or durable delivery status. |
| A20 | Opportunity explanation | `aiQuery.data.message.content` | `/agent/chat`, candidate data.property_id | AI `resolved_estate_id` reads selected_property.id only | PARTIAL | None of these candidate IDs resolve, and all but first candidate already dropped. Ranking prompt also asks LLM to rank despite deterministic-evidence-only rules. |
| A21 | Notification lifecycle | Generated event,title/body,read_at,delivery,duplicates/retry | No notifications API/client | SQL notifications table only; worker no handlers | PARTIAL | No working evaluation/delivery/unread pipeline identified. Do not label a schema as implemented notification system. |
| A22 | Long-running job status/progress | `job_id,status,progress,result_reference,result,error`, timestamps/retries | No frontend jobs adapter/polling | JOB POST/GET already exposes these fields | AVAILABLE_NOT_CONNECTED | Status infrastructure exists, actual worker handlers do not; “RUNNING/SUCCEEDED” result cannot be promised for unregistered types. |

### E. Reports, forms, account and workspace information

Sources: [ReportBuilder][F-report], [DataManagement][F-data-page], [SavedSearches][F-saved], [PropertyNotes][F-notes], [desktopClient][F-desktop], [Settings][F-settings], [TeamManagement][F-team].

| ID | Frontend feature | Required information / frontend field | Current API / call | Backend provider → field / underlying calculation | Status | Contract finding |
| --- | --- | --- | --- | --- | --- | --- |
| W01 | Report KPI snapshot | avg price/m², avg DOM, inventory, velocity | Client reductions over useTupanData first100 and cells | PORT/GEO can supply scoped current subset | WRONG_PROVIDER | Selected report region does not filter all property KPIs; averages zero-impute missing values, inventory is returned-page count, all-regions velocity falls back to first region. |
| W02 | Report top properties | top6 by heat, title/location/price/estimate | Local list sort | Property heat null; not region-filtered | WRONG_PROVIDER | Output does not substantiate regional opportunity ranking. |
| W03 | Report price/inventory histories | price date/value, inventory series | price history by city/area; inventory placeholder | OLD-M price only | PARTIAL | Region applies to price history but not entire report. No inventory history source. |
| W04 | Report AI narrative | `aiSummary` | Text prompt with locally computed KPIs | AI with no scoped context hints | WRONG_PROVIDER | Same evidence problem as A09; not server-verified portfolio report. |
| W05 | PDF preview/export | Current DOM, date, title, selected sections | html2canvas/jsPDF client | Existing rendered results | CONNECTED | Export/rendering is presentation, stays frontend. Export does not validate missing or mis-scoped analytics. |
| W06 | Data-management estate table/create/delete | Form facts and table rows | `appClient.entities.Property.*` all unsupported | EST CRUD already registered | AVAILABLE_NOT_CONNECTED | Map form price→asking_price, bedrooms→rooms, neighborhood→area, age→age_years, status enum. Do not trust manual derived/model fields as fresh model output. |
| W07 | Form derived fields | `price_per_m2`, `price_deviation` | Math in submit/import mapping | Asking/area/estimated operands; domain price math exists in ANA/OLD-PORT | DUPLICATED | Client validation is fine; persisted canonical derived values should be backend-owned. |
| W08 | Manual 4L/heat/confidence-related inputs | luxury/leisure/location/leverage_score,market_heat; form state also confidence/class/count/liquidity | Unsupported create façade | EST arbitrary attributes can store, but no typed/verified model pipeline | PARTIAL | Manual entry is not calculated intelligence. Fields in state but not rendered still have no analytical provider. |
| W09 | Data-management regions table | name,city,market_heat,avg_price_per_m2,inventory | `MarketRegion.list` unsupported | GEO subset; old alternate server's region table differs | PARTIAL | Do not connect to alternate unscoped CRUD just because names look similar. |
| W10 | City reference table/count | `CITIES[].name,state,neighborhoods.length` | Constant | Local catalog, not database count | MOCKED | Table has DATA tag; listed “Áreas” is configured neighborhood count, not available ingested areas. |
| W11 | Bulk upload/extraction/import results | file_url,output[],success,invalid,duplicates,errors | UploadFile/ExtractData/bulkCreate unsupported | Guarded OLD-P `/properties/import`; no `import_excel` function in referenced ingestion module; no active import job handler | PARTIAL | No working equivalent of advertised CSV/XLS/XLSX/JSON end-to-end workflow. |
| W12 | Duplicate import count | `importStatus.duplicates` | Literal0 | No dedup-result provider for current UI flow | MOCKED | Zero cannot be reported as successful duplicate checking. |
| W13 | “Semantic” data-management search | `searchQ`, matched properties | Lowercase substring `.includes` on local list | OLD-P embedding search separate; pgvector schema no current main-app search pipeline | WRONG_PROVIDER | This particular view does not perform semantic search. Natural-language numeric constraints are not parsed by substring matching. |
| W14 | Saved-search definitions | `id,name,filters` | WS GET/POST/DELETE saved-searches | WS `saved_searches`, organization/user scoped | CONNECTED | Definition persistence matches the adapter; not the same as server-side result execution. |
| W15 | Saved-search results/count | `matched.length`, first6, filters status/type/price/neighborhood | React filter over useTupanData first100 | EST facts can support authorized query/count | DERIVABLE | Status currently `Unavailable`; page is not complete inventory. Saved filter names need mapping and server execution for truthful count. |
| W16 | Property note text and create | `n.content`; submit `{content,author_name}` | Adapter posts `{note:payload.note}`; response passed through | WS expects/returns `note` | PARTIAL | New note text becomes undefined → validation failure; returned text invisible because UI reads content. |
| W17 | Note author and date | `author_name`, `created_date` | Same GET | WS `user_id`, `created_at`; no author_name | PARTIAL | Need date mapping and authorized author display join; fallback “Corretor” is not real attribution. |
| W18 | Note realtime updates | `.subscribe` callback | No-op façade | No stream/polling source | MISSING | Manual create reload exists, but other users' updates are not a working realtime feature. |
| W19 | Account name/email/role | `user.full_name,email,role`; avatar initials | `/auth/session` and login/register | AUTH UserResponse / validated membership | CONNECTED | Initials and fallbacks are presentation, not fabricated user photo. |
| W20 | Team member list/role/remove | `id,full_name,email,role` | WS members GET/PATCH/DELETE | ControlPlaneService, authenticated admin authorization | CONNECTED | “Enterprise” is a UI label for admin role, not a subscription entitlement from billing. |
| W21 | Team invitation | email,role,invite success | `users.inviteUser` unsupported | No active main-app invitation route | MISSING | Role editing does not imply invitation/email delivery exists. |
| W22 | Profile name/brokerage edits | full_name,brokerage input | No submit/persistence | User/organization data partly exists; no matching edit contract | PARTIAL | Settings inputs do not save these changes. |
| W23 | Preferences and alerts | defaultPeriod,briefs,alerts,push,sound,autoRefresh,compact | Component useState only | No persistence or consumers for those settings | PARTIAL | Theme/local persona preferences are separate working client state. These toggles do not control actual notifications/refresh. |
| W24 | Model/source settings | Agent model,AVM engine,confidence threshold,context window,data source | Static explanatory strings | Backend config/artifact metadata partly exists, no safe capability endpoint | PARTIAL | Strings “Configurado pelo backend” are not actual model identity/health readings; confidence threshold not implemented. |
| W25 | Login/register/logout/session | email,password,full_name,organization_name / user response | v1 auth methods in desktop façade | AUTH v1 ControlPlaneService | CONNECTED | Supabase v2 exists separately; main data routes still use v1 principal resolution. Runtime login health not tested in this audit. |
| W26 | Social login,OTP,password recovery/reset | OAuth/OTP/reset outcome | Façade throws FEATURE_NOT_AVAILABLE | No matching main-app flow | MISSING | Existing buttons/forms do not constitute functional provider integration. |
| W27 | District boundaries | name,geojson | useMapBoundaries → WS, but hook has no active consumer | WS district_boundaries API | AVAILABLE_NOT_CONNECTED | Current maps use H3 polygons instead; do not mistake administrative boundaries for market cells. |
| W28 | Browser map configuration | API key, map style/camera | Public VITE_GOOGLE_MAPS_API_KEY; active map renderer config | Browser map service | CONNECTED | Presentation configuration; no reason to send pixel/camera calculations to backend. |
| W29 | Loading/error/empty states | pending,error code/message,empty arrays | React Query/local promise state and ApiError | APIs expose errors; ANA exposes per-component state | PARTIAL | Some paths suppress errors to empty arrays (notes), or default absent aggregates to0. Preserve unavailable vs empty vs measured0. |

## 5. Exact naming, units, scope and provenance hazards

| Concept | Existing names/contracts | Required normalization decision |
| --- | --- | --- |
| Estate identity | Legacy `property.id=property-<hash>`; ranking `property_id`; SQL `estate.id` UUID; UI context outer id vs data.id | One authorized estate UUID in data/context; presentation item IDs must not stand in for entity IDs. |
| Asking price | UI `price`; OLD-P `pricing.asking_price`; EST `asking_price`; legacy helper fallback to last sale | Preserve asking vs last-sale target. Never backfill one silently into the other. |
| Valuation | `suggested_price`, `predictions.suggested_price`, `estimated_price`, `pricing.avm_price` legacy fallback | AVM output owns fresh estimate; stored estimate must carry timestamp/model/source before being represented as current. |
| Price deviation | UI `price_deviation` percentage; old item `price_gap` fraction; PORT `average_price_gap` fraction; ANA `difference_percent` percentage | Define units explicitly in contract; compute once against same estimate. A mean ratio differs from aggregate ratio. |
| Price/m² | `price_per_m2`, `price_per_m2` nested metrics, `average_price_m2`, `average_price_per_m2`, `avg_price_per_m2`, `price_m2` metric key | Separate individual value, mean, median, total-weighted average and time-series observation. No statistical fallback under an unchanged label. |
| Age | `age`, `age_years`, `property_age`, `average_listing_age_days`, `days_on_market` | Building age, listing age and DOM are different quantities. |
| Geography | `neighborhood`, `area`, generic `region`, `city`, H3 index | Explicit typed scope; neighborhood is not city; H3 series is not area-wide series. |
| Mean DOM | `average_dom_days`, `average_days_on_market`, `avg_dom`, `dom` | Normalize field name, units=days, nulls and population. |
| 4L | backend 0–5 profile; detail nested 0–100; comparison expects flat fields | Unit conversion may stay in adapter; select a consistent shape and do not assert score provenance absent from EST. |
| Heat/growth normalization | market adapter multiplies values with abs≤1 by100; divides heat filter by100 | Guessing units by magnitude makes e.g.1 and1.01 discontinuous. Set contract unit per field. |
| Share | Legacy type mix monetary share; PORT type distribution count share; region shares monetary | Do not rename both to share without documenting denominator. |
| Freshness | `source:LIVE`, `calculation:EXISTING_MODEL`; platform publication dates/version; stored prediction no date | Publish/retain actual lineage. Static DATA/MODEL/AI badges are not lineage. |
| Time period | Header90d; map period_days; trend horizon24months; agent recognized90d/180d/12m/all | One explicit selection must propagate to query and evidence; 24/36month labels currently default to All available in agent context if passed. |
| Workspace note | UI content/author_name/created_date vs API note/user_id/created_at | Map note/date; join author safely. Author text supplied by client must not define identity. |
| Candidate training target | platform repository selects `price_brl`; parser requires `sale_price_brl` or `asking_price_brl` | Explicit target-kind mapping is missing at this seam; candidate CLI can exclude observations even when table rows exist. Not a live confidence provider. |

## 6. Fields without a valid backend provider: consolidated gap register

This includes blocked/miswired requirements as well as genuinely unsupported quantities. Repeated occurrences refer to matrix IDs rather than pretending that each chart is a different metric.

### 6.1 Already implemented/exposed but not connected correctly

- Authorized estate/portfolio UUID, estate status and portfolio membership; all EST structural/location/price fields (E01–E17, P01).
- Fresh estate valuation and component status; comparable list/count/statistics; per-estate location aggregate and platform market context (E17–E24, E27).
- Selected portfolio totals, count, pricing statistics, concentration, type distribution and market exposure (P02–P09, P12–P17).
- H3 GeoJSON, published inventory/mean price/mean m²/DOM and publication metadata (M01–M12). These are not heat/demand/velocity.
- Typed AI answer evidence, caveats, warnings, follow-up, returned session ID; bounded portfolio tool input; job state (A02–A08, A14–A16, A22).
- Note text/date and saved-search definitions; estate CRUD for DataManagement (W06, W14, W16–W17).

### 6.2 Derivable from existing facts, not yet authoritative backend outputs

- `price_deviation` and cross-screen gap consistency; above/below lists and counts; sold count; mean listing age where dates exist; top-two concentration; pairwise A/B differences and highlight policy (E08/E18/E21/E33/E34, P04/P08–P13).
- Filtered total counts, saved-search matching, dataset-backed filter options and consistently scoped report KPIs (E32, M28–M29, W01/W15).
- Opportunity ordering using the already existing gap criterion can be moved server-side; this does not make it AI ranking or calibrated investment advice (A18–A21).
- Mean/median/sum market summary over published inputs needs an explicitly chosen denominator and missingness policy. Do not claim a mean of cell averages equals an estate-weighted mean (P18/P19).

### 6.3 Partially supported, with a specific missing source or connection

- Property/region heat: a legacy helper exists but is not a viable current global publisher; no published field. Demand/velocity/liquidity do not acquire validity from this helper (M03–M10).
- Price history has a legacy listing-price producer only; inventory/DOM/portfolio histories require dated source states. Current platform refresh deletes/replaces platform heatmap rows and supplies today's period, not a retained series (M18–M26).
- Actual photos/media, normalized 4L lineage, stored prediction horizon/model/date, analysis-history retrieval, notification lifecycle, conversation persistence, semantic retrieval and bulk imports are not completed by arbitrary JSON/table storage (E10/E25/E29/E36, A11/A21, W08/W11/W13).
- Job table, claims, retries and status exist, but default handler registry is empty. Global heatmap/AVM preparation runs through explicit offline platform functions; no scheduler configuration proving automatic periodic execution was identified.
- `assess_data_quality` returns completeness, quality, observed_weight, missing_fields, critical_reasons, warnings and policy_version; conformal/comparable-support helpers remain evidence utilities. They do not produce a calibrated per-estate probability simply because a score is0–100.
- The transaction AVM writes a separate schema-2 candidate artifact and evaluation metadata. The runtime now consumes it only after explicit `promotion_status=production|promoted`, maps authorized EST fields to the versioned feature contract and returns validated interval metadata through ANA. The schema-1 legacy path remains the fallback while no promoted transaction artifact exists. The offline Campinas ITBI importer prepares verified, lineage-carrying `valuation_observations` from the curated workbook and existing local geocode cache; its default is preview-only, and neither its existence nor its migration implies that production has been loaded.
- Macro context fields can be stored and described, but no active ingestion/publisher or working forecast response supplies them. The `market_observations` table's generic metric field does not establish which metrics are actually produced.

### 6.4 Genuinely unsupported in the current serving application

- A probability-style `valuation_confidence` and portfolio mean confidence remain unsupported; the serving interval is the supported uncertainty output. Estate-level liquidity remains unavailable until its global artifact has adequate support, while portfolio-owned liquidity is available only when its own sale/listing history clears its explicit support threshold. Demand score and sales velocity (including monthly historical velocity) remain unsupported.
- A working forward-price forecast: current inference deliberately always raises; response schema and experimental offline optimizer are not a serving implementation.
- Real visitor telemetry backing the overview desktop/mobile chart.
- Realtime notes, actual team invitation delivery, social/OTP/reset flows through the current façade, saved notification preferences/push delivery, and full conversational memory.
- Agent-log token usage and timestamped durable trace history; actual model/version/capability settings response.

Historical values are not classified as DERIVABLE merely because a current aggregate exists. A definition, dated observations and a matching population are required.

## 7. Existing backend outputs needing exposure or frontend connection

### Already exposed: connect first, do not build competing services

1. EST list/detail and portfolios. Preserve response fields through a single adapter; add only missing filter/pagination contract rather than retrieving all tenant data to React.
2. ANA estate analysis and COMP response, including **partial component state**, not only valuation numbers.
3. PORT overview. Existing field groups cover the central portfolio metrics; legacy-specific above/below/growth/listing-age items require explicit parity decisions.
4. GEO `/market/heatmap`. Adapt GeoJSON and metric nesting, carry publication version/date, and expose only filters supported by the stored data.
5. AI structured interpretation metadata/session; JOB status. A job API is not evidence that a particular job type works.

### Code/data exists, but needs a small safe API/domain extension if the existing UI requires it

| Output | Existing source | Missing boundary |
| --- | --- | --- |
| Pairwise comparison differences/winners | Two authorized EST records; frontend existing SPEC policy | Bounded backend composition; do not substitute arbitrary nearest comparable for selected B |
| Above/below lists, sold count, top-two concentration, listing age | PORT/EST operands; some OLD-PORT helpers | Tenant/portfolio-filtered result fields and unified definitions |
| Filtered counts and filter catalogs | EST fields; GEO published dimensions | Validated filter/list/count or facet response |
| Quality/completeness and comparable support | `valuation_uncertainty.py` helpers | Verified feature/lineage adapter, policy version and non-probability response shape |
| Price history on production source | Legacy listed-price calculation; potential explicit dated observations | Real production observation ingestion + scoped historical repository/API; not a rename of snapshot field |
| Model identity/freshness | Serving artifact metadata/config | Safe public capability summary, excluding paths/secrets |
| Note author display | WS user_id and membership/user tables | Tenant-authorized join + response field |
| Agent latency summary | Actual measured request/branch times | Non-additive wall-clock summary; trace timestamp emission |

Do **not** list forecast quantiles, confidence probability, heat/demand/velocity, notification delivery or actual image URLs as ready-to-expose outputs: their required serving/production pipelines are missing.

## 8. Frontend business logic that should move or be normalized

| Location | Current calculation/policy | Responsible backend owner | Keep in frontend |
| --- | --- | --- | --- |
| properties adapter, PropertyDetail, DataManagement, PortfolioService/orchestrator | Asking vs estimate difference, percentage; price/m² | Estate analytical domain under ANA/AVM for valuation-derived results | Currency/unit formatting and input hints |
| `lib/analytics.computeMarketStats` | Mean heat/DOM/growth/velocity, median m², total inventory; null→0 | MKT/GEO published summary with declared population | Chart ordering/axis formatting after receiving results |
| Overview + Portfolio | Top-two concentration, alerts/risk rules; separate above/below/fair policies | PORT, with reusable policy; eventual notification evaluator | Showing returned findings and colors |
| Compare | Absolute/relative difference, fair/high/low winner, top-difference ranking | Bounded comparison domain using EST/ANA | Radar coordinates, visual arrangement and typography |
| ReportBuilder | Average m²/DOM, count and best listings over first100 | PORT or MKT depending explicit report scope | Selected sections, date labels, PDF capture |
| OpportunityNotifications | gap filtering/sort/top3 and count masquerading as notifications | Domain opportunity policy + notification lifecycle when implemented | Panel animation, visual list cap independent of true count |
| SavedSearches | Matches and count over partial loaded slice | Tenant query/repository using stored filters | Form editing and chips; local filter only if explicitly “loaded results” |
| DataManagement | Canonical m²/gap and import success/invalid/duplicate results | Estate/import domain | Basic required-field validation and upload UI |
| AgentLog | Sum of nested/concurrent durations, health inference | Observability response | Milliseconds→seconds display |
| Heat label/legend constants | Strength thresholds and descriptions duplicated | Provider-owned metric policy when heat actually exists | Color palette, opacity and extrusion height |

`computePortfolioStats` is a duplicate **unused** helper, not an active data source; do not migrate unused code as if the UI requires it. It uses different null/median/status rules from PORT/OLD-PORT. The mini-chart's `.slice(-3)` is a display selection bug: either the series must explicitly be monthly or date-aware selection must match its label. Pixel positions, zoom path/mask, metric-tab geometry, hover, scroll/blur, voice-sphere motion, colors, number formatting and unit conversions with a declared scale remain client responsibilities.

## 9. Duplicated/conflicting providers and authority decisions

| Overlap | Current conflict | Authoritative direction without a rewrite |
| --- | --- | --- |
| `PropertyService`, `TenantDataRepository`, nested `backend-fastapi` property CRUD | Chroma documents/hash IDs vs PostgreSQL estates/UUIDs vs another `properties` table | EST for private facts. Keep migration evidence separate; do not point current client to unscoped alternate CRUD. |
| Fresh AVM, persisted predictions, manual estimated_price, candidate model | Same “AVM” label can mean four distinct sources | Serving AVM for fresh values; explicit cached/persisted provenance; candidate remains offline until verified promotion. |
| Legacy `PortfolioService`, PORT SQL, `computePortfolioStats`, ReportBuilder | Different populations, missing-value rules, current-vs-last-sale fallback and active/sold treatment | PORT SQL/domain authority; adapt useful formulas there, not multiple React aggregators. |
| Legacy `MarketService`, `radar.metrics.calculate_market_heat`, global precompute, alternate market_regions CRUD | Missing imports, incompatible legacy algorithm, limited current published metrics, arbitrary stored scores | Platform publication + GEO/MKT reads. Validate/recover an existing algorithm before publishing more metrics; never claim numeric storage is computation. |
| Market series vs overview “median” vs cell average | Same label conceals different statistic and temporal/geographic scope | One declared metric definition per scope, no silent statistical fallback. |
| General comparator vs comparable selection vs similarity_expected_price | A/B difference is not spatial peer retrieval; legacy similarity helper is unconnected | COMP owns peer eligibility/statistics; thin pairwise composition owns two-user-selected comparison; AVM owns estimate. |
| AI market tool vs estate/portfolio tools | Portfolio metric keys go to legacy global market; selected data objects do not provide authority | Route by canonical identity **and scope**, then authorize and retrieve deterministic data. |
| Notifications vs overview alerts vs AI brief | Independent UI rules and misleading AI/monitor labels | One backend findings/opportunity policy; notification delivery is a separate lifecycle, AI only explains findings. |
| v1 AUTH vs Supabase v2 vs nested server auth | Different sessions/guards; desktop v1 client is still active | Keep current auth/data boundary consistent. This audit does not authorize a new auth migration or assume v2 parity. |
| VoiceAgent vs unused IntelligenceAgent | Active page lacks session/trace/evidence handling present in unmounted page | Reuse applicable response handling without swapping visual identity or routes. |

### Important non-authoritative code found

- `ceres/ui/tupan-intel-core/backend-fastapi/app/` contains another server: property/market-region CRUD, embeddings, auth and a generic LLM invoke route. It is not mounted by `backend/api/main.py` and is not targeted by the current `desktopClient` paths. Its region scores are user-supplied columns, not calculated metrics. Its LLM route returns `Local LLM stub: ...` when unconfigured. Do not classify these as current working domain outputs.
- `radar/data_base/metrics.py` contains spatial/HHI/similarity helpers. HHI is used by OLD-PORT; heat/similarity helpers are not the active COMP/GEO provider. `similarity_expected_price` references undefined `real_estate` when invoking the old menu helper; `calculate_market_heat` is not an API-compatible functioning publisher.
- `radar/agent/*`, legacy menu/ingestion and `ceres/ui/api/*.py` are separate legacy clients/agent paths, not the routed React agent API. Their presence does not satisfy missing tools in AuthorizedAiTools.
- `src/demo/localAppClient.js` is **not a mock** despite its filename: it only re-exports the remote desktop façade. Classify actual behavior rather than directory names.

## 10. Hardcoded/mocked/placeholder information inventory

| Location | Value/pattern | Assessment |
| --- | --- | --- |
| ChartAreaInteractive on overview | Fixed daily desktop/mobile counts, April–June2024; fixed reference date | MOCKED, explicitly labeled demonstration; genuinely mounted despite stale comment suggesting otherwise. |
| ListingCard | Three stock Unsplash images | MOCKED photos, explicitly illustrative; not real estate evidence. |
| Overview | `fair: []` and therefore count0 | MOCKED class result; not an unavailable-state representation. |
| DataManagement | Import duplicates always0; static city-area counts tagged DATA | MOCKED result/reference coverage; no measured import/corpus total. |
| Property adapter | confidence,comparable_count,heat,liquidity=null; status/class Unavailable | Honest placeholders, not mock numeric results; producers/mappings differ as documented. |
| MarketTrendMetrics | Inventory/DOM/velocity placeholders and empty histories | Missing data, not generated series. MODEL/AI badges do not prove a source. |
| Settings | “Configured by backend”, model artifact/status descriptions | Static copy, not health/model metadata. Preference toggles are isolated local state. |
| Overview/market helper | Empty regional list→all summary zeros; missing cells counted as0 in averages | Misleading default if treated as observed data; not a fake dataset but a semantic calculation defect. |
| MarketIntelligence | `Number(null)` in velocity formatting can yield0.00 | Missing-data→numeric-zero bug. |
| Compare/notification | AI badges/“priorizadas pela IA” attached to React rules | Wrong attribution, not LLM-derived ranking. |
| DataManagement “Semântica” | Case-insensitive substring search | Wrong capability label, not semantic retrieval. |
| Constants | São Paulo catalog, horizons, metric descriptions, sample questions, colors, animation timings | Not measured market outputs. Keep visual/static copy separate from data completeness claims. |

No hardcoded BRL estate-price dataset was found in the active routed analytics pages. Search examples such as “até2M” are input help, not recorded property prices. No placeholder AI prose is returned by the active AI service: it calls the configured provider or fails; the stub belongs to the separate nested server.

## 11. Smallest safe connection/normalization sequence

These are proposed changes only. No steps were implemented in this audit. No new metric, scoring formula, framework, service deployment, or broad architecture change is required to resolve the first group of failures.

1. **Lock down explicit data contracts and identities.** Add adapter/response fixture tests around existing EST/ANA/PORT/GEO schemas, UUIDs, price/gap units, nulls, dates, scope and partial outcomes. Identify an authorized portfolio explicitly. Retain the legacy guard. Do not conflate global published aggregates with private estate records.
2. **Connect estate facts and fix losses.** One EST adapter for list/detail/compare/catalog/data management; retain all structural fields and normalize enums. Add only necessary server filters/counts to existing repository/list route. Repair note/content/date mapping independently. No UI redesign.
3. **Connect deterministic analysis.** Use ANA for fresh AVM and COMP for actual peers/statistics. Compose two authorized IDs for A/B comparison and put existing arithmetic/policy in the domain layer. Preserve metric tabs, charts and zoom; they consume corrected data, not replacement layouts.
4. **Connect portfolio outputs.** Use PORT once per selected portfolio and reuse the result across summary/charts/brief contexts. Extend that existing service only for currently displayed derivable items, with explicit definitions and tests. Remove stale local alternative calculations only after parity, not during this audit.
5. **Connect global published market data.** GEO geometry/nested-metric adapter; current published fields/freshness only. Reconcile filter capabilities. Expose missing metrics as unavailable until an existing algorithm/source is verified and a platform publisher exists. Do not start private per-user global recomputation to fill gaps.
6. **Repair context and AI consumption.** Canonical typed estate/portfolio/metric/region/date hints; preserve bounded multi-selection. Route portfolio evidence to PORT. Display returned caveats/evidence/partial warnings and track actual session ID. Do not send React-calculated data as trusted evidence or ask the LLM to calculate absent statistics.
7. **Close lifecycle gaps only where the UI promises them.** Connect job status only to registered job types. Implement notification evaluation/read state, import results and conversation persistence using existing tables if those behaviors are retained. Do not mark an empty worker registry production-ready. Reuse one opportunity policy; no invented “hotness” model.
8. **Address genuine source gaps separately.** Historical observations/retention, real photos, working forecast inference and candidate AVM promotion/uncertainty need their own evidence and tests. Maintain unavailable state in the meantime. Demo visitors must remain labeled demonstration unless real telemetry is deliberately introduced.

### Acceptance checks for a later implementation

- Same estate UUID resolves consistently in list/detail/compare/notes/AI; another tenant's ID never supplies data.
- Header/report/market/portfolio filters are explicit in the request and result metadata, or identified as unsupported. Total counts do not describe only a hidden first100-record slice.
- Same asking/estimated inputs yield the same price/m²/gap wherever shown, with stated percentage/fraction units and valuation source/date.
- Portfolio value/active/sold/type/region totals agree on identical scope; zero and no observations are distinct.
- GEO rendering accepts GeoJSON correctly; only one intended version/period/resolution is counted. Changing filters cannot reveal raw private global estates.
- No property/location score, confidence or forecast is inferred from an absent field. Model artifacts and per-branch failures are visible.
- “Three months” is tested with daily, monthly, sparse and missing dates; mini-chart and zoom reference the same series definition.
- AI comparison receives both authorized estates; portfolio/context selection resolves backend tools; missing evidence results in an explicit limitation, not fabricated explanation.
- Note create/read round-trips text/author/date; network failures do not masquerade as empty notes.
- Notification badge semantics and persisted read state agree; retries do not duplicate events; job types shown as functional have actual handlers.
- Active VoiceAgent publishes session/trace metadata and renders warnings; total API latency is not a sum of parallel/nested timings.

## 12. Verification and limitations of this audit

- Inspected routed components, shared data consumers, frontend adapters/types, FastAPI registrations/schemas, provider implementations, SQL/repositories, migrations, worker registry and AVM/forecast code. Searched for hardcodes, mock/demo content, local business calculations, missing imports and unused providers.
- No live database reads, login attempts, external AI calls, background refresh, model training, mutation, migration or production data generation was performed. Existing table contents, installed migrations, enabled development flags and deployed artifact accuracy remain unverified.
- No application tests/build/typecheck were run: application code was not changed. Source-level contradictions above do not depend on a successful live login. Document validation checks reference existence and matrix/status structure, not runtime correctness.
- Exposing one field is not proof of its truth: generic JSON attributes, metric rows, user-entered estimates and labels all need provenance. This audit intentionally does not fill unsupported values or invent backend capabilities.

## 13. Backend → frontend output audit

### 13.1 Definitions and evidence boundary

The reverse audit traces provider → exact field → API → frontend service/type → component → presentation. Provider IDs refer to section 3. Availability and presentation are separate: a declared schema, nullable column or candidate experiment is not a working production output. Absent/schema-only signals are explicitly listed in section 14, not classified as ready-to-expose data.

| Reverse status | Meaning |
| --- | --- |
| DISPLAYED | Current consumer presents the output consistently. Gated legacy endpoints remain gated; no runtime certification implied. |
| AVAILABLE_NOT_EXPOSED | An implementation/helper produces this result for valid input, but no suitable HTTP output exists. Offline-only availability is explicitly noted. |
| EXPOSED_NOT_USED | Implemented main-app API result has no active frontend consumer. |
| USED_INCORRECTLY | Wrong meaning, scope, units, denominator or attribution in the consumer. |
| DUPLICATED | Equivalent output/calculation competes with another provider or redundant presentation. |
| HIDDEN | Response is fetched but useful fields are dropped/suppressed or only handled by an unmounted screen. |
| DEPRECATED | Legacy/compatibility or inactive path is not the intended production authority; no deletion performed. |
| NOT_USEFUL_FOR_UI | Keep raw operational/implementation details out of analytical screens; restricted diagnostics may use them. |

Each row specifies current presentation and best existing presenter. No new metric, confidence number, example price or interval was created. `DISPLAYED` describes code wiring, not successful live execution.

### 13.2 AVM and property value

Evidence: [serving model][B-serving], [AVM runtime][B-avm], [analysis schema][B-analysis-schema], [legacy property schema][B-property-schema], [PropertyDetail][F-detail].

| ID | Backend provider → exact output | API exposure | Frontend service/type → component | Current presentation | Status | Best presenter / condition |
| --- | --- | --- | --- | --- | --- | --- |
| R01 | AVM/ANA `valuation.estimated_price` | GET `/estates/{id}/analysis` | No analysis client; PropertyDetail calls OLD-P | Primary figure exists but uses another source | EXPOSED_NOT_USED | Existing primary valuation figure; no new KPI card |
| R02 | ANA `valuation.listed_price` | Same | No consumer; property price fetched separately | Asking price can come from a different snapshot | EXPOSED_NOT_USED | Existing asking-price row alongside estimate |
| R03 | ANA `valuation.difference,difference_percent` | Same | No client; React and old APIs calculate equivalents | Competing gap paths | DUPLICATED | Existing difference/deviation rows and compare columns, same backend valuation snapshot |
| R04 | ANA `valuation.price_per_m2,estimated_price_per_m2` | Same | No client; PropertyDetail uses old counterparts | Similar rows already exist | EXPOSED_NOT_USED | Existing asking/estimated m² pair, not another price card |
| R05 | AVM `inference_ms` | ANA valuation | None | None | NOT_USEFUL_FOR_UI | AgentLog diagnostics, never confidence or property quality |
| R06 | OLD-P `estimated_price,difference,difference_percent,estimated_price_per_m2` | Guarded POST `/properties/{id}/valuation` | getPropertyValuation → PropertyDetail | Primary estimate and secondary rows | DISPLAYED | Preserve hierarchy while changing authority; live availability unverified |
| R07 | OLD-P alias pairs current_price/listed_price, suggested_price/estimated_price, deviation/difference_percent | Same response | PropertyDetail explicit fields with fallback arithmetic | Repeated transport representations | DUPLICATED | Normalize one contract; never show aliases as distinct metrics |
| R08 | OLD-P `model_available` | Same, true on successful inference | PropertyDetail “Modelo” | Availability only | DISPLAYED | Keep availability meaning; migrate to ANA branch state, not model accuracy |
| R09 | OLD-P `predictions.suggested_price` | `/properties*` | properties adapter → Properties, ListingCard, Compare, EstateAnalysisWorkspace | “AVM” lacks persisted-vs-fresh distinction | USED_INCORRECTLY | Secondary stored estimate; require provenance before calling it current valuation |
| R10 | EST `estimated_price` | `/estates*`, analysis.estate | No EST adapter | None | EXPOSED_NOT_USED | Stored estimate, not proof current model ran; missing model/date lineage |
| R11 | EST `last_sale_price,last_sale_date` | `/estates*` | No client; OLD-P sale price reaches detail without date | Last sale row gated on valuation success | EXPOSED_NOT_USED | Existing factual row with date; sale fact should remain available if AVM fails |
| R12 | OLD-P `pricing.listed_prices[].date/price` | `/properties/{id}` | Preserved only in api_property; no estate-history consumer | Hidden asking-price movement | HIDDEN | Existing detail/zoom analytical area if safe source retained; not forecast or market index |
| R13 | OLD-P `predictions.expected_growth` | `/properties*` | expected_growth_pct; old portfolio consumers | Stored projection with no consistent horizon/version | USED_INCORRECTLY | Secondary stored projection with provenance; not measured market momentum |
| R14 | OLD-P `predictions.expected_dom_days` | `/properties*` | PropertyApiResponse declares; adapter drops | Not shown | HIDDEN | Potential observed-vs-expected DOM row only after forecast provenance verification |
| R15 | Serving metadata `model_type,target,target_transform,schema_version,training_rows,validation_rmse` plus promoted uncertainty metadata | Artifact metadata/load_model and promoted transaction runtime → ANA | PropertyDetail “Sobre o modelo” | Legacy metadata and calibrated metadata are conditionally disclosed | PARTIAL | Expose safe model identity/range evidence only; dataset metrics are not estate confidence |
| R16 | Artifact paths, feature columns/categories, best_params, random_state | Offline/metadata | None | None | NOT_USEFUL_FOR_UI | Keep raw model internals/paths server-side or restricted model review |
| R17 | AVM feature/artifact errors → ANA state/code/message | Analysis response | No ANA consumer | Coarse old errors, no direct partial-result handling | EXPOSED_NOT_USED | Inline actionable valuation warning; incompatibility is not a numerical OOD/confidence score |

Serving metadata has `schema_version`, not an immutable model release ID or `trained_at`. File modification time is not a substitute. Runtime error details.reason is not preserved as a separate ANA component field; component code/message are the actual exposed contract.

### 13.3 Estate facts and comparables

Evidence: [EST schema][B-estate], [COMP SQL][B-repo], [analysis schema][B-analysis-schema], [properties adapter][F-properties], [Compare][F-compare].

| ID | Backend provider → exact output | API exposure | Frontend service/type → component | Current presentation | Status | Best presenter / condition |
| --- | --- | --- | --- | --- | --- | --- |
| R18 | EST title,address,city,area,property_type,summary | `/estates*`, ANA estate | No client; current OLD-P adapter supplies equivalents | Listing/detail/catalog use old source | EXPOSED_NOT_USED | Existing title/location/facts, no extra container |
| R19 | EST area_m2,rooms,bathrooms,parking_spaces,age_years | Same | No client | List-backed compare loses facts | EXPOSED_NOT_USED | Existing facts and 17-field compare table |
| R20 | OLD-P metrics.area_m2/rooms/bathrooms/parking_spaces,age | `/properties*` | propertyToListItem drops; propertyToDetail maps | Detail shows, compare/card lose them | HIDDEN | Shared retained fact mapping, not an extra fetch to repair loss |
| R21 | EST status,days_on_market,listed_since,exclusive | `/estates*` | No client; old exclusive/on_sale_since also dropped | Status placeholder and legacy DOM | EXPOSED_NOT_USED | Existing status/DOM rows; dates/exclusivity as supporting facts |
| R22 | EST source_name,created_at,updated_at | Same | None | No record provenance/freshness | EXPOSED_NOT_USED | Small source/update line; DB edit date is not verified-source or valuation date |
| R23 | EST latitude,longitude,state,postal_code | Same | None | No EST-based location context | EXPOSED_NOT_USED | Existing detail/map context when useful; not coordinate KPI |
| R24 | EST id,external_id,portfolio_id,attributes | Same | No production adapter | None | NOT_USEFUL_FOR_UI | IDs for linking/auth; whitelist useful attributes, never dump JSON |
| R25 | OLD-P profile.luxury/leisure/location_/leverage | `/properties*` | Detail maps ×20; compare wants flat absent scores | Detail radar plus repeated score bars; compare blank | DUPLICATED | Preserve radar, use exact labels/tooltips; no third score display. Provenance still needed |
| R26 | COMP comparables[].id,title,property_type,city,area | `/estates/{id}/comparison` and `/analysis` | No adapter → PropertyDetail placeholder | Actual peers not visible | EXPOSED_NOT_USED | Existing comparable section as linked compact list/table |
| R27 | COMP peer asking_price,estimated_price,area_m2,price_per_m2,rooms,bathrooms,parking_spaces,days_on_market | Same | None | No peer evidence | EXPOSED_NOT_USED | Essential price/m², area, rooms, DOM columns; other facts in expanded row |
| R28 | COMP distance_meters | Same; PostGIS distance or null fallback | None | No location support | EXPOSED_NOT_USED | Table secondary column; distance is not similarity% |
| R29 | COMP local_statistics.comparable_count | Same; full eligible SQL set | UI comparable_count literal null | Support not visible | EXPOSED_NOT_USED | Small evidence indicator; eligible count can exceed limited visible rows |
| R30 | COMP local_statistics.average_asking_price,median_asking_price | Same | None | No local reference | EXPOSED_NOT_USED | Secondary reference near estimate; active asking peers, not verified transaction valuation |
| R31 | COMP local_statistics.average_price_per_m2,median_price_per_m2 | Same | None | No comparable m² benchmark | EXPOSED_NOT_USED | Explicit median reference in existing m² section; mean in tooltip/detail if useful |
| R32 | COMP local_statistics.average_days_on_market | Same | None | Property DOM lacks peer reference | EXPOSED_NOT_USED | Existing market context observed DOM vs peer average |
| R33 | COMP selection method: same tenant/type/radius or city+area fallback | SQL/query logic; no explicit method descriptor in response | None | Scope not described | AVAILABLE_NOT_EXPOSED | Support tooltip with method/radius; not all-market geographic coverage |
| R34 | OLD-P search distance,metadata,document | Guarded POST `/properties/search` | searchProperties retains only mapped property | Search evidence dropped | HIDDEN | Relevant search-match detail only; embedding distance is not comparable similarity/confidence |
| R35 | OLD-P create duplicate flag | Guarded POST `/properties` | DataManagement façade unsupported | No consumer | DEPRECATED | Do not reuse Chroma hash-identity duplicate policy as tenant estate identity |
| R36 | Legacy neighborhood_expected_price / similarity_expected_price | radar metrics helpers, no API | None | None | DEPRECATED | Old data shapes/broken search call; use COMP references, not a competing “AVM” value |

The backend does not return pairwise A/B winners or highlights; Compare calculates them in React. COMP retrieves a subject's nearby peers, not the user's independently selected B.

### 13.4 Portfolio outputs

Evidence: [PORT SQL][B-repo], [PORT schema][B-analysis-schema], [legacy portfolio service][B-portfolio] and [schema][B-portfolio-schema], [Portfolio][F-portfolio].

| ID | Backend provider → exact output | API exposure | Frontend service/type → component | Current presentation | Status | Best presenter / condition |
| --- | --- | --- | --- | --- | --- | --- |
| R37 | PORT portfolio.id,name,description | `/portfolios`, `/portfolios/{id}/overview` | No portfolio-list/overview client | Generic portfolio without actual scope | EXPOSED_NOT_USED | Existing heading/selector; scope prerequisite, not analytics card |
| R38 | PORT valuation_summary.portfolio_value | `/portfolios/{id}/overview` | api/portfolio uses legacy collection | Primary figure from wrong population | EXPOSED_NOT_USED | Existing StatCard, explicitly asking-value total |
| R39 | PORT valuation_summary.estimated_value | Same; SUM stored estimated_price | None | Estimated aggregate absent | EXPOSED_NOT_USED | Secondary stored estimated total if coverage known; COALESCE currently returns0 even when all estimates missing |
| R40 | PORT valuation_summary.active_estate_count | Same | None; old count used | Legacy all-record count | EXPOSED_NOT_USED | Existing active metric and list context |
| R41 | PORT valuation_summary.average_price_gap | Same | Legacy equivalent ×100, local alternatives | Multiple definitions/sources | DUPLICATED | Existing deviation metric; mean ratios not ratio of total values |
| R42 | PORT pricing_statistics.average_asking_price,median_asking_price | Same | None; old equivalents shown | Existing metric options | EXPOSED_NOT_USED | Existing metric tabs; do not force both into new cards |
| R43 | PORT pricing_statistics.average_price_per_m2,median_price_per_m2 | Same | None; old shape has no median m² | Only mean from legacy source | EXPOSED_NOT_USED | One explicit statistic in current tab; optional alternate in tooltip |
| R44 | PORT pricing_statistics.average_days_on_market | Same | No consumer; old average_dom_days | Existing DOM metric | EXPOSED_NOT_USED | Same metric with correct active-portfolio scope |
| R45 | PORT geographic_concentration[].city,area,estate_count,portfolio_value,share | Same | No client; legacy shape adapted into chart | Existing bars bound to global data | EXPOSED_NOT_USED | Existing composition bars with count/value/share tooltip and city+area label |
| R46 | PORT property_distribution[].property_type,estate_count,share | Same | No client; old type mix pie uses count | New count-share not used | EXPOSED_NOT_USED | Existing pie/legend; label count denominator, not monetary share |
| R47 | PORT market_exposure[].city,area,estate_count,average_price_m2,market_heat,latest_observed_on | Same; platform observation join | None | No dated exposure | EXPOSED_NOT_USED | Existing region table/composition tooltip, populated metrics only; nullable heat column isn't a producer |
| R48 | OLD-PORT regional_concentration,property_type_mix | Guarded `/portfolio/analytics` | PortfolioAnalytics → Overview and Portfolio | Repeated composition from legacy source | DUPLICATED | Reuse one PORT result for summary/detail, not more charts |
| R49 | OLD-PORT above_estimate[],below_estimate[] and their fields/counts | Same | Portfolio lists, overview pie/alerts, bell top3 | Stored gaps called opportunity/AI priority; fair slice hardcoded | USED_INCORRECTLY | Existing price-position lists with one deterministic definition, no claim every discount is a hot opportunity |
| R50 | OLD-PORT average_expected_growth; regional_performance price/m² and DOM | Same | Types declare; only best region growth text uses subset | Most details hidden; producer drops negative growth | HIDDEN | Existing regional table only after signed growth/provenance fixed; no extra cards |
| R51 | OLD-PORT stagnation_rate | Same; fraction of valid DOM>90 | Declared PortfolioAnalytics; no component reads | None | HIDDEN | Optional secondary risk row, explicit population/window, migrate scope first |
| R52 | OLD-PORT hhi | Same; property-kind count HHI0–10000 | Typed, unused | None | HIDDEN | Optional composition tooltip; existing distribution may suffice, not a new top-level risk score |
| R53 | OLD-PORT average_listing_age_days | Same; listing date else DOM | Portfolio KPI | Listing-age/DOM conflation possible | USED_INCORRECTLY | Existing secondary metric with correct date; remove semantic fallback after parity |
| R54 | OLD-PORT active_listing_count,sold_listing_count | Same; GET all active / sold=[] | Overview/Portfolio | Sold0 appears measured | USED_INCORRECTLY | Actual status-based scoped counts, not legacy zero |
| R55 | Portfolio target_commission | EST portfolio response | None | None | NOT_USEFUL_FOR_UI | Configuration/admin input if required, not valuation or realized performance metric |

### 13.5 Market, geography and historical outputs

Evidence: [global publisher][B-platform], [aggregation][B-heatmap], [SQL reader][B-repo], [market service][B-market], [market adapter][F-market].

| ID | Backend provider → exact output | API exposure | Frontend service/type → component | Current presentation | Status | Best presenter / condition |
| --- | --- | --- | --- | --- | --- | --- |
| R56 | GEO h3_index,h3_resolution,boundary,center | GET `/market/heatmap` | No new adapter; Map3D/Heatmap3D use old tuples | Appropriate renderer, wrong transport | EXPOSED_NOT_USED | Existing map layer with GeoJSON adapter; no new map page |
| R57 | GEO metrics.inventory | Same and ANA.location_metrics | No new consumer | Legacy tooltip or estate placeholder | EXPOSED_NOT_USED | Existing map/region context; active geocoded records in cell |
| R58 | GEO metrics.average_asking_price | Same | Not in legacy cell view shape | Useful aggregate absent | EXPOSED_NOT_USED | RegionPanel/market comparison secondary reference if useful |
| R59 | GEO metrics.average_price_m2 | Same | No new consumer; old alias chain | Existing m² visuals use legacy | EXPOSED_NOT_USED | Existing metric/table/chart; one statistic/unit |
| R60 | GEO metrics.average_dom_days | Same | No new consumer | Old visuals/placeholder | EXPOSED_NOT_USED | Existing region DOM row/table column |
| R61 | GEO city,area,period_start,period_end | Same | Old cells don't carry equivalent publication context | Filters not proven to match snapshot | EXPOSED_NOT_USED | Existing filter summary; today's snapshot isn't rolling90-day measurement |
| R62 | GEO calculated_at,input_version,scope | Same | None | No publication freshness | EXPOSED_NOT_USED | Small publication date/source disclosure; raw version technical, no extra card |
| R63 | PlatformHeatmapRefresh source_estate_count,aggregate_count,h3_resolution,period_start,period_end | Offline return, no HTTP | None | None | AVAILABLE_NOT_EXPOSED | Operations/DataManagement publication-status summary, not geographic coverage% |
| R64 | ANA location_metrics.h3_index,h3_resolution,metrics,period_start,period_end,calculated_at | Estate analysis/comparison | No client; AI tool can receive | Direct estate context absent | EXPOSED_NOT_USED | Existing “Contexto de mercado”, direct factual rows before AI prose |
| R65 | MKT market_context[].metric,value,unit,observed_on,source_name,scope | Estate analysis/comparison | No client; AI evidence uses | No direct dated market observations | EXPOSED_NOT_USED | Existing market-context rows, known metric labels/units + source/date; don't dump unknown JSON keys |
| R66 | OLD-M history points[].period/value | Guarded `/metrics/price_m2/history` | MetricHistoryResponse→series→Overview,TrendMetrics,MarketIntelligence,ReportBuilder,zoom | Labels imply monthly/H3/median beyond producer | USED_INCORRECTLY | Existing chart labeled asking-price/m² observations, actual dates/city/area, not invented monthly series |
| R67 | OLD-M history metric,unit,aggregation,source.kind/label/detail | Same | Adapter retains, consumers mostly read values | Provenance/statistic hidden | HIDDEN | Chart subtitle/tooltip, no new source panel |
| R68 | OLD-M H3 heat,demand,growth,velocity; overview/chart/catalog schemas | Guarded routes depend on absent modules | Current frontend expects fields | Error/unavailable rather than lost real output | DEPRECATED | Not ready-to-connect outputs; see section14 |
| R69 | Legacy heat intermediates spatial_heat_L,momentum_growth_G,market_heat and clustering helper | radar metrics, unconnected | None | None | DEPRECATED | Non-serving/incompatible helper, not published momentum |
| R70 | WS district boundary name,geojson | `/workspace/district-boundaries` | useMapBoundaries has no active imports | Not rendered | EXPOSED_NOT_USED | Optional existing-map boundary overlay if needed; no obligation to add layer |
| R71 | Generic SourceInfo.calculated_at | Optional schema; old portfolio/history leave unset | Some types retain | No reliable timestamp | NOT_USEFUL_FOR_UI | Don't invent timestamp; GEO has actual publication date, request time isn't freshness |

### 13.6 Quality, uncertainty, evaluation and local correction

These are **offline helpers/candidate results**, not production-estate API outputs. Code-only availability means results for valid supplied inputs, not verified production lineage/calibration. Evidence: [uncertainty helpers][B-quality], [validation metrics][B-validation], [candidate trainer][B-candidate].

| ID | Backend provider → exact output | API exposure | Frontend service/type → component | Current presentation | Status | Best presenter / condition |
| --- | --- | --- | --- | --- | --- | --- |
| R72 | assess_data_quality: completeness,quality (0–100) | ANA `data_quality` | PropertyDetail disclosure | Deterministic evidence fields are shown | DISPLAYED | Evidence-quality indicator, **not confidence probability** |
| R73 | Same helper missing_fields,critical_reasons,warnings,policy_version | ANA `data_quality` | PropertyDetail disclosure | Missing fields and reason codes are shown when present | DISPLAYED | Keep raw policy/reason values secondary to the valuation; do not call them confidence |
| R74 | Same helper observed_weight / internal weights | None | None | None | NOT_USEFUL_FOR_UI | Score implementation detail, not another displayed metric |
| R75 | fit_conformal: level,sample_count,nonconformity_quantile | Promoted transaction metadata → ANA valuation/diagnostics | PropertyDetail range and model disclosure | Nominal interval, calibration support and out-of-time coverage are shown conditionally | PARTIAL | q-hat remains internal; sample_count is not comparable_count |
| R76 | conformal_interval: lower_log,upper_log tuple | Promoted transaction runtime returns exponentiated BRL bounds | PropertyDetail range row | BRL interval is shown only with `uncertainty_status=calibrated` | DISPLAYED | Log bounds are never presented directly as currency |
| R77 | local_residual_correction: correction_log,lambda | No serving invocation/API | None | Not applied to current AVM | AVAILABLE_NOT_EXPOSED | Deferred adjustment explanation only if actually integrated; correction_log is not BRL/direct percent |
| R78 | Same helper effective_n,max_age_days,residual_dispersion,warnings | None | None | No local support info | AVAILABLE_NOT_EXPOSED | Deferred comparable-support caution tooltip; effective_n differs from raw count/calibration size |
| R79 | regression_metrics: sample_count,mae_brl,mdape,p90_ape,within_5/10/20 | Offline validation/candidate | None | None | AVAILABLE_NOT_EXPOSED | Model review details, not estate-confidence badge; within bands are fractions, mdape/p90 percentages |
| R80 | regression_metrics: median_ratio,cod,prd | Offline | None | None | NOT_USEFUL_FOR_UI | Restricted model diagnostics, not estate/portfolio tiles |
| R81 | Candidate training_rows,calibration_rows,test_rows,validation_metrics,out_of_time_metrics | Offline metadata | None | No deployed-model scorecard | AVAILABLE_NOT_EXPOSED | Model review only; don't describe candidate performance as serving model accuracy |
| R82 | Candidate uncertainty.method,calibration,out_of_time_coverage,out_of_time_median_width_pct,promotion_status | Offline | None | No serving range/promotion view | AVAILABLE_NOT_EXPOSED | Model evaluation; coverage is population-level, not probability one estimate is correct |
| R83 | Candidate feature_columns,categories,parameters,random_state,model/metadata paths | Offline | None | None | NOT_USEFUL_FOR_UI | Technical artifact internals, not frontend analytics |
| R84 | Training preparation eligible_observations,excluded_observations,promotion_status,reason,candidate_only | Offline candidate command | None | No readiness evidence in Settings | AVAILABLE_NOT_EXPOSED | DataManagement/model readiness diagnostics; fix price_brl target mapping before readiness claim |

Quality helper checks presence/numeric validity, lineage timing and freshness with fixed weights; it is not a complete OOD detector. Local correction requires eligible **out-of-fold residual records with historical cutoffs**. Today's nearest active listings cannot substitute for that input.

### 13.7 AI interpretation, reason codes, notifications and operational outputs

Evidence: [agent response schema][B-agent-schema], [agent routes][B-agent-routes], [AI orchestration][B-ai], [controlled tools][B-tools], [AI internal schema][B-ai-schema], [trace storage][B-traces], [VoiceAgent][F-voice], [AgentLog][F-log], [production-data/job routes][B-production-routes], [job response schema][B-estate], [worker][B-worker], [workspace][B-workspace]. All endpoint paths below use the main application's `/api/v1` prefix.

| ID | Backend provider → exact output | API exposure | Frontend service/type → component | Current presentation | Status | Best presenter / condition |
| --- | --- | --- | --- | --- | --- | --- |
| R85 | AI interpretation.answer → message.content | POST `/agent/chat` | sendAgentMessage → VoiceAgent; agent adapter → AiBrief/other prompts | Natural-language answer | DISPLAYED | Existing chat/brief as explicitly AI interpretation; not the only valuation/evidence display |
| R86 | AI interpretation.insights[].statement,evidence_keys,caveat | Same | Response returned; active VoiceAgent extracts only message.content | Structured statements/caveats lost | HIDDEN | Existing insight/answer disclosure, not a new card for every insight; preserve caveats beside claims |
| R87 | AI interpretation.answer_evidence_keys; sources[].label,detail | Same | Active VoiceAgent drops; non-routed IntelligenceAgent can populate recentTrace | No visible evidence trail from active agent | HIDDEN | Compact sources disclosure under answer and AgentLog; labels are tool names, not original document citations |
| R88 | AI warnings[] | Same | Active VoiceAgent drops; AgentLog depends on recentTrace from other page | Partial evidence/provider warnings absent | HIDDEN | Short caution beside affected answer, with details in existing log |
| R89 | AI interpretation.follow_up | Same | No active consumer | None | HIDDEN | Optional inline question only if helpful; not automatic backend action |
| R90 | AI session_id | Same | VoiceAgent neither retains returned session nor supplies it on next question | Local history appears continuous; trace/session linkage missing | HIDDEN | Retain internally for AgentLog/context continuity; no raw session badge. Does not create conversation memory by itself |
| R91 | AI actions[].label,tool | Same; labels describe successfully used tools | No active consumer | None | HIDDEN | Existing evidence/log details; these are tool-use records, **not executable action recommendations** |
| R92 | AuthorizedAiTools ToolResult.data | Internal chat tool result; chat route omits raw payload | None through chat; ANA/COMP/PORT/GEO already expose underlying facts | Facts can exist only inside AI evidence in this flow | AVAILABLE_NOT_EXPOSED | Prefer deterministic endpoints for existing analytical components; no need to expose unrestricted/raw tool JSON |
| R93 | ANA timing.components[].name,state,code,message | Estate comparison/analysis, portfolio overview, heatmap | No new analysis client | Component degradation/skipping not shown | EXPOSED_NOT_USED | Existing section-specific unavailable/warning state; keep successful branches visible, distinguish no data from failed branch |
| R94 | ANA timing.total_ms,components[].duration_ms | Same | None | None | NOT_USEFUL_FOR_UI | Diagnostics only, not a customer analytical metric or confidence proxy |
| R95 | AI traces events[].event_type,status,summary,tool,duration_ms,metadata | GET `/agent/sessions/{session_id}/traces` | getAgentTraces → AgentLog, enabled only with recentTrace.sessionId | Active VoiceAgent does not enable this chain | EXPOSED_NOT_USED | Existing AgentLog, safe summaries; optional created_at is not populated by current producer, don't invent timestamps |
| R96 | AI per-tool duration_ms plus enclosing interpretation-event duration_ms | Same | AgentLog sums all durations into totalMs | Parallel/nested spans counted as total elapsed | USED_INCORRECTLY | Show enclosing elapsed time separately from branch/tool times; summation is not request latency |
| R97 | JOB job_id,job_type,status,progress,created_at,started_at,completed_at,result_reference,error | POST `/jobs`; GET `/jobs/{job_id}` in production_data routes | No job client/status polling in analytical screens | No progress/result consumer | EXPOSED_NOT_USED | Existing import/long-operation state only when a handler actually exists; generic worker has no registered domain handlers |
| R98 | ErrorResponse code,message,request_id,details | Main API errors | client.js → most pages; PropertyNotes catches silently | Many errors shown, notes failure appears empty/successless | HIDDEN | Existing actionable error message + optional support ID; never dump arbitrary details or secrets |
| R99 | Tenant/user IDs, queue leases, payloads, attempts and worker coordination internals | Repository / subset in authorized job response | Mostly none | None | NOT_USEFUL_FOR_UI | Internal authorization/idempotency/retry mechanics; only user-relevant status in operations UI |
| R100 | WS PropertyNoteResponse.note,user_id,created_at | `/workspace/properties/{property_id}/notes` | desktopClient → PropertyNotes expects content,author_name,created_date | Body/date lost; author fallback; create sends content rather than adapter's note | USED_INCORRECTLY | Existing notes, normalized field mapping and authorized author display; user ID is not a display name |

The `notifications` table is **not** a produced notification feed: no notification API/evaluator/delivery handler was found. `OpportunityNotifications` reads legacy below-estimate listings and ranks them in React. Therefore there is no existing notification output to connect merely by changing a field name. Similarly, database `analysis_results`, `conversations` and messages tables do not establish an implemented analysis archive or conversation-history API. These gaps are recorded below rather than classified as usable outputs.

## 14. Existence gate for high-value information

This table prevents the reverse audit from treating an attractive schema, a nullable field or an offline experiment as a deployed analytical capability. **Do not create confidence, forecast, momentum or coverage figures to fill these gaps.**

| Requested information | What actually exists | What may be presented now / prerequisite |
| --- | --- | --- |
| AVM estimate | Serving point inference and ANA valuation | Direct primary figure after connecting authorized analysis; artifact/runtime still must be available |
| AVM confidence score | No calibrated per-estate probability in serving response | No “86% confidence” or high/medium/low category without a validated policy/provider; the promoted path exposes interval and coverage evidence, while completeness is not confidence |
| Lower/upper valuation bounds | Promoted transaction runtime exponentiates conformal bounds; legacy runtime remains point-only | Range is displayed only when `uncertainty_status=calibrated`; candidate artifacts and absent metadata remain explicit unavailable states |
| Time-series forecast quantiles | Forecast schemas describe P10/P50/P90; default analyze_tendency always rejects inference | Not a working prediction-range source, and not an estate AVM interval |
| Comparable count | local_statistics.comparable_count | Evidence indicator with eligible population; list length is the limited returned subset |
| Comparable similarity | No similarity score in ComparableEstate | Distance may be shown as distance; don't convert it or vector-search distance to a similarity percentage |
| Local residual adjustment | Offline OOF/cutoff-aware helper, not applied in serving | No “locally adjusted” claim until it actually affects the served estimate with lineage |
| Freshness | EST.updated_at, market observed_on, heatmap calculated_at/periods, legacy price-point dates | Distinct record edit / observation / aggregation / price-event dates. Neither API response time nor schema_version is freshness |
| Model version | Legacy schema metadata; promoted transaction `model_version` | Promoted model version is shown as bounded diagnostics; schema_version alone remains a format version, not a unique release or trained_at timestamp |
| Sample/support size | Comparable eligible count, heatmap inventory, offline effective_n, calibration/training/test counts | Different populations, never interchangeable. Aggregate inventory is not the valid-value count for every average |
| Geographic coverage | H3 geometry, cell resolution, aggregate count, source record count | Show available footprint, not a coverage percentage: no coverage denominator or representativeness estimate is produced |
| OOD / low-confidence indicator | Feature/category validation errors; quality/helper warning codes | Actionable validity/support warnings where integrated, not a statistical OOD detector or calibrated confidence score |
| Market momentum / heat / velocity / demand | Legacy missing-module paths; generic observations can store these names | No implemented current publication pipeline for those signals. Nullable market_heat/read support does not prove measured data exists |
| Neighborhood/reference price | COMP mean/median asking price/m², GEO cell means, published market observations | Explicit source/scope/statistic/date. Private tenant peers are not the universal neighborhood market; asking listings are not sales |
| Portfolio concentration | PORT region monetary shares and type count shares; old HHI | Existing composition visualization, explicit denominator. No need to add HHI if the chart already answers the question |
| Valuation deviation | ANA difference/difference_percent; PORT mean price-gap fraction; legacy equivalents | One backend formula per scope and agreed sign/units; no duplicate React formulas or inferred “AI opportunity” |
| Historical movement | Legacy per-estate listed_prices and per-observation-date asking-price/m² history | Exact dates and statistic, not automatically three months. No stored inventory/DOM/velocity history in the active new API |
| Macroeconomic context | Optional forecast context fields (rates, credit, inflation, income, employment, indices) | No verified current producer/serving result; no macro dashboard or narrative claiming live measurements |
| Reason codes | HTTP code, ANA branch code/message, offline quality/local-support warnings | Existing error/analytical caution presentation; machine code translated once, not a generic failure hiding partial success |
| Notifications | Storage schema plus generic jobs; bell is local legacy listing ranking | Requires real evaluation/feed lifecycle before presenting delivery, unread state or AI-detected opportunities |
| Optional legacy portfolio performance | lsp,active_listing_months,exclusive_retention,commission_retention,gci_per_sqm,clustering_coefficient declared but left at None by _analyse | Not unexposed calculated results; do not populate from placeholders or claim computation exists |
| Market overview/signals/catalog | API/type shapes referencing absent analytics-controller path | Contracts alone are not data producers; no ready output to reconnect |
| Estate images | No verified estate-photo provider in the traced estate contract; catalog uses explicitly illustrative stock images | Don't promote illustrative imagery to factual property evidence |

## 15. Smallest coherent presenter connections (specification, not applied changes)

Make these connections in dependency order. Reuse existing routes and presenters; no extra dashboard, universal “metric renderer”, or architecture rewrite is needed. Shared production data and tenant-owned estate/portfolio data retain their distinct scopes.

| Order | Existing destination | Authoritative outputs to bind | Minimal work / guardrails |
| --- | --- | --- | --- |
| 1 | api/properties adapter; Properties, PropertyDetail, Compare, EstateAnalysisWorkspace | EST facts/IDs/status/portfolio membership | Add compatible estate response normalization and authorized portfolio selection; don't pass legacy address hashes as estate UUIDs. Preserve UI routes, use correct ID mapping; don't disable tenant guards |
| 2 | PropertyDetail valuation and current metric tab/zoom | ANA valuation and component status | Use one authorized analysis snapshot for estimate, asking price, difference and m². Show useful partial results when optional branches fail. Keep geometry, metric tab and zoom motion unchanged; don't make AI success a prerequisite |
| 3 | Existing PropertyDetail comparables and market-context areas; Compare fact table | COMP peers, distance, count, median/mean references; MKT/GEO context dates | Replace placeholder with compact evidence table; label tenant/radius selection and list limit. Explicitly distinguish arbitrary selected-estate comparison from backend nearest-peer selection; don't invent similarity scores |
| 4 | Portfolio and Overview existing totals/composition/metric selectors | PORT valuation_summary,pricing_statistics,geographic_concentration,property_distribution,market_exposure | One portfolio-scoped response reused across charts. Select useful summary metrics; deeper facts in existing tooltips/table. Keep missing estimates separate from true zero before adding aggregate-estimate display |
| 5 | MarketMap, Map3D/Heatmap3D, RegionPanel, map tooltips/filter summary | GEO geometry and four published metrics,calculated_at,periods; MKT dated observations when populated | Adapt GeoJSON/metric keys once, preserve current map renderer. Publish only supported filter meanings; no private cross-tenant computation and no invented heat/momentum. Keep unavailable data explicit |
| 6 | Existing historical charts and their zoom view | Actual price observations + source/statistic/date | Preserve motion and presentation; correct record-vs-month and mean-vs-median semantics first. Request historical backend support separately, don't synthesize monthly inventory/DOM/forecast values |
| 7 | VoiceChatHistory/AiBrief and AgentLog | AI evidence_keys,caveats,warnings,sources,session_id; branch states | Keep prose separate from deterministic facts; compact source/caution disclosure. Wire session to existing trace view without claiming persisted memory. Don't turn actions into runnable controls |
| 8 | PropertyNotes and existing import/status area | WS note/date/author identity; JOB lifecycle only for implemented operations | Fix field normalization and silent error handling; no new “background analysis complete” state with an empty handler registry |
| Deferred | Existing valuation detail and Settings/model information | Quality/completeness, valid calibrated bounds, safe serving-model metadata, local support | Only after backend serving/lineage/parity verified. Use a range and small evidence disclosure, not a second AVM card or a made-up certainty percentage |

### 15.1 What to avoid adding or duplicating

- Do not render `message.content` and identical `interpretation.answer` twice; neither is independent evidence.
- Do not turn compatibility aliases (`current_price/listed_price`, `suggested_price/estimated_price`) into separate metrics.
- PropertyDetail repeats price/m² and 4L across figures/radar/bars. Keep one primary value and one useful comparison/detail; additional repeated KPI cards add no information.
- Overview and Portfolio may legitimately offer summary versus detail, but should share provider/scope/formula rather than separately recompute the same values.
- A detailed composition chart often communicates concentration better than another HHI badge. Keep HHI optional, defined and scoped.
- Missing “fair value” classification must not be a zero-valued slice. Below-estimate ranking is a price-position list, not a notification lifecycle or automatic risk-adjusted opportunity.
- Do not retain the hardcoded visitor chart as market evidence, and do not replace it with invented estate data. Removal/replacement was not performed by this audit.
- Don't add raw IDs, artifact paths, schema versions, hyperparameters, log-space residuals, queue internals or whole JSON objects to analytical screens.

## 16. Deterministic analytics before AI interpretation

The presentation contract should follow this order within existing surfaces:

1. **Fact/result:** authorized estate facts, served AVM point, explicit asking price, backend-calculated deviation, scoped portfolio totals or published geographic statistic.
2. **Evidence:** comparable count/list/distance, exact reference statistic, observed/calculated date and scope. Small inline labels, table columns and tooltips are preferable to additional cards.
3. **Limits:** missing data, degraded branches, incomplete support and actual uncertainty only when a valid producer exists. Empty/missing/failed/stale are different states; none should silently become zero.
4. **Interpretation:** optional AI explanation with caveats and evidence references. Its absence must not hide successful deterministic results. AI sources currently identify tools, not independently verified external citations.

No frontend business calculation is needed to obtain values already supplied by ANA/PORT/COMP/GEO. Unit conversion for display, currency/date formatting, chart coordinates, colors and animation geometry remain frontend concerns. Where a missing derived field is genuinely needed, define it once in the existing authoritative domain service rather than in both React and the LLM.

### Acceptance examples for future connections

- If AVM fails but peer/location queries succeed, show peers/context and an AVM-specific warning; never a fabricated estimate or empty whole page.
- If estimated_price exists without lineage, call it a stored estimate, not a freshly calculated model value. No implied accuracy from a green success state.
- If comparable_count is 100 and the response limit is 12, say 12 displayed / 100 eligible; do not label all 100 as inspected or give their absence a similarity score.
- If all portfolio estimates are missing, the SQL COALESCE zero must not become “portfolio estimated at R$0”. Establish coverage/missing semantics before exposing that total.
- If observed_on differs from calculated_at or updated_at, retain each meaning. A newly built heatmap may aggregate old observations.
- If the AI service is unavailable, existing deterministic analytical sections still remain useful. A raw tool payload is not a substitute for those sections.
- A forecast prediction interval, AVM valuation interval, data-quality score, OOF effective support, training sample count and model-validation error are distinct quantities; never relabel one as another.

## 17. Reverse-audit result and verification boundary

The reverse matrix inventories **100 output groups**, including explicit diagnostics/deprecated-code classifications: 41 EXPOSED_NOT_USED, 15 HIDDEN, 14 AVAILABLE_NOT_EXPOSED, 8 USED_INCORRECTLY, 5 DUPLICATED, 4 DEPRECATED, 3 DISPLAYED and 10 NOT_USEFUL_FOR_UI. These are grouped audit findings, not percentages of total frontend completeness or independently measured metrics. Grouping does not imply every output warrants a new visible element. Important results:

- **Unused but already exposed:** tenant estate/portfolio facts; ANA valuation/partial status; comparable peers/count/distance/local statistics; scoped portfolio statistics/distributions/exposure; platform heatmap geometry/four metrics/publication context; dated market observations; AI evidence/warnings/session links; generic job state.
- **Useful but not exposed or not serving:** selected safe model metadata, data-quality/reason output, comparison-selection provenance, platform publication readiness, calibrated candidate uncertainty and local-support output. Offline candidate capabilities require integration/validation, not just UI wiring.
- **Shown incorrectly or ambiguously:** stored estimates treated as current, duplicate deviation formulas/units, old global portfolio scope, stock price-gap lists called AI opportunities, date-history called months/median/H3, notes field mismatches, aggregate zero/missing ambiguity, summed concurrent/nested trace durations.
- **No valid current output to surface:** per-estate confidence probability, comparable similarity percentage, calibrated serving AVM bounds, production forecast, measured coverage percentage, operational momentum/demand/velocity pipeline, real notification feed, and persisted agent conversation retrieval.
- **Prefer reusing:** PropertyDetail valuation/comparables/context; Compare facts; Portfolio/Overview composition; RegionPanel/map tooltips; current chart/zoom; AiBrief/chat evidence disclosure; AgentLog. Preserve the distinctive metric tab and zoom, which do not cause the contract mismatches.

The historical audit rows were checked against registered route/provider/schema/adapter chains and source references. The implementation below adds compatible v1 connections and isolated fixtures; no database contents, credentials, remote model/provider, current training artifact or deployed production response were used. No training, precomputation, migrations or background-job behavior was invented. Runtime status is recorded in Section 18.1.

## 18. Bidirectional reconciliation execution state

### Stored-estimate lineage implementation (2026-09-15)

Migration 014 introduces `estates.estimate_provenance`, owned by a database
trigger. Future recorded values get a source, recording time and a versioned
fingerprint of the estate input snapshot. Existing estimates are not backfilled
with invented dates/model identities. Changed input marks the record
`inputs_changed`; removing the estimate clears provenance and replacing it
resets attribution. Client create/update schemas reject the provenance field.

The typed estate, comparable and portfolio-position responses carry this
metadata. Catalog, comparison, comparable table and portfolio positions use
the same disclosure. Portfolio totals additionally report lineage coverage
and changed-input counts. JSON extraction keeps reads compatible before the
migration. The input fingerprint identifies the recorded estate snapshot,
not a training dataset version; recording time is not a valuation date.
Current writes record supplied values and cannot assert an AVM model version.
Persisting a future AVM result with verified model identity remains separate.
Migration 014 is prepared locally and has not been applied to production.

Verification for this change: 29 focused backend tests passed; lint and
production build passed. The full backend suite ran 89 tests (84 passed,
3 skipped, 2 failed). The timing-sensitive AI test passed on isolated rerun;
the existing readiness test still expected 503 from an available database.
Frontend typecheck retains the existing unrelated component errors.
The SQL trigger has not been executed against PostgreSQL: the local Docker
daemon was unavailable. Its database behavior therefore still needs validation
before production application.

**Status: reconciled for the supported v1 information paths.** The two audits remain the source of truth for capabilities that are still unavailable; this section records the compatible connections that were implemented. Strategy A was selected: preserve existing v1 routes and add only compatible, tenant-authorized contracts. The retained [v1 characterization tests][B-contract-tests] remain in place.

### 18.1 Verification baseline

| Check | Actual command / result |
| --- | --- |
| Existing backend analysis/AI/tenant/valuation/platform tests | From ceres: `.\.venv-local\Scripts\python.exe -m unittest backend.tests.test_analysis_orchestrator backend.tests.test_ai_orchestrator backend.tests.test_tenant_repository backend.tests.test_valuation_contract backend.tests.test_platform_intelligence` — 21 passed |
| Retained characterization | `.\.venv-local\Scripts\python.exe -m unittest backend.tests.test_information_contract_characterization -v` — 8 passed |
| Frontend lint | From frontend: `npm.cmd run lint` — passed |
| Frontend typecheck | `npm.cmd run typecheck` — pre-existing failures in table/UI props, CSS custom-property typing, map coordinates, voice beams, auth facade calls, workspace entity types and other components; not claimed green |
| Existing frontend regression | `node --test tests/frontend-refinement.test.mjs` — could not start: `Cannot find module 'playwright'` from tests/frontend-review.mjs; no visual result claimed |
| Production build | Not run at the compatibility-decision stage; production code unchanged |

The deterministic characterization and reconciliation suites cover signed valuation percentages and m², missing versus zero, absence of fabricated confidence/bounds, comparable eligible count versus limited rows, distance versus similarity, optional AVM failure, required estate access before inference, heatmap GeoJSON/publication/null semantics, structured AI evidence transport, pair-comparison authorization, catalog field whitelisting and bounded SQL search. They use isolated fixtures, not production data or external providers.

Final verification supersedes the historical baseline rows above: the combined backend reconciliation suite passed 37 tests; the AVM serving/calibration additions are covered by the valuation contract suite; frontend lint passed; the frontend fixture regression passed 7 tests using the bundled Playwright runtime; and the production build passed. Frontend typecheck has no reconciliation syntax errors, but retains unrelated pre-existing component typing failures listed by the command.

The 2026-09-12 recheck additionally ran `python -m unittest discover -s
backend/tests -p 'test_*.py'`: 52 tests passed, 3 were skipped and one
pre-existing readiness assertion failed because the fixture database was
available when that test expected a 503. The focused AVM contract suite passed
8 tests. `npm run lint` and `npm run build` passed; the frontend typecheck
still reports the existing broad JSX/component typing backlog, with no error
from the calibrated AVM contract.

### 18.2 Completed bounded implementation

| Observed friction | Smallest planned transformation | Protecting verification | Navigation/ownership impact |
| --- | --- | --- | --- |
| Old property IDs/shapes and dropped facts | Normalize the existing EST/ANA contracts in the frontend API boundary; resolve filters/pagination explicitly | Contract fixtures plus routed list/detail/compare tests | Existing UI routes retained; authority EST/ANA |
| Duplicate deviations and ambiguous percentage units | Consume backend deviation once; centralize missing domain output in the existing provider only under the selected compatibility strategy | Signed/zero/null characterization plus new API/consumer assertions | No React/AI valuation formulas |
| Comparables and partial results not rendered | Bind the existing detail sections to COMP/MKT/GEO and branch state | Failure/empty/success fixture tests; authorized entity checks | No new page or artificial similarity/confidence score |
| Portfolio data lacks selected portfolio scope | Bind existing summaries/composition to PORT; define missing-estimate coverage before using totals | Portfolio/null/denominator fixtures and tenant tests | Existing charts/metric tab/zoom remain |
| Map consumes obsolete geometry/metric keys | One explicit GEO adapter for published fields, units, scope and supported filters | GeoJSON/null/zero fixture plus map interaction test | Current renderer retained; no new precomputation |
| AI warnings/evidence/session lost | Retain and present structured supporting metadata in existing chat/log | AI transport characterization plus rendered warning/evidence tests | AI explains deterministic facts; no duplicate analytical authority |
| Notification feed and temporal/uncertainty capabilities missing | Keep unsupported capabilities explicit; never replace them with mocks or unrelated metrics | Missing-provider assertions and canonical gap register | No invented notification lifecycle/forecast/confidence |

The clean-code skill requires choosing between preserving the current v1 API contract and adding a parallel v2 before production changes. Recommendation: **preserve v1**, because the tenant-scoped analysis endpoints already exist; reconnecting consumers and compatible additions can address most gaps without another API generation. The user's earlier Supabase-auth versioning decision does not automatically select a strategy for this separate analytics contract. Four auxiliary reference files linked by the skill are absent; repository tests and the skill's main compatibility rules were used instead.

The supported v1 paths are implemented and verified with isolated fixtures. Section 15 remains the historical audit/avoidance guidance; Section 18.3 is the current ownership map. The reverse-audit gaps listed above remain intentionally unsupported rather than mocked.

### 18.3 Implemented ownership and connections

| Feature | Provider → API → consumer | Contract decision |
| --- | --- | --- |
| Property analysis / AVM | ANA fan-out → analysis endpoint → PropertyDetail | Estimate, signed gap, m² values and branch warnings are backend-owned; legacy serving is explicitly not calibrated, while promoted transaction artifacts can provide a conformal range |
| Comparables | COMP branch in ANA → analysis response → PropertyDetail; pair endpoint → Compare | Count distinguishes eligible peers from displayed limit; versioned structural cosine similarity is backend-owned, nullable and distinct from geographic distance or confidence |
| Estate comparison | EST tenant reads + comparison_metrics → estate-pair endpoint → Compare | Differences and units are calculated once by backend; React formats only |
| Portfolio | PORT branches → portfolio overview endpoint → usePortfolioAnalytics, Portfolio, Overview | Selected portfolio is explicit; missing estimates are null; bounded rows are labeled separately from full counts |
| Heatmap / market map / estate heat | GEO platform aggregate repository → heatmap and estate analytics contracts → getMarketCells/estateToView → MarketMap, Overview, Properties, PropertyDetail, Compare | Heat is computed offline and normalized once; catalog uses a bounded page join, detail/pair reuse the location aggregate, and React only formats the nullable score |
| Market history and liquidity horizon | Published observations/H3 survival publications → published-metrics → useMarketAnalytics → Overview/MarketIntelligence | The shared top-bar horizon is in the request and cache key; Overview has a real liquidity metric/series consumer. Missing publication dates remain gaps, not reconstructed history |
| AI | Authorized deterministic tools → agent chat → VoiceAgent, AiEvidence, AgentLog | AI receives bounded authorized identifiers and evidence keys, not browser-calculated values |
| Notifications / notes | Existing workspace endpoints only → existing presenters | No notification lifecycle or unsupported global note feed is fabricated; unavailable providers remain visible as such |

The remaining reverse-audit gaps are intentional or data-dependent: probability-style AVM confidence, a validated production forecast artifact, notification generation/delivery, 4L lineage and persisted conversation retrieval. Comparable cosine similarity is connected. Heat, growth, velocity and liquidity have publication paths, but a displayed history or score still requires sufficient real source support and actual dated publications. A conformal interval is represented only when a reviewed transaction artifact is promoted; the current candidate is not served, and catalog estimates without persisted calibrated bounds remain `INSUFFICIENT_CONFIDENCE` rather than receiving a fabricated range.

### 18.4 Active-route closeout (2026-09-16)

| Invariant | Verified implementation state |
| --- | --- |
| Every displayed estate heat value has one source | `market_heat` comes only from the latest applicable global H3 aggregate, normalized by `published_cell_indicators`; invalid units/support return null |
| Overview liquidity follows the user's horizon | `timePeriod` → explicit days → `/market/published-metrics?liquidity_horizon_days=…` → horizon-keyed query → liquidity KPI/series |
| Valuation class is not recreated by React | Backend `classify_asking_price`; calibrated interval required for below/within/above, otherwise `INSUFFICIENT_CONFIDENCE` |
| Comparison and detail share market ownership | Both use tenant-authorized estates plus global aggregate-only location context; neither can read another tenant's estates |
| Forward-only history is honest | B13/F05/F06/F13/F14 show only persisted dated publications/snapshots; no backfill or interpolated calendar points |

Verification for this closeout: 51 focused backend contract tests passed, then
18 reconciliation/orchestrator tests passed after adding market-heat regression
coverage. The full backend suite finished with 96 passed, 3 skipped and the
pre-existing readiness-fixture failure: it expects HTTP 503 while the configured
database is reachable and `/ready` correctly returns HTTP 200. Frontend lint and
production build passed. Typecheck retains the
pre-existing broad JSX/component typing backlog and reports no error in the
files changed by this closeout. Browser regression tests could not start in the
current dependency installation because `playwright` is absent; no rendered
visual verification is claimed. The active `/overview` preview returned HTTP
200; native browser inspection was unavailable because the Windows UI sandbox
could not initialize.

## Source index

Frontend references are relative to this document; backend references point to the actual main application, not the nested alternative server.

[F-client]: ../ceres/ui/tupan-intel-core/src/api/client.js
[F-properties]: ../ceres/ui/tupan-intel-core/src/api/properties.js
[F-properties-page]: ../ceres/ui/tupan-intel-core/src/pages/Properties.jsx
[F-detail]: ../ceres/ui/tupan-intel-core/src/pages/PropertyDetail.jsx
[F-compare]: ../ceres/ui/tupan-intel-core/src/pages/Compare.jsx
[F-trends]: ../ceres/ui/tupan-intel-core/src/pages/MarketTrends.jsx
[F-listing]: ../ceres/ui/tupan-intel-core/src/components/tupan/ListingCard.jsx
[F-overview]: ../ceres/ui/tupan-intel-core/src/pages/Overview.jsx
[F-portfolio]: ../ceres/ui/tupan-intel-core/src/pages/Portfolio.jsx
[F-portfolio-api]: ../ceres/ui/tupan-intel-core/src/api/portfolio.js
[F-analytics]: ../ceres/ui/tupan-intel-core/src/lib/analytics.js
[F-market]: ../ceres/ui/tupan-intel-core/src/api/market.js
[F-map]: ../ceres/ui/tupan-intel-core/src/pages/MarketMap.jsx
[F-intelligence]: ../ceres/ui/tupan-intel-core/src/pages/MarketIntelligence.jsx
[F-filters]: ../ceres/ui/tupan-intel-core/src/components/tupan/FiltersPanel.jsx
[F-region]: ../ceres/ui/tupan-intel-core/src/components/tupan/RegionPanel.jsx
[F-map3d]: ../ceres/ui/tupan-intel-core/src/components/tupan/Map3D.jsx
[F-agent]: ../ceres/ui/tupan-intel-core/src/api/agent.js
[F-voice]: ../ceres/ui/tupan-intel-core/src/pages/VoiceAgent.jsx
[F-brief]: ../ceres/ui/tupan-intel-core/src/components/tupan/AiBrief.jsx
[F-notifications]: ../ceres/ui/tupan-intel-core/src/components/tupan/OpportunityNotifications.jsx
[F-context]: ../ceres/ui/tupan-intel-core/src/lib/AppContext.jsx
[F-log]: ../ceres/ui/tupan-intel-core/src/pages/AgentLog.jsx
[F-report]: ../ceres/ui/tupan-intel-core/src/pages/ReportBuilder.jsx
[F-data-page]: ../ceres/ui/tupan-intel-core/src/pages/DataManagement.jsx
[F-saved]: ../ceres/ui/tupan-intel-core/src/pages/SavedSearches.jsx
[F-notes]: ../ceres/ui/tupan-intel-core/src/components/tupan/PropertyNotes.jsx
[F-desktop]: ../ceres/ui/tupan-intel-core/src/api/desktopClient.js
[F-settings]: ../ceres/ui/tupan-intel-core/src/pages/Settings.jsx
[F-team]: ../ceres/ui/tupan-intel-core/src/pages/TeamManagement.jsx
[B-main]: ../ceres/backend/api/main.py
[B-repo]: ../ceres/backend/repositories/tenant_data.py
[B-estate]: ../ceres/backend/api/schemas/estate.py
[B-analysis]: ../ceres/backend/services/analysis_orchestrator.py
[B-analysis-routes]: ../ceres/backend/api/routes/analysis.py
[B-avm]: ../ceres/backend/services/avm_runtime.py
[B-platform]: ../ceres/backend/services/platform_intelligence.py
[B-platform-repo]: ../ceres/backend/repositories/platform_intelligence.py
[B-property]: ../ceres/backend/services/property.py
[B-market]: ../ceres/backend/services/market.py
[B-portfolio]: ../ceres/backend/services/portfolio.py
[B-forecast]: ../ceres/backend/services/forecast.py
[B-train-analytics]: ../ceres/train/analytics.py
[B-ai]: ../ceres/backend/services/ai/orchestrator.py
[B-tools]: ../ceres/backend/services/ai/tools/analysis_tools.py
[B-control]: ../ceres/backend/services/control_plane.py
[B-workspace]: ../ceres/backend/api/routes/workspace.py
[B-jobs]: ../ceres/backend/repositories/job_queue.py
[B-worker]: ../ceres/backend/worker.py
[B-candidate]: ../ceres/train/transaction_avm.py
[B-data]: ../ceres/train/valuation_data.py
[B-quality]: ../ceres/train/valuation_uncertainty.py
[B-agent-schema]: ../ceres/backend/api/schemas/agent.py
[B-analysis-schema]: ../ceres/backend/api/schemas/analysis.py
[B-property-schema]: ../ceres/backend/api/schemas/property.py
[B-portfolio-schema]: ../ceres/backend/api/schemas/portfolio.py
[B-serving]: ../ceres/train/avm.py
[B-validation]: ../ceres/train/valuation_validation.py
[B-heatmap]: ../ceres/backend/services/heatmap_precompute.py
[B-ai-schema]: ../ceres/backend/services/ai/schemas.py
[B-traces]: ../ceres/backend/services/ai/trace_store.py
[B-agent-routes]: ../ceres/backend/api/routes/agent.py
[B-production-routes]: ../ceres/backend/api/routes/production_data.py
[B-contract-tests]: ../ceres/backend/tests/test_information_contract_characterization.py
