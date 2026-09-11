import { api } from '@/api/client';

/**
 * @typedef {object} H3CellResponse
 * @property {string} h3_index
 * @property {number} h3_resolution
 * @property {string | null} [city]
 * @property {string | null} [neighborhood]
 * @property {[number, number] | null} [center]
 * @property {Array<[number, number]>} boundary
 * @property {number | null} [market_heat]
 * @property {number | null} [demand_score]
 * @property {number | null} [average_price_m2]
 * @property {number | null} [price_growth]
 * @property {number} inventory
 * @property {number | null} [average_dom_days]
 * @property {number | null} [sales_velocity]
 * @property {'EXISTING_MODEL' | 'UNAVAILABLE'} calculation
 * @property {'LIVE' | 'MOCK'} source
 */

/**
 * @typedef {H3CellResponse & {
 *   id: string,
 *   label: string,
 *   market_heat: number | null,
 *   demand_score: number | null,
 *   price_growth_pct: number | null
 * }} MarketCell
 */

/** @param {unknown} value */
function numberOrNull(value) {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

/**
 * The H3 calculation returns normalized scores. Existing visual components
 * render scores on a 0–100 scale; this is a display-unit conversion only.
 *
 * @param {unknown} value
 */
function displayScore(value) {
  const number = numberOrNull(value);
  return number === null ? null : Math.abs(number) <= 1 ? number * 100 : number;
}

/** @param {unknown} value */
function displayPercent(value) {
  const number = numberOrNull(value);
  return number === null ? null : Math.abs(number) <= 1 ? number * 100 : number;
}

/**
 * @param {H3CellResponse} cell
 * @returns {MarketCell}
 */
export function marketCellToView(cell) {
  const shortIndex = cell.h3_index.slice(-6);
  return {
    ...cell,
    id: cell.h3_index,
    label: cell.neighborhood ? `${cell.neighborhood} · ${shortIndex}` : `H3 · ${shortIndex}`,
    market_heat: displayScore(cell.market_heat),
    demand_score: displayScore(cell.demand_score),
    price_growth_pct: displayPercent(cell.price_growth),
  };
}

/**
 * @typedef {object} MarketCellFilters
 * @property {string} [city]
 * @property {string} [neighborhood]
 * @property {string} [propertyKind]
 * @property {number} [periodDays]
 * @property {number} [h3Resolution]
 * @property {number} [priceMin]
 * @property {number} [priceMax]
 * @property {number} [heatMin]
 * @property {AbortSignal} [signal]
 */

/**
 * @param {MarketCellFilters} [filters]
 * @returns {Promise<{ source: object, filters: object, cells: MarketCell[] }>}
 */
export async function getMarketCells({
  city,
  neighborhood,
  propertyKind,
  periodDays,
  h3Resolution = 9,
  priceMin,
  priceMax,
  heatMin,
  signal,
} = {}) {
  const response = await api.get('/market/cells', {
    query: {
      city,
      neighborhood,
      property_kind: propertyKind,
      period_days: periodDays,
      h3_resolution: h3Resolution,
      price_min: priceMin,
      price_max: priceMax,
      // The UI's slider is a percentage representation of the API score.
      heat_min: heatMin == null ? undefined : heatMin / 100,
    },
    signal,
  });
  return { ...response, cells: response.cells.map(marketCellToView) };
}

/**
 * @param {string} h3Index
 * @param {MarketCellFilters} [filters]
 * @returns {Promise<{ cell: MarketCell, source: object }>}
 */
/**
 * @param {string} h3Index
 * @param {MarketCellFilters} [filters]
 */
export async function getMarketRegion(h3Index, { signal, ...filters } = {}) {
  const response = await getMarketRegionRaw(h3Index, { signal, ...filters });
  return { ...response, cell: marketCellToView(response.cell) };
}

/**
 * @param {string} h3Index
 * @param {MarketCellFilters} [filters]
 */
async function getMarketRegionRaw(h3Index, {
  city,
  neighborhood,
  propertyKind,
  periodDays,
  h3Resolution = 9,
  priceMin,
  priceMax,
  heatMin,
  signal,
} = {}) {
  return api.get(`/market/regions/${encodeURIComponent(h3Index)}`, {
    query: {
      city,
      neighborhood,
      property_kind: propertyKind,
      period_days: periodDays,
      h3_resolution: h3Resolution,
      price_min: priceMin,
      price_max: priceMax,
      heat_min: heatMin == null ? undefined : heatMin / 100,
    },
    signal,
  });
}

/**
 * @typedef {object} MetricHistoryValue
 * @property {string} date ISO calendar date (`YYYY-MM-DD`), never a timestamp.
 * @property {number | null} value
 */

/**
 * @typedef {object} MetricHistoryResponse
 * @property {string} metric
 * @property {string} unit
 * @property {string | null} frequency Frequency is absent from the current API contract.
 * @property {string} aggregation
 * @property {MetricHistoryValue[]} values
 * @property {object} source
 */

/** @param {unknown} value */
function toDateOnly(value) {
  return String(value ?? '').slice(0, 10);
}

/**
 * Formats a date-only market observation as a local calendar date. Constructing
 * the Date from numeric parts avoids UTC parsing and its off-by-one-day shifts.
 *
 * @param {string} date
 * @param {Intl.DateTimeFormatOptions} [options]
 */
export function formatMetricDate(date, options = { month: 'short', year: '2-digit' }) {
  const [year, month, day] = toDateOnly(date).split('-').map(Number);
  if (!year || !month || !day) return toDateOnly(date);
  return new Intl.DateTimeFormat('pt-BR', options).format(new Date(year, month - 1, day));
}

/**
 * Converts the API's `points[].period` contract into the shared frontend
 * `values[].date` representation used by chart components.
 * Historical support is currently limited by the backend to `price_m2`.
 *
 * @param {string} metric
 * @param {{ city?: string, area?: string, signal?: AbortSignal }} [filters]
 * @returns {Promise<MetricHistoryResponse>}
 */
export async function getMetricHistory(metric, { city, area, signal } = {}) {
  const response = await api.get(`/metrics/${encodeURIComponent(metric)}/history`, {
    query: { city, area },
    signal,
  });
  return {
    metric: response.metric,
    unit: response.unit,
    frequency: null,
    aggregation: response.aggregation,
    values: (response.points || []).map((point) => ({
      date: toDateOnly(point.period),
      value: numberOrNull(point.value),
    })),
    source: response.source,
  };
}

/**
 * @param {MetricHistoryResponse | undefined} history
 * @returns {Array<{ date: string, label: string, value: number }>}
 */
export function metricHistoryToChartSeries(history) {
  return (history?.values || [])
    .filter((point) => numberOrNull(point.value) !== null && /^\d{4}-\d{2}-\d{2}$/.test(point.date))
    .sort((left, right) => left.date.localeCompare(right.date))
    .map((point) => ({ date: point.date, label: formatMetricDate(point.date), value: point.value }));
}

/**
 * Limits an already-returned history to a calendar-month display window. This
 * does not recalculate or aggregate the metric; the API remains authoritative.
 *
 * @param {Array<{ date: string, label: string, value: number }>} series
 * @param {number} months
 */
export function limitMetricHistoryToMonths(series, months) {
  if (!Number.isInteger(months) || months <= 0) return series;
  const latest = series.at(-1);
  if (!latest) return [];
  const [latestYear, latestMonth] = latest.date.split('-').map(Number);
  const cutoff = new Date(latestYear, latestMonth - months, 1);
  return series.filter((point) => {
    const [year, month, day] = point.date.split('-').map(Number);
    return new Date(year, month - 1, day) >= cutoff;
  });
}

/** @param {'30d' | '60d' | '90d' | '6m' | '12m' | 'custom' | undefined} period */
export function periodToDays(period) {
  return ({ '30d': 30, '60d': 60, '90d': 90, '6m': 180, '12m': 365 })[period] || undefined;
}
