import React from 'react';
import { Check, Palette } from 'lucide-react';
import { THEMES } from '@/lib/themes';
import { useApp } from '@/lib/AppContext';
import { cn } from '@/lib/utils';

function hsl(v) { return `hsl(${v})`; }

function ThemePreview({ theme, active }) {
  const v = theme.vars;
  return (
    <div
      className="relative h-24 rounded-2xl overflow-hidden transition-transform duration-300 group-hover:scale-[1.02]"
      style={{ background: hsl(v['--background']), border: `1px solid ${hsl(v['--border'])}` }}
    >
      {/* ambient glow */}
      <div className="absolute -top-6 -left-6 w-24 h-24 rounded-full blur-2xl opacity-70" style={{ background: hsl(v['--bg-glow-1']) }} />
      <div className="absolute -bottom-8 -right-4 w-24 h-24 rounded-full blur-2xl opacity-60" style={{ background: hsl(v['--bg-glow-2']) }} />
      {/* faux card */}
      <div
        className="absolute left-3 top-3 right-10 h-12 rounded-xl flex flex-col justify-center px-2.5 gap-1"
        style={{ background: hsl(v['--card']), border: `1px solid ${hsl(v['--border'])}`, boxShadow: '0 6px 16px -8px rgba(0,0,0,0.18)' }}
      >
        <span className="h-1.5 w-10 rounded-full" style={{ background: hsl(v['--foreground']), opacity: 0.85 }} />
        <span className="h-1.5 w-16 rounded-full" style={{ background: hsl(v['--muted-foreground']), opacity: 0.6 }} />
      </div>
      {/* primary pill */}
      <div
        className="absolute right-3 top-3 h-6 px-2.5 rounded-full flex items-center text-[8px] font-semibold"
        style={{ background: hsl(v['--primary']), color: hsl(v['--primary-foreground']) }}
      >
        AVM
      </div>
      {/* chart dots */}
      <div className="absolute left-3 bottom-3 flex items-end gap-1">
        {['--chart-1', '--chart-3', '--chart-4'].map((k, i) => (
          <span key={k} className="w-2 rounded-full" style={{ height: 8 + i * 4, background: hsl(v[k]) }} />
        ))}
      </div>
      {/* active check */}
      {active && (
        <div className="absolute right-2.5 bottom-2.5 w-5 h-5 rounded-full flex items-center justify-center" style={{ background: hsl(v['--primary']), color: hsl(v['--primary-foreground']) }}>
          <Check className="w-3 h-3" strokeWidth={3} />
        </div>
      )}
    </div>
  );
}

export default function ThemePicker() {
  const { theme, setTheme } = useApp();

  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <Palette className="w-3.5 h-3.5 text-brand" />
        <span className="text-xs text-text-secondary">Escolha uma estética — a mudança é instantânea e salva neste navegador.</span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {THEMES.map((t) => {
          const active = theme === t.id;
          return (
            <button
              key={t.id}
              type="button"
              aria-pressed={active}
              onClick={() => setTheme(t.id)}
              className={cn(
                'group text-left rounded-2xl p-3 transition-all duration-200',
                active ? 'ring-2 ring-brand bg-brand/5' : 'ring-1 ring-border hover:ring-brand/40 hover:bg-elevated/50'
              )}
            >
              <ThemePreview theme={t} active={active} />
              <div className="mt-2.5 flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="text-sm font-semibold text-foreground truncate">{t.name}</div>
                  <div className="text-[10px] font-mono uppercase tracking-wide text-text-muted">{t.tagline}</div>
                </div>
              </div>
              <p className="text-[11px] text-text-muted leading-snug mt-1.5">{t.description}</p>
            </button>
          );
        })}
      </div>
    </div>
  );
}
