import { api, ApiError } from '@/api/client';

const AUTHORIZED_MARKET_METRICS = new Set([
  'price_m2', 'asking_price', 'avm_price', 'avm_deviation', 'market_heat',
  'dom', 'active_listings', 'regional_exposure', 'pricing_distribution',
  'kind_distribution', 'listing_age', 'liquidity', 'price_growth', 'sales_velocity',
]);

/**
 * Converts UI selections into bounded hints for the deterministic-service-backed
 * API. Displayed browser values never become analytical evidence: the backend
 * validates the metric key and resolves the underlying data itself.
 *
 * @param {Array<{ id?: string, label?: string, type?: string, data?: Record<string,any> }>} items
 */
export function agentContextFromItems(items = []) {
  const typed = type => items.filter(item => item.type?.toLowerCase() === type).map(item => item.data || {});
  const properties = typed('property');
  const ids = [...new Set(properties.map(item => item.id || item.property_id).filter(Boolean))];
  if (ids.length > 1) throw new ApiError('Selecione um imóvel por análise. A comparação de vários imóveis ainda não está conectada à IA.', {code: 'CONTEXT_NOT_SUPPORTED'});
  const portfolio = typed('portfolio')[0] || items.map(item => item.data).find(data => data?.portfolio_id);
  const region = typed('region')[0];
  const metrics = items.filter(item => ['metric', 'kpi', 'chart'].includes(item.type?.toLowerCase())).map(item => item.data || {});
  if (new Set(metrics.map(item => item.metric ?? item.metric_key).filter(Boolean)).size > 1) throw new ApiError('Selecione uma métrica por consulta. O backend ainda não suporta múltiplas métricas na mesma solicitação.', {code:'CONTEXT_NOT_SUPPORTED'});
  const metric = metrics[0];
  const metricKey = metric?.metric ?? metric?.metric_key;
  /** @type {{city?:string,area?:string,h3_resolution?:number}} */
  const filters = {};
  if (metric?.city) filters.city = metric.city;
  if (metric?.area) filters.area = metric.area;
  if (region?.city) filters.city = region.city;
  if (region?.area || region?.neighborhood) filters.area = region.area || region.neighborhood;
  if (region?.h3_resolution != null) filters.h3_resolution = region.h3_resolution;
  if (region?.h3_index) throw new ApiError('A interpretação de uma célula H3 específica ainda não está conectada. O mapa continua mostrando seus dados publicados.', {code:'CONTEXT_NOT_SUPPORTED'});
  if (items.length && !ids.length && !portfolio && !Object.keys(filters).length && !AUTHORIZED_MARKET_METRICS.has(metricKey)) throw new ApiError('Este contexto não possui um provedor analítico conectado à Ceres.', {code:'CONTEXT_NOT_SUPPORTED'});
  return {
    estate_id: ids[0],
    portfolio_id: portfolio?.portfolio_id || portfolio?.id,
    metric: AUTHORIZED_MARKET_METRICS.has(metricKey) ? metricKey : undefined,
    period: metric?.period,
    market_filters: filters,
  };
}

/**
 * @param {{ message: string, sessionId?: string | null, contextItems?: Array<{ id?: string, label?: string, type?: string, data?: Record<string,any> }>, reportScope?: {city?: string, area?: string}, signal?: AbortSignal }} request
 */
export function sendAgentMessage({ message, sessionId = null, contextItems = [], reportScope, signal }) {
  const context = agentContextFromItems(contextItems);
  if (reportScope) {
    context.report_scope = { city: reportScope.city, area: reportScope.area };
  }
  return api.post('/agent/chat', {
    session_id: sessionId || undefined,
    message,
    context,
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
