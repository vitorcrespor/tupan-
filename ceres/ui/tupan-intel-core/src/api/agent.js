import { api } from '@/api/client';

const AUTHORIZED_MARKET_METRICS = new Set([
  'price_m2', 'asking_price', 'avm_price', 'avm_deviation', 'market_heat',
  'dom', 'active_listings', 'regional_exposure', 'pricing_distribution',
  'kind_distribution', 'listing_age', 'liquidity',
]);

/**
 * Converts UI selections into bounded hints for the existing LangGraph-backed
 * API. Displayed browser values never become analytical evidence: the backend
 * validates the metric key and resolves the underlying data itself.
 *
 * @param {Array<{ type?: string, data?: object }>} items
 */
export function agentContextFromItems(items = []) {
  const region = items.find((item) => item.type === 'Region')?.data;
  const property = items.find((item) => item.type === 'Property')?.data;
  const metric = items.find((item) => item.type === 'Metric' || item.type === 'KPI')?.data;
  const metricKey = metric?.metric ?? metric?.metric_key;
  return {
    selected_region: region,
    selected_property: property,
    metric: AUTHORIZED_MARKET_METRICS.has(metricKey) ? metricKey : undefined,
    region: region?.name || region?.neighborhood,
    period: metric?.period,
    market_filters: {},
  };
}

/**
 * @param {{ message: string, sessionId?: string | null, contextItems?: Array<{ type?: string, data?: object }>, signal?: AbortSignal }} request
 */
export function sendAgentMessage({ message, sessionId = null, contextItems = [], signal }) {
  return api.post('/agent/chat', {
    session_id: sessionId || undefined,
    message,
    context: agentContextFromItems(contextItems),
  }, { signal, timeoutMs: 60_000 });
}

/**
 * @param {string} sessionId
 * @param {{ limit?: number, signal?: AbortSignal }} [options]
 */
export function getAgentTraces(sessionId, { limit = 250, signal } = {}) {
  return api.get(`/agent/sessions/${encodeURIComponent(sessionId)}/traces`, {
    query: { limit },
    signal,
  });
}