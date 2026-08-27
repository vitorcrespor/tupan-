import React from 'react';
import { PERSONAS, TONES, FOCUS, FOCUS_LABELS } from '@/lib/voicePersona';
import { Volume2, VolumeX } from 'lucide-react';

const Chip = ({ active, children, onClick }) => (
  <button
    onClick={onClick}
    className={`px-3 h-7 rounded-full text-[11px] font-medium border transition-all ${
      active
        ? 'bg-brand text-brand-foreground border-brand shadow-glow'
        : 'bg-surface/70 text-text-secondary border-border hover:text-foreground'
    }`}
  >
    {children}
  </button>
);

export default function PersonaPanel({ value, onChange }) {
  const set = (patch) => onChange({ ...value, ...patch });
  const toggleFocus = (f) =>
    set({ focus: value.focus.includes(f) ? value.focus.filter((x) => x !== f) : [...value.focus, f] });

  return (
    <div className="aero-glass aero-gloss rounded-3xl p-5 space-y-5 w-full">
      <div>
        <div className="text-[10px] uppercase tracking-widest text-text-muted mb-2">Seu nome</div>
        <input
          value={value.name}
          onChange={(e) => set({ name: e.target.value })}
          placeholder="Como a Ceres deve te chamar?"
          className="w-full h-9 rounded-full bg-surface/80 border border-border px-4 text-sm text-foreground outline-none focus:border-brand placeholder:text-text-muted"
        />
      </div>

      <div>
        <div className="text-[10px] uppercase tracking-widest text-text-muted mb-2">Persona</div>
        <div className="space-y-2">
          {PERSONAS.map((p) => (
            <button
              key={p.id}
              onClick={() => set({ persona: p.id })}
              className={`w-full text-left px-3.5 py-2.5 rounded-2xl border transition-all ${
                value.persona === p.id
                  ? 'bg-brand/12 border-brand/40 shadow-glow'
                  : 'bg-surface/60 border-border hover:border-brand/30'
              }`}
            >
              <div className="text-sm font-semibold text-foreground">{p.label}</div>
              <div className="text-[11px] text-text-muted">{p.blurb}</div>
            </button>
          ))}
        </div>
      </div>

      <div>
        <div className="text-[10px] uppercase tracking-widest text-text-muted mb-2">Tamanho da resposta</div>
        <div className="flex flex-wrap gap-2">
          {TONES.map((t) => (
            <Chip key={t.id} active={value.tone === t.id} onClick={() => set({ tone: t.id })}>
              {t.label}
            </Chip>
          ))}
        </div>
      </div>

      <div>
        <div className="text-[10px] uppercase tracking-widest text-text-muted mb-2">Áreas de foco</div>
        <div className="flex flex-wrap gap-2">
          {FOCUS.map((f) => (
            <Chip key={f} active={value.focus.includes(f)} onClick={() => toggleFocus(f)}>
              {FOCUS_LABELS[f] || f}
            </Chip>
          ))}
        </div>
      </div>

      <div className="pt-1 border-t border-white/60 space-y-3">
        <button
          onClick={() => set({ speak: !value.speak })}
          className="flex items-center justify-between w-full text-xs text-text-secondary"
        >
          <span className="flex items-center gap-2">
            {value.speak ? <Volume2 className="w-3.5 h-3.5 text-brand" /> : <VolumeX className="w-3.5 h-3.5" />}
            Falar as respostas em voz alta
          </span>
          <span className={`w-9 h-5 rounded-full relative transition-colors ${value.speak ? 'bg-brand' : 'bg-border'}`}>
            <span
              className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-all ${
                value.speak ? 'left-[18px]' : 'left-0.5'
              }`}
            />
          </span>
        </button>
        <div>
          <div className="flex items-center justify-between text-[10px] uppercase tracking-widest text-text-muted mb-1">
            <span>Velocidade da voz</span>
            <span className="tnum text-text-secondary">{value.rate.toFixed(1)}x</span>
          </div>
          <input
            type="range"
            min="0.7"
            max="1.4"
            step="0.1"
            value={value.rate}
            onChange={(e) => set({ rate: Number(e.target.value) })}
            className="w-full accent-brand"
          />
        </div>
      </div>
    </div>
  );
}