import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { X } from 'lucide-react';
import { useApp } from '@/lib/AppContext';
import { NAV_GROUPS } from '@/lib/navGroups';

export default function MenuWindow() {
  const { navOpen, setNavOpen } = useApp();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  if (!navOpen) return null;

  const go = (to) => {
    navigate(to);
    setNavOpen(false);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-black/15 backdrop-blur-[3px]"
        onClick={() => setNavOpen(false)}
      />
      <div className="relative w-[min(92vw,640px)] aero-glass aero-gloss rounded-3xl p-6 shadow-soft-lg ab9-drop">
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2.5">
            <span
              className="w-2 h-2 rounded-full"
              style={{
                background: 'radial-gradient(circle at 34% 28%, hsl(188 88% 76%), hsl(188 78% 54%))',
                boxShadow: '0 0 8px -1px hsl(188 82% 52% / 0.6)',
              }}
            />
            <span className="font-mono text-[11px] tracking-[0.3em] uppercase text-text-secondary">
              Ceres · Menu
            </span>
          </div>
          <button
            onClick={() => setNavOpen(false)}
            aria-label="Fechar menu"
            className="w-8 h-8 rounded-full border border-border bg-surface/60 flex items-center justify-center text-text-muted hover:text-foreground hover:bg-surface transition-colors"
          >
            <X className="w-4 h-4" strokeWidth={1.7} />
          </button>
        </div>

        <button
          onClick={() => go('/agent')}
          className="group relative w-full mb-5 flex items-center gap-3 p-3 rounded-2xl border border-brand/30 bg-gradient-to-br from-aqua/15 to-lagoon/10 hover:from-aqua/25 hover:to-lagoon/20 transition-all"
        >
          <span
            className="w-10 h-10 rounded-full shrink-0"
            style={{
              background: 'radial-gradient(circle at 34% 28%, hsl(188 88% 76%), hsl(188 78% 54%) 52%, hsl(196 74% 42%))',
              boxShadow: '0 0 16px -2px hsl(188 82% 52% / 0.55), inset 0 4px 10px -4px hsl(0 0% 100% / 0.6)',
            }}
          />
          <span className="flex flex-col items-start leading-tight">
            <span className="text-sm font-semibold text-foreground">Agente Ceres</span>
            <span className="text-[11px] text-text-secondary">Pergunte à inteligência</span>
          </span>
          <span className="ml-auto text-text-muted group-hover:text-brand transition-colors">→</span>
        </button>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-x-8 gap-y-6">
          {NAV_GROUPS.map((g, ci) => {
            const Icon = g.icon;
            return (
              <div key={g.title} className={ci > 0 ? 'sm:border-l border-dashed border-border sm:pl-8' : ''}>
                <div className="flex items-center gap-3 pb-3">
                  <span className="w-8 h-8 rounded-lg border border-foreground/30 flex items-center justify-center text-foreground">
                    <Icon className="w-4 h-4" strokeWidth={1.6} />
                  </span>
                  <span className="font-mono text-sm text-foreground">{g.title}</span>
                </div>
                <ul className="flex flex-col gap-0.5">
                  {g.items.map((it) => {
                    const active = pathname === it.to || pathname.startsWith(it.to + '/');
                    return (
                      <li key={it.to}>
                        <button
                          onClick={() => go(it.to)}
                          className={`flex items-center gap-2.5 w-full pl-1 pr-2.5 py-2 rounded-lg text-left text-[13px] transition-colors ${
                            active
                              ? 'text-foreground font-semibold'
                              : 'text-muted-foreground hover:text-foreground hover:bg-foreground/[0.04]'
                          }`}
                        >
                          <span className={`w-[7px] h-[7px] rounded-full shrink-0 ${active ? 'bg-brand' : 'bg-foreground/25'}`} />
                          {it.label}
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}