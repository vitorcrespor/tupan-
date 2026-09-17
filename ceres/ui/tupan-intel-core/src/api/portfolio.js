import { api, ApiError } from '@/api/client';

/** @typedef {{id: string, name: string, description: string|null}} Portfolio */
/** @typedef {{property_id: string, title: string|null, region: string|null, asking_price: number|null, estimated_price: number|null, price_gap: number|null, difference: number|null,estimate_provenance?:import('./properties').EstateResponse['estimate_provenance']}} PricePosition */
/** @typedef {object} PortfolioOverview
 * @property {Portfolio} portfolio
 * @property {{active_estate_count:number,portfolio_value:number,estimated_value:number,average_price_gap:number|null,estimate_lineage_count:number,estimate_inputs_changed_count:number}|null} valuation_summary
 * @property {{average_asking_price:number|null,median_asking_price:number|null,average_price_per_m2:number|null,median_price_per_m2:number|null,average_days_on_market:number|null,listing_age_count:number,average_listing_age_days:number|null}|null} pricing_statistics
 * @property {{score:number|null,status:string,horizon_days:number|null,active_estate_count:number,eligible_estate_count:number,observed_estate_count:number,sale_event_count:number,model_version:string|null}|null} liquidity_summary
 * @property {Array<{observed_on:string,active_estate_count:number,asking_price_count:number,estimated_count:number,days_on_market_count:number,listing_age_count:number,portfolio_value:number|null,average_days_on_market:number|null,average_listing_age_days:number|null,average_price_gap:number|null}>} history
 * @property {{above_count:number,below_count:number,equal_count:number,missing_count:number,asking_count:number,estimated_count:number,rows:PricePosition[]}|null} positions
 * @property {Array<{city:string|null,area:string|null,estate_count:number,portfolio_value:number,share:number}>} geographic_concentration
 * @property {Array<{property_type:string|null,estate_count:number,share:number}>} property_distribution
 * @property {Array<{city:string|null,area:string|null,estate_count:number,average_price_m2:number|null,market_heat:number|null,latest_observed_on:string|null}>} market_exposure
 * @property {number|null} top_region_share
 * @property {{total_ms:number,components:import('./analysis').AnalysisStatus[]}} timing
 */

/** @param {{signal?:AbortSignal}} [options]
 * @returns {Promise<Portfolio[]>} */
export function getPortfolios({ signal } = {}) {
  return api.get('/portfolios', { signal });
}

/** Field/unit mapping only; totals and distributions remain backend-owned.
 * @param {PortfolioOverview} response
 */
export function portfolioToView(response) {
  const summary=response.valuation_summary, prices=response.pricing_statistics, positions=response.positions;
  return {
    portfolio: response.portfolio,
    active_listing_count: summary?.active_estate_count ?? null,
    estimate_lineage_count: summary?.estimate_lineage_count ?? null,
    estimate_inputs_changed_count: summary?.estimate_inputs_changed_count ?? null,
    portfolio_value: summary && positions && (positions.asking_count > 0 || summary.active_estate_count === 0) ? summary.portfolio_value : null,
    estimated_value: summary && positions && positions.estimated_count === summary.active_estate_count ? summary.estimated_value : null,
    average_asking_price: prices?.average_asking_price ?? null,
    median_asking_price: prices?.median_asking_price ?? null,
    average_price_per_m2: prices?.average_price_per_m2 ?? null,
    median_price_per_m2: prices?.median_price_per_m2 ?? null,
    average_dom_days: prices?.average_days_on_market ?? null,
    listing_age_count: prices?.listing_age_count ?? 0,
    average_listing_age_days: prices?.average_listing_age_days ?? null,
    liquidity_score: response.liquidity_summary?.score ?? null,
    liquidity_status: response.liquidity_summary?.status ?? null,
    liquidity_horizon_days: response.liquidity_summary?.horizon_days ?? null,
    liquidity_eligible_estate_count: response.liquidity_summary?.eligible_estate_count ?? null,
    liquidity_observed_estate_count: response.liquidity_summary?.observed_estate_count ?? null,
    liquidity_sale_event_count: response.liquidity_summary?.sale_event_count ?? null,
    average_price_gap: summary?.average_price_gap ?? null,
    top_region_share: response.top_region_share,
    asking_count: positions?.asking_count ?? null, estimated_count: positions?.estimated_count ?? null,
    above_count: positions?.above_count ?? null, below_count: positions?.below_count ?? null,
    equal_count: positions?.equal_count ?? null, missing_count: positions?.missing_count ?? null,
    positions_available: positions != null,
    above_estimate: (positions?.rows || []).filter(item => item.price_gap > 0),
    below_estimate: (positions?.rows || []).filter(item => item.price_gap < 0),
    regional_concentration: response.geographic_concentration.map(item => ({
      region: [item.area, item.city].filter(Boolean).join(', ') || 'Região não informada',
      property_count: item.estate_count, portfolio_value: item.portfolio_value, share: item.share,
    })),
    property_type_mix: response.property_distribution.map(item => ({
      kind: item.property_type, property_count: item.estate_count, share: item.share,
    })),
    market_exposure: response.market_exposure,
    history: Array.isArray(response.history) ? response.history : [],
    warnings: response.timing.components.filter(item => item.state !== 'success'),
    source: {kind: 'LIVE', label: response.portfolio.name, detail: 'Imóveis ativos do portfólio autorizado'},
  };
}

/** @param {{portfolioId?: string|null, liquidityHorizonDays?: number|null, signal?: AbortSignal}} [options] */
export async function getPortfolioAnalytics({ portfolioId, liquidityHorizonDays, signal } = {}) {
  const id = portfolioId || (await getPortfolios({ signal }))[0]?.id;
  if (!id) throw new ApiError('Nenhum portfólio cadastrado nesta organização.', {code: 'NO_PORTFOLIO'});
  const response = await api.get(`/portfolios/${encodeURIComponent(id)}/overview`, {
    signal,
    query: { liquidity_horizon_days: liquidityHorizonDays },
  });
  return portfolioToView(response);
}
