import { api } from '@/api/client';

/**
 * @typedef {{
 *   scope:{city:string|null,area:string|null,active_only:true},
 *   summary:{active_estate_count:number,asking_price_count:number,price_per_m2_count:number,days_on_market_count:number,average_asking_price:number|null,average_price_per_m2:number|null,average_days_on_market:number|null}|null,
 *   featured_estates:Array<{id:string,title:string|null,city:string|null,area:string|null,asking_price:number|null,price_per_m2:number|null,days_on_market:number|null,updated_at:string}>,
 *   market_metrics:Array<{metric:'sales_velocity',unit:'sales/day',value:number|null,observed_on:string|null,source_name:string|null,status:'available'|'unavailable',reason:string|null}>,
 *   timing:{total_ms:number,components:Array<{name:string,state:string,duration_ms:number,code?:string|null,message?:string|null}>}
 * }} ReportSummary
 */

/**
 * Complete tenant-scope report aggregates are calculated on the API. The
 * browser supplies geography only; organization identity comes from the
 * session and no first-page catalog arithmetic is performed here.
 *
 * @param {{city?:string,area?:string,featuredLimit?:number,signal?:AbortSignal}} [filters]
 * @returns {Promise<ReportSummary>}
 */
export function getReportSummary({ city, area, featuredLimit = 6, signal } = {}) {
  return api.get('/analytics/report-summary', {
    query: { city, area, featured_limit: featuredLimit },
    signal,
  });
}
