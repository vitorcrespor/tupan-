export const CITIES = [
  {
    name: 'São Paulo',
    state: 'SP',
    neighborhoods: ['Pinheiros', 'Vila Madalena', 'Jardins', 'Itaim Bibi', 'Moema', 'Brooklin', 'Vila Olímpia', 'Santana', 'Tatuapé', 'Cerqueira César'],
  },
];

export const PROPERTY_TYPES = ['Apartment', 'House', 'Penthouse', 'Commercial', 'Land'];

export const TIME_PERIODS = [
  { id: '30d', label: '30 dias' },
  { id: '60d', label: '60 dias' },
  { id: '90d', label: '90 dias' },
  { id: '6m', label: '6 meses' },
  { id: '12m', label: '12 meses' },
  { id: 'custom', label: 'Personalizado' },
];

// The top-bar selector is the one authoritative UI control for a listing
// liquidity horizon. "custom" deliberately remains unscored until the UI
// supports an explicit number of days; it must never silently become 90 days.
export const LIQUIDITY_HORIZON_DAYS = Object.freeze({
  '30d': 30,
  '60d': 60,
  '90d': 90,
  '6m': 180,
  '12m': 365,
});

export function liquidityHorizonDays(period) {
  return LIQUIDITY_HORIZON_DAYS[period] ?? null;
}

export function timePeriodLabel(period) {
  return TIME_PERIODS.find((item) => item.id === period)?.label || 'Horizonte não definido';
}

export const SAMPLE_QUESTIONS = [
  'Quais imóveis estão sobreavaliados?',
  'Onde meu portfólio está geograficamente superexposto?',
  'Quais bairros têm a demanda mais forte agora?',
  'Quais anúncios eu deveria priorizar?',
  'Por que os dias no mercado caíram em Pinheiros?',
  'Compare Pinheiros com Vila Madalena.',
  'Quais imóveis têm alto aquecimento de mercado mas precificação fraca?',
  'O que mudou no meu portfólio este mês?',
];
