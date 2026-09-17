/**
 * Compatibility façade for pre-existing account/workspace screens.
 *
 * The old implementation stored identities, property notes, and saved searches
 * in the browser. This adapter intentionally has no local persistence: every
 * data operation crosses the versioned FastAPI boundary.
 */
import { api, ApiError } from '@/api/client';

/** @param {(event: {data?: Record<string, any>}) => void} [_callback] */
const noRealtimeSubscription = (_callback) => () => {};

/** @returns {never} */
function unsupported(feature) {
  throw new ApiError(`${feature} ainda não está disponível no backend cloud.`, { code: 'FEATURE_NOT_AVAILABLE' });
}

function authUser(response) {
  return response?.user ?? response;
}

const entityAdapters = {
  User: {
    list: async (_sort, _limit) => api.get('workspace/members'),
    update: async (id, payload) => api.patch(`workspace/members/${encodeURIComponent(id)}`, payload),
    delete: async (id) => api.delete(`workspace/members/${encodeURIComponent(id)}`),
  },
  SavedSearch: {
    list: async (_sort, _limit) => api.get('workspace/saved-searches'),
    create: async (payload) => api.post('workspace/saved-searches', { name: payload.name, filters: payload.filters ?? {} }),
    delete: async (id) => api.delete(`workspace/saved-searches/${encodeURIComponent(id)}`),
  },
  PropertyNote: {
    list: async (_sort, _limit) => unsupported('A listagem de notas sem imóvel'),
    filter: async (query, _sort, _limit) => {
      if (!query?.property_id) return [];
      return api.get(`workspace/properties/${encodeURIComponent(query.property_id)}/notes`);
    },
    create: async (payload) => api.post(`workspace/properties/${encodeURIComponent(payload.property_id)}/notes`, { note: payload.note }),
  },
  DistrictBoundary: {
    list: async (_sort, _limit) => api.get('workspace/district-boundaries'),
  },
  // Property records already have a separate typed domain API. Data-management
  // migration is intentionally explicit rather than recreating a browser DB.
  Property: {
    list: async (_sort, _limit) => unsupported('A gestão de registros de imóveis'),
    create: async (_payload) => unsupported('O cadastro de imóveis'),
    bulkCreate: async (_payloads) => unsupported('A importação de imóveis'),
    delete: async (_id) => unsupported('A remoção de imóveis'),
  },
  MarketRegion: {
    list: async (_sort, _limit) => unsupported('A gestão de regiões de mercado'),
  },
};

const entities = {
  User: { ...entityAdapters.User, subscribe: noRealtimeSubscription },
  SavedSearch: { ...entityAdapters.SavedSearch, subscribe: noRealtimeSubscription },
  PropertyNote: { ...entityAdapters.PropertyNote, subscribe: noRealtimeSubscription },
  DistrictBoundary: { ...entityAdapters.DistrictBoundary, subscribe: noRealtimeSubscription },
  Property: { ...entityAdapters.Property, subscribe: noRealtimeSubscription },
  MarketRegion: { ...entityAdapters.MarketRegion, subscribe: noRealtimeSubscription },
};

export const appClient = {
  entities,
  auth: {
    async me() { return authUser(await api.get('auth/session')); },
    async loginViaEmailPassword(email, password) { return authUser(await api.post('auth/login', { email, password })); },
    async register(payload) { return authUser(await api.post('auth/register', payload)); },
    async logout() { await api.post('auth/logout', {}); },
    // Browser credentials are an HttpOnly cookie. There is deliberately no
    // token setter/getter in desktop JavaScript.
    setToken(_token) {},
    /** @returns {Promise<{access_token?: string}>} */
    async verifyOtp(_payload) { return unsupported('A verificação de e-mail'); },
    async resendOtp(_email) { return unsupported('O reenvio de verificação'); },
    async resetPasswordRequest(_email) { return unsupported('A recuperação de senha'); },
    async resetPassword(_payload) { return unsupported('A recuperação de senha'); },
    loginWithProvider(_provider, _returnTo) { return unsupported('O login social'); },
    redirectToLogin() { window.location.assign('/login'); },
  },
  users: {
    inviteUser: async (_email, _role) => unsupported('Os convites de equipe'),
  },
  functions: {
    async invoke(name, _payload) {
      if (name === 'mapsKey' || name === 'getMapsConfig') {
        // Restricted browser map keys are presentation configuration, not
        // privileged cloud credentials. They remain optional.
        const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || '';
        return { data: name === 'mapsKey' ? { key: apiKey } : { apiKey } };
      }
      return { data: {} };
    },
  },
  integrations: {
    Core: {
      /** @returns {Promise<{file_url: string}>} */
      async UploadFile(_payload) { return unsupported('O upload de arquivos'); },
      /** @returns {Promise<{output: Array<Record<string, any>>}>} */
      async ExtractDataFromUploadedFile(_payload) { return unsupported('A importação de planilhas'); },
    },
  },
};
