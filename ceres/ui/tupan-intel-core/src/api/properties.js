import { api } from '@/api/client';

/** Backend EstateResponse; nullable observations stay null, never synthetic scores.
 * @typedef {object} EstateResponse
 * @property {string} id
 * @property {string | null} [portfolio_id]
 * @property {string | null} [title]
 * @property {string | null} [address]
 * @property {string | null} [city]
 * @property {string | null} [area]
 * @property {string | null} [property_type]
 * @property {string} [status]
 * @property {number | null} [asking_price]
 * @property {number | null} [estimated_price]
 * @property {{source:string,recorded_at:string,model_version:string|null,input_version:string,status:'recorded'|'inputs_changed'}|null} [estimate_provenance]
 * @property {number | null} [stored_price_deviation_pct] Signed percent, estimate denominator.
 * @property {'BELOW_ESTIMATED_RANGE'|'WITHIN_ESTIMATED_RANGE'|'ABOVE_ESTIMATED_RANGE'|'INSUFFICIENT_CONFIDENCE'|null} [valuation_class]
 * @property {number | null} [estimated_lower_bound]
 * @property {number | null} [estimated_upper_bound]
 * @property {number | null} [valuation_interval_level]
 * @property {number | null} [market_heat] Published H3 market-heat score for the estate location.
 * @property {number | null} [liquidity_score] Conditional probability of leaving the market, 0–100.
 * @property {number | null} [liquidity_horizon_days] Explicit horizon selected in the top bar.
 * @property {string | null} [liquidity_status]
 * @property {number | null} [price_per_m2]
 * @property {number | null} [area_m2]
 * @property {number | null} [rooms]
 * @property {number | null} [bathrooms]
 * @property {number | null} [parking_spaces]
 * @property {number | null} [age_years]
 * @property {number | null} [days_on_market]
 * @property {number | null} [last_sale_price]
 * @property {string | null} [last_sale_date]
 * @property {string | null} [summary]
 * @property {string} [updated_at]
 * @property {string | null} [source_name]
 * @property {number} [comparable_count] Count of authorized active peers using the canonical 2.5 km/city-area rule.
 */
export const PROPERTY_KIND_OPTIONS = [
  { value: 'casa de rua', label: 'Casa de rua' }, { value: 'casa de condomínio', label: 'Casa de condomínio' },
  { value: 'apartamento', label: 'Apartamento' }, { value: 'studio', label: 'Studio' },
  { value: 'cobertura', label: 'Cobertura' }, { value: 'sobrado', label: 'Sobrado' },
  { value: 'chácara', label: 'Chácara' }, { value: 'sítio', label: 'Sítio' },
];
/** @param {unknown} value */
const numberOrNull = value => typeof value === 'number' && Number.isFinite(value) ? value : null;

/** One view mapping shared by catalog, detail and comparison. No business formulas.
 * @param {EstateResponse} estate
 */
export function estateToView(estate) {
  return {
    id: estate.id, portfolio_id: estate.portfolio_id,
    title: estate.title || estate.address || 'Imóvel sem título',
    address: estate.address || '—', city: estate.city || '—', neighborhood: estate.area || '—',
    property_type: estate.property_type || null,
    price: numberOrNull(estate.asking_price), price_per_m2: numberOrNull(estate.price_per_m2),
    suggested_price: numberOrNull(estate.estimated_price),
    estimated_lower_bound: numberOrNull(estate.estimated_lower_bound),
    estimated_upper_bound: numberOrNull(estate.estimated_upper_bound),
    valuation_interval_level: numberOrNull(estate.valuation_interval_level),
    estimate_provenance: estate.estimate_provenance ?? null,
    price_deviation: numberOrNull(estate.stored_price_deviation_pct),
    days_on_market: numberOrNull(estate.days_on_market),
    bedrooms: numberOrNull(estate.rooms), bathrooms: numberOrNull(estate.bathrooms),
    parking_spaces: numberOrNull(estate.parking_spaces), area_m2: numberOrNull(estate.area_m2),
    property_age: numberOrNull(estate.age_years), last_sale_price: numberOrNull(estate.last_sale_price),
    last_sale_date: estate.last_sale_date, source_name: estate.source_name, updated_at: estate.updated_at,
    summary: estate.summary,
    status: ({ active: 'Active', sold: 'Sold', off_market: 'Off Market', archived: 'Archived' })[estate.status] || 'Unavailable',
    // These providers do not exist in the serving estate contract.
    valuation_class: estate.valuation_class || 'Unavailable', valuation_confidence: null,
    comparable_count: numberOrNull(estate.comparable_count),
    market_heat: numberOrNull(estate.market_heat),
    liquidity_score: numberOrNull(estate.liquidity_score),
    liquidity_horizon_days: numberOrNull(estate.liquidity_horizon_days),
    liquidity_status: estate.liquidity_status || null,
    expected_growth_pct: null, sale_price: null,
    luxury_score: null, leisure_score: null, location_score: null, leverage_score: null,
    profile_scores: { luxury: null, leisure: null, location: null, leverage: null },
    api_property: estate,
  };
}

/** @typedef {ReturnType<typeof estateToView>} PropertyListItem */
/** @typedef {PropertyListItem} PropertyDetail */
/** @typedef {{items: PropertyListItem[], page: {limit: number, offset: number, total: number}}} PropertyPage */

/** @param {{city?: string, area?: string, kind?: string, portfolio_id?: string, query?: string, liquidity_horizon_days?: number, limit?: number, offset?: number, signal?: AbortSignal}} [filters]
 * @returns {Promise<PropertyPage>}
 */
export async function getProperties({ signal, ...filters } = {}) {
  const response = await api.get('/analytics/estates', { query: { limit: 100, ...filters }, signal });
  return { ...response, items: response.items.map(estateToView) };
}

/** @param {string} propertyId
 * @param {{signal?: AbortSignal, liquidity_horizon_days?: number}} [options]
 */
export async function getProperty(propertyId, { signal, liquidity_horizon_days } = {}) {
  return estateToView(await api.get(`/estates/${encodeURIComponent(propertyId)}`, { query: { liquidity_horizon_days }, signal }));
}

/** Text search over authorized estate facts, not an embedding-similarity score.
 * @param {{query: string, city?: string, area?: string, kind?: string, liquidity_horizon_days?:number, limit?: number, signal?: AbortSignal}} filters
 */
export async function searchProperties({ query, ...filters }) {
  if (!query.trim()) throw new TypeError('A busca de imóveis exige um texto de consulta.');
  return getProperties({ ...filters, query: query.trim() });
}
