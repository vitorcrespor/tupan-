// Shared aqua/lagoon chart palette (Frutiger Aero theme).
// Recharts needs concrete color strings, so we resolve the CSS tokens to hsl().

export const CHART = {
  aqua: 'hsl(188 78% 52%)',
  lagoon: 'hsl(196 72% 46%)',
  teal: 'hsl(174 68% 42%)',
  mint: 'hsl(158 62% 42%)',
  sky: 'hsl(206 70% 54%)',
  positive: 'hsl(158 62% 40%)',
  negative: 'hsl(348 62% 54%)',
  warning: 'hsl(42 88% 48%)',
  grid: 'hsl(190 42% 84%)',
  axis: 'hsl(202 20% 39%)',
  tooltipBg: 'hsl(190 70% 98% / 0.94)',
  tooltipBorder: 'hsl(188 62% 62% / 0.38)',
  tooltipLabel: 'hsl(202 28% 30%)',
};

export const tooltipStyle = {
  background: CHART.tooltipBg,
  border: `1px solid ${CHART.tooltipBorder}`,
  borderRadius: 16,
  fontSize: 12,
  padding: '10px 12px',
  boxShadow: '0 18px 42px -16px rgba(16,92,110,0.34), inset 0 1px 0 rgba(255,255,255,0.8)',
  backdropFilter: 'blur(12px)',
};
