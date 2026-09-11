# Ceres frontend refinement — 11 September 2026

## Scope and review method

Refactored the existing frontend in place, following the supplied product brief
and Impeccable's layout/craft review. This is a composition and hierarchy pass,
not a replacement application or a new dashboard template.

The worktree already contained substantial changes. The protected-component
checks below compare against the start of this refinement, not against Git HEAD.
Unrelated edits were retained. No API contracts, authentication, routing,
backend services or dependencies were changed by this composition pass.

Rendered review uses the real components and routes with isolated API fixtures.
It does not authenticate as a customer or write production data. Synthetic
estates/history exist only in the test harness, never as application fallback data.

## Audit findings

1. Repeated equal-width metric grids gave all information the same priority.
2. Portfolio statistics occupied a long card grid below an isolated summary.
3. Property analysis scattered requested price, AVM and evidence into similar boxes.
4. Comparison duplicated property cards instead of making the matrix dominant.
5. Static analytical sections inherited the same glass/elevation as interactive cards.
6. Overview had a second page-specific palette that disagreed with the selected theme.
7. Texture, glow, tiny badges and container-relative type competed with analytical content.
8. Empty radar charts suggested evidence that the available data did not support.

## Changes applied

| Area | Composition and hierarchy |
| --- | --- |
| Overview | Two leading indicators followed by four supporting metrics; uses available workspace width. Four existing sections and their navigator remain. |
| Portfolio | Valuation summary beside compact statistic ledgers, followed by geographic/type concentration. All twelve original metric cards remain available in “Séries e indicadores,” including their history and context actions. |
| Market metrics | One dominant time-series chart with four supporting indicators; inventory and velocity charts form the secondary row. Removed redundant aliasing of the history value field. |
| Market intelligence | Primary/supporting analytical split, flat filter toolbar, consistent section rhythm. |
| Estate analysis / AVM | Property facts at left; estimated valuation and analytical evidence occupy the dominant right-hand region. Asking price remains visible when valuation is unavailable. No confidence interval is invented. |
| Comparison | A semantic, horizontally scrollable matrix with seventeen attributes, integrated property selectors and right-aligned values. Supporting charts/differences are secondary. Fixed an existing undefined difference formatting crash. |
| Listings / property table | Persistent basic facts, restrained object cards, flat toolbar and aligned numeric columns. Existing actions and image carousel remain. |
| Shared surfaces | Static Panel sections use spacing and a thin divider. Panels with metric/context interactions retain the specialized elevated host and tab. Ordinary context tags become quiet annotations. |

## Files changed in the composition pass

- src/index.css
- src/components/tupan/primitives.jsx
- src/components/tupan/StatCard.jsx
- src/components/tupan/ListingCard.jsx
- src/pages/Overview.jsx
- src/pages/Portfolio.jsx
- src/pages/MarketTrends.jsx
- src/pages/MarketIntelligence.jsx
- src/pages/Compare.jsx
- src/pages/PropertyDetail.jsx
- src/pages/Properties.jsx

Review/regression coverage: tests/frontend-review.mjs and
tests/frontend-refinement.test.mjs. Existing route-loading and voice-chat tests
were also run.

## Identity intentionally preserved

- MetricKnob.jsx, MetricKnob.css and KpiCard.css remain byte-for-byte unchanged
  from the beginning of this refinement. The 58px tab, selector, placement,
  context actions and distinctive shape remain.
- KpiCard's history and dimensional zoom code remain unchanged: original
  geometry, transition mask, 500ms movement, reveal and return.
- VoiceAgent, VoiceChatHistory, VoiceNav and SectionNav were not edited.
  Sphere, waves, chat fading, anchored navigation and menu motion remain.
- Five existing themes remain. Overview now inherits the selected theme
  instead of maintaining another private set of palette overrides.
- The quieter stationary application background retains a subtle aqua tone;
  the separate moving voice background is unaffected.
- Listing images/carousel, saved-search actions, filters, PDF export and
  analytical data flows remain. Useful metrics were regrouped, not deleted.

Protected SHA-256 values:

| File | SHA-256 |
| --- | --- |
| MetricKnob.jsx | 58B8A3A5E1335F77CA13EEB6E5C976E25EDB31E9682338798995CCABFC27733F |
| MetricKnob.css | 042C237ABD13E045FEB489098A36B21D06A8E7E6B10AF303A6242AFA18E7497F |
| KpiCard.css | A3857552BB7CD6BA8F8546EE0D0A3C5BD42ED1D2CEAA43EF763D214D82190829 |
| VoiceAgent.jsx | 4281ADB890EAD48F14715FDBF71A57DBC132DA3AADE8922A055B37D49D31D56D |

## Existing visual language, formalized

- Spacing: 4 / 8 / 12 / 16 / 24 / 32px; narrow and desktop gutters remain responsive.
- Type: existing system family; 15px page titles, 14–16px section/object titles,
  12–14px UI/body copy, 11–12px annotations and tabular analytical numbers.
  The main portfolio value uses a stable 36px size instead of container units.
- Radius: modest functional controls and 12px listing objects; no radius on
  static sections. Distinctive metric tabs, navigation capsules and zoom retain
  their original geometry.
- Surfaces: ambient page → flat analytical section → self-contained object or
  interactive metric surface → elevated overlay. No automatic card per section.
- Buttons: existing primary, secondary and tertiary hierarchy; retained focus
  affordances. Accent is used for actions, selected states and analytical series.
- Tables: left-aligned labels, right-aligned numeric columns, subtle separators;
  genuinely wide data scrolls locally rather than widening the whole page.
- Charts: existing series colors, labels and entry animations; no decorative
  glow or empty radar invented for absent evidence.
- Motion: preserved zoom, menu expansion and agent motion. Removed only the
  decorative global atmosphere movement and redundant listing hover scaling.

## Verification and limitations

- **Lint:** passed (npm run lint).
- **Production build:** passed (npm run build; 5,368 modules). Existing warnings
  remain for stale Browserslist data, two ambiguous Tailwind animation utilities,
  and large report/shared chunks.
- **Typecheck:** reports 90 diagnostics in pre-existing JavaScript/React wrapper inference,
  entity-adapter and optional-prop diagnostics. No checks were disabled. This
  frontend must not be described as typecheck-clean.
- **Impeccable detector:** no findings on the changed scope.
- **Browser regression suite:** latest sequential full run passed 11 of 12 tests.
  Account/notifications across five themes and two widths, responsive details,
  two-estate comparison, portfolio indicators/history, market horizon changes,
  full-screen loading and native chat scroll/blur passed.
- **Zoom test caveat:** the frame-sampling test passed in earlier runs but failed
  in the latest full run because it captured too few intermediate widths. An
  isolated retry timed out waiting for the card to stabilize before clicking.
  Browser timing is inconsistent in this environment; the suite is not fully
  green. The animation was not replaced, shortened or disabled to make a test pass.
  A final smoothness check on the user's normal desktop remains advisable.
- **Rendered review:** fourteen major desktop routes at 1280px, narrow layouts
  at 390px, selected comparison, market section, light theme and agent.
  No page exceptions in the broad desktop capture or final follow-up. Final market
  captures have document widths of exactly 1280px and 390px, with visible chart
  curves after animation. Empty/unavailable states
  are intentional fixtures, not evidence of live backend outages.
- **Preview:** http://127.0.0.1:4174/login returned HTTP 200 after the changes.
- **Not claimed:** production API health, authenticated customer data parity,
  real map-cell performance or AI-provider availability. These were not changed
  or exercised by the isolated visual review.

Screenshots are in the local temporary directories
ceres-frontend-composition-after and ceres-frontend-composition-final.
