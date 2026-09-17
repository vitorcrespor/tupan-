import {api, ApiError} from '@/api/client';

/** Resolution choices that are useful for an interactive city-level map.
 * The publisher supports every valid H3 level (0–15); the UI intentionally
 * offers the four levels that retain legible, decision-useful coverage.
 */
export const H3_RESOLUTION_OPTIONS = [
  { value: 7, label: 'Ampla · H3 7' },
  { value: 8, label: 'Regional · H3 8' },
  { value: 9, label: 'Bairro · H3 9' },
  { value: 10, label: 'Detalhada · H3 10' },
];

/** @typedef {{h3_index:string,h3_resolution:number,city:string|null,area:string|null,boundary:{type:string,coordinates:number[][][]}|null,center:{type:string,coordinates:number[]}|null,metrics:Record<string,unknown>,indicators?:Record<string,number|null>,liquidity_details?:{score:number|null,status:string,horizon_days:number,observation_count:number|null,sale_event_count:number|null,model_version:string,as_of:string}|null,calculated_at:string,period_start:string,period_end:string,input_version:string,scope:string}} PublishedCell */
/** @param {unknown} value */
function numberOrNull(value) { return typeof value === 'number' && Number.isFinite(value) ? value : null; }

/** GeoJSON is lng/lat; Leaflet requires lat/lng. This is a visual transformation only.
 * @param {PublishedCell} cell
 */
export function marketCellToView(cell) {
  const coordinates = cell.boundary?.type === 'Polygon' ? cell.boundary.coordinates[0] : [];
  return {
    ...cell, id: cell.h3_index, neighborhood: cell.area,
    label: [cell.area, cell.city].filter(Boolean).join(', ') || `H3 · ${cell.h3_index}`,
    boundary: (coordinates || []).map(([lng,lat]) => [lat,lng]),
    center: cell.center?.type === 'Point' ? [cell.center.coordinates[1],cell.center.coordinates[0]] : null,
    inventory: numberOrNull(cell.metrics.inventory),
    average_price_m2: numberOrNull(cell.metrics.average_price_m2),
    average_asking_price: numberOrNull(cell.metrics.average_asking_price),
    average_dom_days: numberOrNull(cell.metrics.average_dom_days),
    market_heat: numberOrNull(cell.indicators?.market_heat),
    liquidity: numberOrNull(cell.indicators?.liquidity),
    liquidity_details: cell.liquidity_details || null,
    price_growth_pct: numberOrNull(cell.indicators?.price_growth),
    sales_velocity: numberOrNull(cell.indicators?.sales_velocity),
    dataset_kind: cell.metrics.dataset_kind === 'transactions' ? 'transactions' : 'listings',
    transaction_count: numberOrNull(cell.metrics.transaction_count),
    source_row_count: numberOrNull(cell.metrics.source_row_count),
    geocoded_row_count: numberOrNull(cell.metrics.geocoded_row_count),
    average_transaction_price: numberOrNull(cell.metrics.average_transaction_price),
    median_transaction_price: numberOrNull(cell.metrics.median_transaction_price),
    partial_coverage: cell.metrics.partial_coverage === true,
    calculation: 'PUBLISHED_AGGREGATE', source: 'LIVE',
  };
}

/** @param {{publishedOnly?:boolean,signal?:AbortSignal}} [options] */
export function getMarketRegions({publishedOnly = true, signal} = {}) {
  return api.get('/market/regions', {query:{published_only:publishedOnly}, signal});
}

/** @param {{city?:string, neighborhood?:string, h3Resolution?:number, liquidityHorizonDays?:number, signal?:AbortSignal, propertyKind?:string, periodDays?:number, priceMin?:number, priceMax?:number, heatMin?:number}} [filters] */
export async function getMarketCells({city, neighborhood, h3Resolution=9, liquidityHorizonDays, signal, ...unsupported} = {}) {
  if (!Number.isInteger(h3Resolution) || h3Resolution < 0 || h3Resolution > 15) {
    throw new ApiError('A resolução H3 deve estar entre 0 e 15.', {code:'INVALID_H3_RESOLUTION'});
  }
  if (Object.values(unsupported).some(value => value != null)) {
    throw new ApiError('Este agregado publicado aceita apenas cidade, bairro e resolução H3. Filtros de preço, tipo, aquecimento e período não estão disponíveis.', {code:'FILTER_NOT_SUPPORTED'});
  }
  const response = await api.get('/market/heatmap', {query:{city,area:neighborhood,h3_resolution:h3Resolution,liquidity_horizon_days:liquidityHorizonDays},signal});
  // Select the latest publication per cell for this snapshot, without aggregating values.
  const cells = [...new Map([...response.cells].reverse().map(cell => [cell.h3_index, cell])).values()];
  return {...response, source:{kind:'LIVE',label:'Agregação global publicada'}, filters:{city,neighborhood,h3Resolution,liquidityHorizonDays}, cells:cells.map(marketCellToView)};
}

export async function getMarketRegion(h3Index, filters = {}) {
  const response = await getMarketCells(filters);
  const cell = response.cells.find(item => item.h3_index === h3Index);
  if (!cell) throw new ApiError('A célula não está disponível neste recorte publicado.', {code:'NOT_FOUND',status:404});
  return {cell,source:response.source};
}

/**
 * @typedef {object} MetricHistoryValue
 * @property {string} date ISO calendar date (`YYYY-MM-DD`), never a timestamp.
 * @property {number | null} value
 * @property {string | null} [reason] Why the observation cannot be used, if known.
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
 * The backend returns only persisted publications for each supported metric;
 * no client-side aggregation or inferred points are added here.
 *
 * @param {string} metric
 * @param {{ city?: string, area?: string, signal?: AbortSignal }} [filters]
 * @returns {Promise<MetricHistoryResponse>}
 */
export async function getMetricHistory(metric, { city, area, signal } = {}) {
  const published = await getPublishedMarketMetrics({city, area, signal});
  return publishedMetricHistory(published, metric);
}

/** @typedef {{metric:string,unit:string,value:number|null,observed_on:string|null,source_name:string|null,status:'available'|'unavailable',reason:string|null,points:Array<{period:string,value:number|null,reason:string|null}>}} PublishedMetric */
/** @typedef {{scope:'platform',city:string|null,area:string|null,h3_index:string|null,aggregation:'published',metrics:PublishedMetric[]}} PublishedMarket */
/** @param {{city?:string,area?:string,h3Index?:string,liquidityHorizonDays?:number,signal?:AbortSignal}} [filters] @returns {Promise<PublishedMarket>} */
export function getPublishedMarketMetrics({city,area,h3Index,liquidityHorizonDays,signal} = {}) {
  return api.get('/market/published-metrics', {query:{city,area,h3_index:h3Index,liquidity_horizon_days:liquidityHorizonDays},signal});
}

/** @param {PublishedMarket|undefined} published @param {string} metric @returns {MetricHistoryResponse} */
export function publishedMetricHistory(published, metric) {
  const response = published?.metrics.find(item => item.metric === metric);
  return {
    metric,
    unit: response?.unit || '',
    frequency: null,
    aggregation: 'published',
    values: (response?.points || []).map((point) => ({
      date: toDateOnly(point.period),
      value: numberOrNull(point.value),
      reason: point.reason || null,
    })),
    source: {kind:'LIVE',label:response?.source_name || 'Sem observações publicadas',reason:response?.reason},
  };
}

/**
 * @param {MetricHistoryResponse | undefined} history
 * The explicit null points preserve a known publication gap. Recharts leaves
 * those gaps unconnected by default, rather than implying a measured trend.
 *
 * @returns {Array<{ date: string, label: string, value: number | null, reason: string | null }>}
 */
export function metricHistoryToChartSeries(history) {
  return (history?.values || [])
    .filter((point) => /^\d{4}-\d{2}-\d{2}$/.test(point.date))
    .sort((left, right) => left.date.localeCompare(right.date))
    .map((point) => ({
      date: point.date,
      label: formatMetricDate(point.date),
      value: numberOrNull(point.value),
      reason: point.reason || null,
    }));
}

/**
 * Limits an already-returned history to a calendar-month display window. This
 * does not recalculate or aggregate the metric; the API remains authoritative.
 *
 * @param {Array<{ date: string, label: string, value: number | null, reason?: string | null }>} series
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
