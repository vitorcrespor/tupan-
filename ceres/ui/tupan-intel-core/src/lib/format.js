export const formatBRL = (n) => {
  if (n == null || Number.isNaN(n)) return '—';
  return 'R$ ' + Math.round(n).toLocaleString('pt-BR');
};

export const formatBRLCompact = (n) => {
  if (n == null || Number.isNaN(n)) return '—';
  const abs = Math.abs(n);
  if (abs >= 1e9) return 'R$ ' + (n / 1e9).toFixed(2) + 'B';
  if (abs >= 1e6) return 'R$ ' + (n / 1e6).toFixed(1) + 'M';
  if (abs >= 1e3) return 'R$ ' + (n / 1e3).toFixed(0) + 'K';
  return 'R$ ' + Math.round(n);
};

export const formatNumber = (n) => (n == null || Number.isNaN(n) ? '—' : n.toLocaleString('pt-BR'));

export const formatPct = (n, withSign = true) => {
  if (n == null || Number.isNaN(n)) return '—';
  const s = n > 0 && withSign ? '+' : '';
  return s + n.toFixed(1) + '%';
};

export const formatM2 = (n) =>
  n == null || Number.isNaN(n) ? '—' : 'R$ ' + Math.round(n).toLocaleString('pt-BR');

export const classColor = (cls) =>
  ({ Overpriced: 'text-negative', Underpriced: 'text-positive', 'Fair Value': 'text-text-secondary' }[cls] || 'text-text-secondary');

export const classBadge = (cls) =>
  ({
    Overpriced: 'bg-negative/10 text-negative border-negative/20',
    Underpriced: 'bg-positive/10 text-positive border-positive/20',
    'Fair Value': 'bg-brand/10 text-brand border-brand/20',
  }[cls] || 'bg-muted text-muted-foreground border-border');

export const heatColor = (h) => {
  if (h >= 75) return '#3FD6A8';
  if (h >= 60) return '#2FBFD1';
  if (h >= 45) return '#4A90D9';
  return '#6E7BC4';
};

export const heatRgb = (h) => {
  if (h >= 75) return [63, 214, 168];
  if (h >= 60) return [47, 191, 209];
  if (h >= 45) return [74, 144, 217];
  return [110, 123, 196];
};

export const heatLabel = (h) => {
  if (h >= 75) return 'Forte';
  if (h >= 60) return 'Moderado';
  if (h >= 45) return 'Frio';
  return 'Fraco';
};

export const demandColor = (d) =>
  ({ High: 'text-positive', Medium: 'text-warning', Low: 'text-negative' }[d] || 'text-text-secondary');