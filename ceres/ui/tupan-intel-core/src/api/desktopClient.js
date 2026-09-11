/**
 * Compatibility façade for pre-existing account/workspace screens.
 *
 * The old implementation stored identities, property notes, and saved searches
 * in the browser. This adapter intentionally has no local persistence: every
 * data operation crosses the versioned FastAPI boundary.
 */
import { api, ApiError } from '@/api/client';

const noRealtimeSubscription = () => () => {};

function unsupported(feature) {
  throw new ApiError(`${feature} ainda não está disponível no backend cloud.`, { code: 'FEATURE_NOT_AVAILABLE' });
}

function authUser(response) {
  return response?.user ?? response;
}

const entityAdapters = {
  User: {
    list: async () => api.get('workspace/members'),
    update: async (id, payload) => api.patch(`workspace/members/${encodeURIComponent(id)}`, payload),
    delete: async (id) => api.delete(`workspace/members/${encodeURIComponent(id)}`),
  },
  SavedSearch: {
    list: async () => api.get('workspace/saved-searches'),
    create: async (payload) => api.post('workspace/saved-searches', { name: payload.name, filters: payload.filters ?? {} }),
    delete: async (id) => api.delete(`workspace/saved-searches/${encodeURIComponent(id)}`),
  },
  PropertyNote: {
    list: async () => unsupported('A listagem de notas sem imóvel'),
    filter: async (query) => {
      if (!query?.property_id) return [];
      return api.get(`workspace/properties/${encodeURIComponent(query.property_id)}/notes`);
    },
    create: async (payload) => api.post(`workspace/properties/${encodeURIComponent(payload.property_id)}/notes`, { note: payload.note }),
  },
  DistrictBoundary: {
    list: async () => api.get('workspace/district-boundaries'),
  },
  // Property records already have a separate typed domain API. Data-management
  // migration is intentionally explicit rather than recreating a browser DB.
  Property: {
    list: async () => unsupported('A gestão de registros de imóveis'),
    create: async () => unsupported('O cadastro de imóveis'),
    bulkCreate: async () => unsupported('A importação de imóveis'),
    delete: async () => unsupported('A remoção de imóveis'),
  },
  MarketRegion: {
    list: async () => unsupported('A gestão de regiões de mercado'),
  },
};

function entity(name) {
  const adapter = entityAdapters[name];
  if (!adapter) return { list: async () => unsupported(`A entidade ${name}`), subscribe: noRealtimeSubscription };
  return { ...adapter, subscribe: noRealtimeSubscription };
}

export const appClient = {
  entities: new Proxy({}, { get: (_target, name) => entity(String(name)) }),
  auth: {
    async me() { return authUser(await api.get('auth/session')); },
    async loginViaEmailPassword(email, password) { return authUser(await api.post('auth/login', { email, password })); },
    async register(payload) { return authUser(await api.post('auth/register', payload)); },
    async logout() { await api.post('auth/logout', {}); },
    // Browser credentials are an HttpOnly cookie. There is deliberately no
    // token setter/getter in desktop JavaScript.
    setToken() {},
    async verifyOtp() { return unsupported('A verificação de e-mail'); },
    async resendOtp() { return unsupported('O reenvio de verificação'); },
    async resetPasswordRequest() { return unsupported('A recuperação de senha'); },
    async resetPassword() { return unsupported('A recuperação de senha'); },
    loginWithProvider() { return unsupported('O login social'); },
    redirectToLogin() { window.location.assign('/login'); },
  },
  users: {
    inviteUser: async () => unsupported('Os convites de equipe'),
  },
  functions: {
    async invoke(name) {
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
      async UploadFile() { return unsupported('O upload de arquivos'); },
      async ExtractDataFromUploadedFile() { return unsupported('A importação de planilhas'); },
    },
  },
};