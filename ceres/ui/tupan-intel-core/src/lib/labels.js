// Display labels for enum values stored in the database. The stored values
// stay in English (they are entity enum keys); these maps only affect what
// the user sees on screen.
export const PROPERTY_TYPE_LABELS = {
  Apartment: 'Apartamento',
  House: 'Casa',
  Penthouse: 'Cobertura',
  Commercial: 'Comercial',
  Land: 'Terreno',
  'casa de rua': 'Casa de rua',
  'casa de condomínio': 'Casa de condomínio',
  apartamento: 'Apartamento',
  studio: 'Studio',
  cobertura: 'Cobertura',
  sobrado: 'Sobrado',
  chácara: 'Chácara',
  sítio: 'Sítio',
};

export const STATUS_LABELS = {
  Active: 'Ativo',
  Sold: 'Vendido',
  'Off Market': 'Fora do mercado',
  Unavailable: 'Indisponível',
};

export const VALUATION_LABELS = {
  Overpriced: 'Sobreavaliado',
  Underpriced: 'Subavaliado',
  'Fair Value': 'Preço justo',
  Unavailable: 'Indisponível',
};

export const DEMAND_LABELS = {
  Low: 'Baixa',
  Medium: 'Média',
  High: 'Alta',
};

export const propertyTypeLabel = (v) => PROPERTY_TYPE_LABELS[v] || v;
export const statusLabel = (v) => STATUS_LABELS[v] || v;
export const valuationLabel = (v) => VALUATION_LABELS[v] || v;
export const demandLabel = (v) => DEMAND_LABELS[v] || v;
