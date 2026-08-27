import { api } from '@/api/client';

/** Property kinds declared by the existing Python `radar.data_base.kind` enum. */
export const PROPERTY_KIND_OPTIONS = [
  { value: 'casa de rua', label: 'Casa de rua' },
  { value: 'casa de condomínio', label: 'Casa de condomínio' },
  { value: 'apartamento', label: 'Apartamento' },
  { value: 'studio', label: 'Studio' },
  { value: 'cobertura', label: 'Cobertura' },
  { value: 'sobrado', label: 'Sobrado' },
  { value: 'chácara', label: 'Chácara' },
  { value: 'sítio', label: 'Sítio' },
];

/**
 * @typedef {object} PropertyApiResponse
 * @property {string} id
 * @property {string | null} [kind]
 * @property {number | null} [dom_days]
 * @property {number | null} [age]
 * @property {string | null} [summary]
 * @property {{ city?: string | null, area?: string | null, address?: string | null, h3_index?: string | null } | null} [location]
 * @property {{ rooms?: number | null, bathrooms?: number | null, parking_spaces?: number | null, area_m2?: number | null, price_per_m2?: number | null } | null} [metrics]
 * @property {{ asking_price?: number | null, last_sale_price?: number | null, sale_price?: number | null } | null} [pricing]
 * @property {{ suggested_price?: number | null, expected_growth?: number | null, expected_dom_days?: number | null } | null} [predictions]
 * @property {{ luxury?: number | null, leisure?: number | null, location_?: number | null, leverage?: number | null } | null} [profile]
 */

/**
 * @typedef {object} PropertyListItem
 * @property {string} id
 * @property {string} title
 * @property {string} address
 * @property {string} city
 * @property {string} neighborhood
 * @property {string | null} property_type
 * @property {number | null} price
 * @property {number | null} price_per_m2
 * @property {number | null} suggested_price
 * @property {number | null} price_deviation
 * @property {number | null} days_on_market
 * @property {number | null} expected_growth_pct
 * @property {null} market_heat
 * @property {null} liquidity_score
 * @property {'Unavailable'} status
 * @property {'Unavailable'} valuation_class
 * @property {null} valuation_confidence
 * @property {null} comparable_count
 * @property {PropertyApiResponse} api_property
 */

/**
 * @typedef {PropertyListItem & {
 *   bedrooms: number | null,
 *   bathrooms: number | null,
 *   parking_spaces: number | null,
 *   area_m2: number | null,
 *   property_age: number | null,
 *   last_sale_price: number | null,
 *   sale_price: number | null,
 *   profile_scores: { luxury: number | null, leisure: number | null, location: number | null, leverage: number | null }
 * }} PropertyDetail
 */

/**
 * @typedef {object} PropertyValuationResponse
 * @property {string} property_id
 * @property {number} current_price
 * @property {number} suggested_price
 * @property {number | null} deviation
 * @property {number} listed_price
 * @property {number} estimated_price
 * @property {number} difference
 * @property {number | null} difference_percent
 * @property {number | null} price_per_m2
 * @property {number | null} estimated_price_per_m2
 * @property {boolean} model_available
 */

/** @param {unknown} value */
function numberOrNull(value) {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

/**
 * Adapts the API transport schema to the pre-existing table/detail view model.
 * Fields with no property endpoint equivalent intentionally remain null.
 *
 * @param {PropertyApiResponse} property
 * @returns {PropertyListItem}
 */
export function propertyToListItem(property) {
  const location = property.location || {};
  const metrics = property.metrics || {};
  const pricing = property.pricing || {};
  const predictions = property.predictions || {};
  const price = numberOrNull(pricing.asking_price);
  const suggestedPrice = numberOrNull(predictions.suggested_price);

  return {
    id: property.id,
    title: location.address || property.summary || 'Imóvel sem endereço',
    address: location.address || '—',
    city: location.city || '—',
    neighborhood: location.area || '—',
    property_type: property.kind || null,
    price,
    price_per_m2: numberOrNull(metrics.price_per_m2),
    suggested_price: suggestedPrice,
    price_deviation: price !== null && suggestedPrice !== null && suggestedPrice !== 0
      ? ((price - suggestedPrice) / suggestedPrice) * 100
      : null,
    days_on_market: numberOrNull(property.dom_days),
    expected_growth_pct: numberOrNull(predictions.expected_growth) === null
      ? null
      : /** @type {number} */ (predictions.expected_growth) * 100,
    market_heat: null,
    liquidity_score: null,
    status: 'Unavailable',
    valuation_class: 'Unavailable',
    valuation_confidence: null,
    comparable_count: null,
    api_property: property,
  };
}

/**
 * The four-metric domain model is stored on a 0–5 scale. The existing detail
 * controls display scores on a 0–100 scale, so this is a presentation-unit
 * conversion only.
 *
 * @param {unknown} value
 */
function profileScore(value) {
  const numericValue = numberOrNull(value);
  return numericValue === null ? null : numericValue * 20;
}

/**
 * @param {PropertyApiResponse} property
 * @returns {PropertyDetail}
 */
export function propertyToDetail(property) {
  const metrics = property.metrics || {};
  const pricing = property.pricing || {};
  const profile = property.profile || {};
  return {
    ...propertyToListItem(property),
    bedrooms: numberOrNull(metrics.rooms),
    bathrooms: numberOrNull(metrics.bathrooms),
    parking_spaces: numberOrNull(metrics.parking_spaces),
    area_m2: numberOrNull(metrics.area_m2),
    property_age: numberOrNull(property.age),
    last_sale_price: numberOrNull(pricing.last_sale_price),
    sale_price: numberOrNull(pricing.sale_price),
    profile_scores: {
      luxury: profileScore(profile.luxury),
      leisure: profileScore(profile.leisure),
      location: profileScore(profile.location_),
      leverage: profileScore(profile.leverage),
    },
  };
}

/**
 * @typedef {{ items: PropertyListItem[], page: { limit: number, offset: number, total: number } }} PropertyPage
 */

/**
 * @param {{ city?: string, area?: string, kind?: string, limit?: number, offset?: number, signal?: AbortSignal }} [filters]
 * @returns {Promise<PropertyPage>}
 */
export async function getProperties({ signal, ...filters } = {}) {
  const response = await api.get('/properties', { query: { limit: 100, ...filters }, signal });
  return {
    ...response,
    items: response.items.map(propertyToListItem),
  };
}

/**
 * @param {string} propertyId
 * @param {{ signal?: AbortSignal }} [options]
 * @returns {Promise<PropertyDetail>}
 */
export async function getProperty(propertyId, { signal } = {}) {
  const property = await api.get(`/properties/${encodeURIComponent(propertyId)}`, { signal });
  return propertyToDetail(property);
}

/**
 * Triggers the existing backend valuation adapter. The frontend does not
 * prepare model features, load models, or calculate an AVM locally.
 *
 * @param {string} propertyId
 * @param {{ signal?: AbortSignal }} [options]
 * @returns {Promise<PropertyValuationResponse>}
 */
export function getPropertyValuation(propertyId, { signal } = {}) {
  return api.post(`/properties/${encodeURIComponent(propertyId)}/valuation`, undefined, { signal });
}

/**
 * @param {{ query: string, city?: string, area?: string, kind?: string, limit?: number, signal?: AbortSignal }} filters
 * @returns {Promise<PropertyPage>}
 */
export async function searchProperties({ query, signal, ...filters }) {
  const normalizedQuery = query.trim();
  if (!normalizedQuery) {
    throw new TypeError('A busca de imóveis exige um texto de consulta.');
  }
  const response = await api.post('/properties/search', { query: normalizedQuery, limit: 100, ...filters }, { signal });
  return {
    ...response,
    items: response.items
      .map((result) => result.property)
      .filter((property) => property !== null && property !== undefined)
      .map(propertyToListItem),
  };
}
