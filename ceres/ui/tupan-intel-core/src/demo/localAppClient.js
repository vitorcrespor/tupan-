/**
 * Demo-only local persistence for screens that do not yet have a backend API
 * (authentication, team administration, notes, saved searches and manual
 * data-management). Production data screens use the domain API modules.
 */
const STORAGE_PREFIX = 'tupan_demo_';

const now = () => new Date().toISOString();
const id = () => crypto.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`;
const neighborhoods = ['Pinheiros', 'Vila Madalena', 'Jardins', 'Itaim Bibi', 'Moema', 'Brooklin', 'Vila Olímpia', 'Santana', 'Tatuapé', 'Cerqueira César'];

const seedRegions = neighborhoods.map((name, index) => ({
  id: `region-${index + 1}`,
  name,
  city: 'São Paulo',
  average_price_per_m2: 9800 + index * 620,
  market_heat: 54 + ((index * 7) % 42),
  demand_score: 58 + ((index * 5) % 38),
  liquidity_score: 50 + ((index * 9) % 45),
  created_date: now(),
}));

const seedProperties = Array.from({ length: 36 }, (_, index) => {
  const neighborhood = neighborhoods[index % neighborhoods.length];
  const area = 55 + (index % 8) * 18;
  const pricePerM2 = 9700 + (index % 10) * 690;
  const price = area * pricePerM2;
  return {
    id: `property-${index + 1}`,
    title: `${index % 5 === 0 ? 'Cobertura' : 'Apartamento'} ${neighborhood}`,
    address: `Rua ${neighborhood}, ${100 + index * 7}`,
    city: 'São Paulo',
    neighborhood,
    latitude: -23.55 - (index % 7) * 0.006,
    longitude: -46.62 - (index % 9) * 0.007,
    property_type: index % 5 === 0 ? 'Penthouse' : 'Apartment',
    bedrooms: 1 + (index % 4),
    bathrooms: 1 + (index % 3),
    parking_spaces: index % 3,
    area_m2: area,
    price,
    suggested_price: Math.round(price * (0.94 + (index % 5) * 0.025)),
    price_per_m2: pricePerM2,
    price_deviation: -6 + (index % 7) * 2,
    valuation_confidence: 76 + (index % 18),
    valuation_class: 'Fair Value',
    comparable_count: 8 + (index % 14),
    days_on_market: 18 + (index % 9) * 6,
    market_heat: 56 + ((index * 7) % 40),
    liquidity_score: 52 + ((index * 5) % 43),
    luxury_score: 45 + ((index * 9) % 50),
    leisure_score: 50 + ((index * 6) % 45),
    location_score: 62 + ((index * 5) % 35),
    leverage_score: 48 + ((index * 8) % 46),
    property_age: 2 + (index % 28),
    status: 'Active',
    created_date: new Date(Date.now() - index * 86400000).toISOString(),
  };
});

const seedUsers = [{ id: 'local-admin', full_name: 'Tupan Admin', email: 'admin@tupan.local', role: 'admin', created_date: now() }];
const seeds = { Property: seedProperties, MarketRegion: seedRegions, User: seedUsers, SavedSearch: [], PropertyNote: [], DistrictBoundary: [] };
const listeners = new Map();

function readEntity(name) {
  const key = `${STORAGE_PREFIX}${name}`;
  const stored = localStorage.getItem(key);
  if (stored) return JSON.parse(stored);
  const initial = seeds[name] || [];
  localStorage.setItem(key, JSON.stringify(initial));
  return initial;
}

function writeEntity(name, records, event) {
  localStorage.setItem(`${STORAGE_PREFIX}${name}`, JSON.stringify(records));
  (listeners.get(name) || []).forEach((callback) => callback(event));
}

function entity(name) {
  return {
    async list(sort = '-created_date', limit = 500) {
      const descending = sort.startsWith('-');
      const field = sort.replace(/^-/, '');
      return [...readEntity(name)].sort((a, b) => String(a[field] || '').localeCompare(String(b[field] || '')) * (descending ? -1 : 1)).slice(0, limit);
    },
    async filter(query, sort = '-created_date', limit = 100) {
      const results = readEntity(name).filter((record) => Object.entries(query).every(([key, value]) => record[key] === value));
      const descending = sort.startsWith('-');
      const field = sort.replace(/^-/, '');
      return results.sort((a, b) => String(a[field] || '').localeCompare(String(b[field] || '')) * (descending ? -1 : 1)).slice(0, limit);
    },
    async create(payload) {
      const record = { ...payload, id: id(), created_date: now(), updated_date: now() };
      const records = [...readEntity(name), record];
      writeEntity(name, records, { type: 'create', data: record });
      return record;
    },
    async bulkCreate(payloads) { return Promise.all(payloads.map((payload) => this.create(payload))); },
    async update(recordId, payload) {
      let updated;
      const records = readEntity(name).map((record) => record.id === recordId ? (updated = { ...record, ...payload, updated_date: now() }) : record);
      writeEntity(name, records, { type: 'update', data: updated });
      return updated;
    },
    async delete(recordId) {
      writeEntity(name, readEntity(name).filter((record) => record.id !== recordId), { type: 'delete', id: recordId });
      return { success: true };
    },
    subscribe(callback) {
      listeners.set(name, [...(listeners.get(name) || []), callback]);
      return () => listeners.set(name, (listeners.get(name) || []).filter((item) => item !== callback));
    },
  };
}

const entities = new Proxy({}, { get: (_, name) => entity(name) });
const localUser = () => JSON.parse(localStorage.getItem(`${STORAGE_PREFIX}session`) || 'null');
const setLocalUser = (user) => localStorage.setItem(`${STORAGE_PREFIX}session`, JSON.stringify(user));

export const appClient = {
  entities,
  auth: {
    async me() { return localUser() || seedUsers[0]; },
    async loginViaEmailPassword(email) { setLocalUser({ ...seedUsers[0], email }); return { success: true }; },
    async register({ email }) { setLocalUser({ ...seedUsers[0], id: id(), email, role: 'admin' }); return { success: true }; },
    async verifyOtp() { return { access_token: 'local-session' }; },
    async resendOtp() { return { success: true }; },
    async resetPasswordRequest() { return { success: true }; },
    async resetPassword() { return { success: true }; },
    setToken() {},
    loginWithProvider(_provider, returnTo = '/') { setLocalUser(seedUsers[0]); window.location.href = returnTo; },
    logout() { localStorage.removeItem(`${STORAGE_PREFIX}session`); window.location.href = '/login'; },
    redirectToLogin() { window.location.href = '/login'; },
  },
  users: {
    async inviteUser(email, role = 'user') { return entity('User').create({ email, full_name: email.split('@')[0], role }); },
  },
  functions: {
    async invoke(name) {
      if (name === 'mapsKey' || name === 'getMapsConfig') {
        const key = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || '';
        return { data: name === 'mapsKey' ? { key } : { apiKey: key } };
      }
      return { data: {} };
    },
  },
  integrations: {
    Core: {
      async UploadFile({ file }) { return { file_url: URL.createObjectURL(file), file }; },
      async ExtractDataFromUploadedFile() { throw new Error('Importação inteligente requer um provedor externo. O cadastro manual continua disponível.'); },
    },
  },
};
