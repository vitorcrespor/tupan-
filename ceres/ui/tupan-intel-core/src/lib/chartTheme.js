// Shared chart palette resolved from the active Ceres theme.
// CSS custom properties keep Recharts surfaces and series aligned with every theme.
export const CHART = {
  aqua: 'hsl(var(--aqua))',
  lagoon: 'hsl(var(--lagoon))',
  teal: 'hsl(var(--chart-1))',
  mint: 'hsl(var(--chart-2))',
  sky: 'hsl(var(--chart-5))',
  positive: 'hsl(var(--positive))',
  negative: 'hsl(var(--negative))',
  warning: 'hsl(var(--warning))',
  grid: 'hsl(var(--border) / 0.72)',
  axis: 'hsl(var(--text-secondary))',
  tooltipBg: 'hsl(var(--surface-popover))',
  tooltipBorder: 'hsl(var(--edge-subtle))',
  tooltipLabel: 'hsl(var(--foreground))',
};

export const tooltipStyle = {
  background: CHART.tooltipBg,
  border: `1px solid ${CHART.tooltipBorder}`,
  borderRadius: 14,
  fontSize: 12,
  padding: '10px 12px',
  color: CHART.tooltipLabel,
  boxShadow: '0 18px 42px -22px hsl(var(--surface-shadow)), inset 0 1px 0 hsl(var(--surface-highlight))',
  backdropFilter: 'blur(12px)',
};
