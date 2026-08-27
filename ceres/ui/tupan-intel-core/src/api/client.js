/**
 * Thin HTTP client shared by the API modules.  Domain modules own endpoint
 * paths and payload shapes; React components never call fetch directly.
 */

const DEFAULT_TIMEOUT_MS = 20_000;

export class ApiError extends Error {
  /**
   * @param {string} message
   * @param {{ status?: number | null, code?: string, details?: unknown, cause?: unknown }} [options]
   */
  constructor(message, { status = null, code = 'API_ERROR', details = null, cause = null } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
    this.cause = cause;
  }
}

function apiBaseUrl() {
  const baseUrl = import.meta.env.VITE_API_BASE_URL;
  if (!baseUrl) {
    throw new ApiError('A URL da API não foi configurada. Defina VITE_API_BASE_URL.', {
      code: 'API_CONFIGURATION_ERROR',
    });
  }
  return baseUrl.replace(/\/+$/, '');
}

function apiUrl(path, query) {
  const url = new URL(`${apiBaseUrl()}/${path.replace(/^\/+/, '')}`);
  for (const [key, value] of Object.entries(query || {})) {
    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

async function parseResponseBody(response) {
  const contentType = response.headers.get('content-type') || '';
  if (response.status === 204) return null;
  if (!contentType.includes('application/json')) return await response.text();
  try {
    return await response.json();
  } catch {
    return null;
  }
}

/**
 * @template T
 * @param {'GET' | 'POST' | 'PATCH' | 'DELETE'} method
 * @param {string} path
 * @param {{ query?: Record<string, unknown>, body?: unknown, signal?: AbortSignal, timeoutMs?: number }} [options]
 * @returns {Promise<T>}
 */
async function request(method, path, { query, body, signal, timeoutMs = DEFAULT_TIMEOUT_MS } = {}) {
  const timeoutController = new AbortController();
  const timeoutId = window.setTimeout(() => timeoutController.abort(), timeoutMs);

  if (signal) {
    if (signal.aborted) timeoutController.abort();
    else signal.addEventListener('abort', () => timeoutController.abort(), { once: true });
  }

  try {
    const response = await fetch(apiUrl(path, query), {
      method,
      headers: {
        Accept: 'application/json',
        ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: timeoutController.signal,
    });
    const payload = await parseResponseBody(response);

    if (!response.ok) {
      const errorPayload = payload && typeof payload === 'object' ? payload : {};
      throw new ApiError(errorPayload.message || `A API respondeu com status ${response.status}.`, {
        status: response.status,
        code: errorPayload.code || 'HTTP_ERROR',
        details: errorPayload.details || payload,
      });
    }
    return /** @type {T} */ (payload);
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (timeoutController.signal.aborted && !signal?.aborted) {
      throw new ApiError('A consulta à API excedeu o tempo limite.', {
        code: 'API_TIMEOUT',
        cause: error,
      });
    }
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('A consulta à API foi cancelada.', { code: 'API_ABORTED', cause: error });
    }
    throw new ApiError('Não foi possível conectar à API.', { code: 'NETWORK_ERROR', cause: error });
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export const api = {
  get: (path, options) => request('GET', path, options),
  post: (path, body, options) => request('POST', path, { ...options, body }),
  patch: (path, body, options) => request('PATCH', path, { ...options, body }),
  delete: (path, options) => request('DELETE', path, options),
};

/** @param {unknown} error */
export function apiErrorMessage(error) {
  if (!(error instanceof ApiError)) {
    if (import.meta.env.DEV && error instanceof Error && error.message) {
      return `Ocorreu um erro inesperado: ${error.message}`;
    }
    return 'Ocorreu um erro inesperado ao consultar a API.';
  }
  if (!import.meta.env.DEV || (!error.status && !error.code)) return error.message;
  const diagnostics = [error.status ? `HTTP ${error.status}` : null, error.code].filter(Boolean).join(' · ');
  return `${error.message} (${diagnostics})`;
}
