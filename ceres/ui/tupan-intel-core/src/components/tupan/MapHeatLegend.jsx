import React from 'react';

const BANDS = [
  { c: '#3FD6A8', l: 'Forte (75+)' },
  { c: '#2FBFD1', l: 'Moderado (60–74)' },
  { c: '#4A90D9', l: 'Frio (45–59)' },
  { c: '#6E7BC4', l: 'Fraco (<45)' },
];

export default function MapHeatLegend() {
  return (
    <div className="aero-glass aero-gloss rounded-2xl p-3.5 space-y-2 pointer-events-none">
      <div className="text-[10px] uppercase tracking-widest text-text-muted">Aquecimento de mercado</div>
      {BANDS.map((x) => (
        <div key={x.l} className="flex items-center gap-2.5">
          <span
            className="w-4 h-4 rounded-md shadow-glow"
            style={{ background: `linear-gradient(160deg, ${x.c}, ${x.c}bb)` }}
          />
          <span className="text-[11px] text-text-secondary">{x.l}</span>
        </div>
      ))}
      <div className="pt-1.5 border-t border-white/60 text-[9px] leading-relaxed text-text-muted">
        A cor representa o aquecimento · as áreas são células H3 calculadas
      </div>
    </div>
  );
}
