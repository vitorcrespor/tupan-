import { api } from '@/api/client';

/**
 * Converts the UI's attached context into the transport schema consumed by
 * the existing LangGraph-backed API.  It only forwards selected evidence;
 * it does not calculate market or valuation values in the browser.
 *
 * @param {Array<{ type?: string, data?: object }>} items
 */
export function agentContextFromItems(items = []) {
  const region = items.find((item) => item.type === 'Region')?.data;
  const property = items.find((item) => item.type === 'Property')?.data;
  const metric = items.find((item) => item.type === 'Metric' || item.type === 'KPI')?.data;
  return {
    selected_region: region,
    selected_property: property,
    metric: metric?.metric,
    region: region?.name || region?.neighborhood,
    period: metric?.period,
    market_filters: items.length ? { attached_context: items.map(({ type, data }) => ({ type, data })) } : {},
  };
}

/**
 * @param {{ message: string, sessionId?: string | null, contextItems?: Array<{ type?: string, data?: object }>, signal?: AbortSignal }} request
 */
export function sendAgentMessage({ message, sessionId = null, contextItems = [], signal } = {}) {
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
