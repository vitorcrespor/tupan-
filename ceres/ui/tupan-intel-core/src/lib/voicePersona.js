const KEY = 'ceres.voice.persona';

export const PERSONAS = [
  { id: 'analyst', label: 'Analista', blurb: 'Preciso, números primeiro', prompt: 'um analista quantitativo preciso que lidera com números e cita métricas' },
  { id: 'advisor', label: 'Consultor', blurb: 'Acolhedor, consultivo', prompt: 'um consultor acolhedor que enquadra os dados como recomendações' },
  { id: 'scout', label: 'Caçador', blurb: 'Rápido, caça oportunidades', prompt: 'um caçador de oportunidades ágil que evidencia oportunidades e riscos de forma direta' },
];

export const TONES = [
  { id: 'concise', label: 'Conciso', prompt: 'Responda em no máximo 3 frases curtas.' },
  { id: 'balanced', label: 'Equilibrado', prompt: 'Responda em um parágrafo curto.' },
  { id: 'detailed', label: 'Detalhado', prompt: 'Responda de forma completa com uma breve análise.' },
];

export const FOCUS = ['Pricing', 'Demand', 'Liquidity', 'Risk', 'Portfolio'];
export const FOCUS_LABELS = {
  Pricing: 'Precificação',
  Demand: 'Demanda',
  Liquidity: 'Liquidez',
  Risk: 'Risco',
  Portfolio: 'Portfólio',
};

export const DEFAULT_PERSONA = {
  name: '',
  persona: 'analyst',
  tone: 'concise',
  focus: ['Pricing', 'Demand'],
  speak: true,
  rate: 1,
};

export const loadPersona = () => {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? { ...DEFAULT_PERSONA, ...JSON.parse(raw) } : DEFAULT_PERSONA;
  } catch {
    return DEFAULT_PERSONA;
  }
};

export const savePersona = (p) => {
  try {
    localStorage.setItem(KEY, JSON.stringify(p));
  } catch {
    /* storage unavailable */
  }
};

// Builds the spoken-conversation system framing from the user's personalization.
export const buildVoicePrompt = (p, question) => {
  const persona = PERSONAS.find((x) => x.id === p.persona) || PERSONAS[0];
  const tone = TONES.find((x) => x.id === p.tone) || TONES[0];
  const focusLabels = (p.focus || []).map((f) => FOCUS_LABELS[f] || f);
  return [
    `Você é a Ceres, uma assistente de voz de inteligência imobiliária para corretores de São Paulo. Fale como ${persona.prompt}.`,
    p.name ? `Você está falando com ${p.name}; chame-o pelo nome ocasionalmente.` : '',
    focusLabels.length ? `Eles se importam mais com: ${focusLabels.join(', ')}.` : '',
    'Esta é uma conversa falada: use frases simples, sem markdown, sem listas, sem tabelas.',
    tone.prompt,
    '',
    `Pergunta: ${question}`,
  ]
    .filter(Boolean)
    .join('\n');
};