import { api } from '@/api/client';

/** @typedef {{name: string, state: 'success'|'degraded'|'skipped', code: string|null, message: string|null, duration_ms: number}} AnalysisStatus */
/** @typedef {{listed_price: number|null, estimated_price: number, difference: number|null, difference_percent: number|null, price_per_m2: number|null, estimated_price_per_m2: number|null, inference_ms: number, lower_bound: number|null, upper_bound: number|null, interval_level: number|null, calibration_sample_count: number|null, out_of_time_coverage: number|null, model_version: string|null, uncertainty_status: 'calibrated'|'not_calibrated'|'unavailable', valuation_class:'BELOW_ESTIMATED_RANGE'|'WITHIN_ESTIMATED_RANGE'|'ABOVE_ESTIMATED_RANGE'|'INSUFFICIENT_CONFIDENCE'|null}} Valuation */
/** @typedef {{id: string, title: string|null, property_type:string|null, asking_price: number|null, estimated_price:number|null, area_m2: number|null, price_per_m2: number|null, rooms: number|null, bathrooms:number|null, parking_spaces:number|null, days_on_market: number|null, city:string|null, area:string|null, distance_meters: number|null,similarity_score:number|null,similarity_status:string,similarity_method:'cosine',similarity_feature_version:string,estimate_provenance?:import('./properties').EstateResponse['estimate_provenance']}} Comparable */
/** @typedef {{comparable_count: number, average_asking_price: number|null, median_asking_price: number|null, average_price_per_m2: number|null, median_price_per_m2: number|null, average_days_on_market: number|null}} LocalStatistics */
/** @typedef {object} EstateAnalysis
 * @property {import('./properties').EstateResponse} estate
 * @property {Valuation|null} valuation
 * @property {Comparable[]} comparables
 * @property {{eligible_count:number,candidate_count:number,scored_count:number,returned_count:number,candidate_limit:number,truncated:boolean,similarity_method:'cosine',similarity_feature_version:string}|null} comparable_metadata
 * @property {LocalStatistics|null} local_statistics
 * @property {Array<{metric:string,value:number,unit:string|null,observed_on:string,source_name:string,scope:string}>} market_context
 * @property {{h3_index:string|null,h3_resolution:number|null,city:string|null,area:string|null,period_start:string|null,period_end:string|null,metrics:Record<string,unknown>,input_version:string|null,calculated_at:string|null,scope:'tenant'|'platform'|null}|null} location_metrics
 * @property {{total_ms:number,components:AnalysisStatus[]}} timing
 * @property {{policy_version:string,completeness:number,quality:number,missing_fields:string[],critical_reasons:string[],warnings:string[]}|null} data_quality
 * @property {{model_type:string|null,target:string|null,training_rows:number|null,schema_version:number|null,uncertainty_status:'calibrated'|'not_calibrated'|'unavailable',uncertainty_method:string|null,calibration_sample_count:number|null,out_of_time_coverage:number|null,out_of_time_median_width_pct:number|null,model_version:string|null}|null} avm_diagnostics
 */

/** One deterministic request; AI is never a prerequisite for the results.
 * @param {string} estateId
 * @param {{signal?: AbortSignal, liquidity_horizon_days?:number|null}} [options]
 * @returns {Promise<EstateAnalysis>}
 */
export function getEstateAnalysis(estateId, { signal, liquidity_horizon_days } = {}) {
  return api.get(`/estates/${encodeURIComponent(estateId)}/analysis`, { query: { liquidity_horizon_days }, signal });
}

/** @typedef {{key:string,a_value:number|null,b_value:number|null,difference:number|null,unit:string}} EstatePairMetric */
/** @param {string} aId @param {string} bId @param {{signal?:AbortSignal,liquidity_horizon_days?:number|null}} [options]
 * @returns {Promise<{a:import('./properties').EstateResponse,b:import('./properties').EstateResponse,metrics:EstatePairMetric[],valuation_basis:string,similarity_score:number|null,similarity_status:string,similarity_method:'cosine',similarity_feature_version:string}>}
 */
export function getEstatePair(aId, bId, {signal, liquidity_horizon_days} = {}) {
  return api.get('/analytics/estate-pair', {query:{a_id:aId,b_id:bId,liquidity_horizon_days},signal});
}
