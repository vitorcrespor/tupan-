import { api } from '@/api/client';

/**
 * @typedef {object} PortfolioConcentration
 * @property {string} region
 * @property {number} property_count
 * @property {number} portfolio_value
 * @property {number} share Fraction from 0 to 1.
 */

/**
 * @typedef {object} PortfolioTypeMix
 * @property {string} kind
 * @property {number} property_count
 * @property {number} portfolio_value
 * @property {number} share Fraction from 0 to 1.
 */

/**
 * @typedef {object} PortfolioRegionalPerformance
 * @property {string} region
 * @property {number} property_count
 * @property {number | null} average_expected_growth Fraction from the persisted model.
 * @property {number | null} average_price_per_m2
 * @property {number | null} average_dom_days
 */

/**
 * @typedef {object} PortfolioValuationItem
 * @property {string} property_id
 * @property {string} title
 * @property {string | null} region
 * @property {string | null} kind
 * @property {number | null} asking_price
 * @property {number | null} estimated_price
 * @property {number | null} price_gap Positive means above the persisted estimate.
 * @property {number | null} dom_days
 * @property {number | null} expected_growth
 */

/**
 * @typedef {object} PortfolioAnalytics
 * @property {number} active_listing_count
 * @property {number} sold_listing_count
 * @property {number} portfolio_value
 * @property {number | null} average_asking_price
 * @property {number | null} median_asking_price
 * @property {number | null} average_price_per_m2
 * @property {number | null} average_price_gap
 * @property {number | null} average_expected_growth
 * @property {number | null} average_listing_age_days
 * @property {number | null} average_dom_days
 * @property {number | null} stagnation_rate
 * @property {number | null} hhi
 * @property {PortfolioConcentration[]} regional_concentration
 * @property {PortfolioTypeMix[]} property_type_mix
 * @property {PortfolioRegionalPerformance[]} regional_performance
 * @property {PortfolioValuationItem[]} above_estimate
 * @property {PortfolioValuationItem[]} below_estimate
 * @property {object} source
 */

/**
 * Reads deterministic analytics over the persisted current property collection.
 * The backend owns all aggregation and valuation-gap calculations.
 *
 * @param {{ signal?: AbortSignal }} [options]
 * @returns {Promise<PortfolioAnalytics>}
 */
export function getPortfolioAnalytics({ signal } = {}) {
  return api.get('/portfolio/analytics', { signal });
}
