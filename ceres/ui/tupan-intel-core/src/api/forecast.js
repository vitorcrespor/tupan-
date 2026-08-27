import { api } from '@/api/client';

/**
 * @typedef {object} ForecastPoint
 * @property {number} period_days Forecast horizon measured from the property reference point.
 * @property {number} value Predicted P50 property price in BRL.
 * @property {number} p10 Lower quantile price in BRL.
 * @property {number} p90 Upper quantile price in BRL.
 */

/**
 * @typedef {object} PropertyForecastResponse
 * @property {string | null} property_id
 * @property {'property_price'} metric
 * @property {'BRL'} unit
 * @property {number} time_span_days
 * @property {number} current_value
 * @property {number} expected_growth_pct Percentage, not a fractional rate.
 * @property {Array<{ period_days: number, value: number }>} historical Observed points only; the current model returns an empty array.
 * @property {ForecastPoint[]} forecast Predicted points only.
 * @property {[number, number, number]} interval Legacy [P10, P50, P90] representation.
 * @property {{ reference_date?: string | null, city?: string | null, state?: string | null, indicators?: Record<string, number> } | null} context
 * @property {'existing_xgboost_quantile_time_series'} model
 */

/**
 * Runs the backend's existing property-price time-series forecast. This is
 * distinct from the AVM: it predicts a future price at a time horizon, while
 * the AVM estimates current market value.
 *
 * @param {string} propertyId
 * @param {{ timeSpanDays?: number, signal?: AbortSignal }} [options]
 * @returns {Promise<PropertyForecastResponse>}
 */
export function getPropertyForecast(propertyId, { timeSpanDays = 180, signal } = {}) {
  return api.post('/forecast', {
    property_id: propertyId,
    time_span_days: timeSpanDays,
  }, { signal });
}
