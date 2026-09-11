import React, { useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useApp } from '@/lib/AppContext';
import { NAV_GROUPS } from '@/lib/navGroups';
import useOutsideDismiss from '@/lib/useOutsideDismiss';

export default function VoiceNav({ showTrigger = false }) {
  const { navOpen, setNavOpen } = useApp();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const open = navOpen;
  const navRef = useRef(null);

  const go = (to) => { navigate(to); setNavOpen(false); };
  useOutsideDismiss(navRef, open, () => setNavOpen(false), { ignoreSelector: '[data-main-nav-toggle]' });

  return (
    <>
      {showTrigger && (
        <div className="h-16 shrink-0 flex items-center px-5">
          <button
            onClick={() => setNavOpen(!open)}
            data-main-nav-toggle
            aria-label="Menu"
            aria-expanded={open}
            className={`w-10 h-10 rounded-full flex items-center justify-center border transition-all ${
              open
                ? 'bg-card border-foreground/40 text-foreground'
                : 'bg-card/80 border-border text-foreground hover:border-foreground/40'
            }`}
            style={{ boxShadow: '0 6px 18px -8px rgba(20,90,105,0.25)' }}
          >
            <span className="w-4 h-4 rounded-full" style={{ background: 'radial-gradient(circle at 34% 28%, hsl(188 88% 76%), hsl(188 78% 54%) 52%, hsl(196 74% 42%))', boxShadow: '0 0 8px -1px hsl(188 82% 52% / 0.6)' }} />
          </button>
        </div>
      )}

      <div
        className="grid"
        style={{
          gridTemplateRows: open ? '1fr' : '0fr',
          transition: 'grid-template-rows 0.42s cubic-bezier(0.22,1,0.36,1)',
        }}
      >
        <div className="overflow-hidden min-h-0">
          <nav
            ref={navRef}
            className="bg-background border-y border-border"
            style={{
              boxShadow: '0 18px 40px -18px rgba(20,90,105,0.28)',
              opacity: open ? 1 : 0,
              transition: 'opacity 0.3s ease 0.08s',
            }}
            aria-label="Primary"
          >
            <div className="max-w-5xl mx-auto px-6 sm:px-10 pt-6">
              <button
                onClick={() => go('/agent')}
                className="group w-full flex items-center gap-3 p-3 rounded-2xl border border-brand/30 bg-gradient-to-br from-aqua/15 to-lagoon/10 hover:from-aqua/25 hover:to-lagoon/20 transition-all"
              >
                <span
                  className="w-9 h-9 rounded-full shrink-0"
                  style={{
                    background: 'radial-gradient(circle at 34% 28%, hsl(188 88% 76%), hsl(188 78% 54%) 52%, hsl(196 74% 42%))',
                    boxShadow: '0 0 14px -2px hsl(188 82% 52% / 0.55), inset 0 4px 10px -4px hsl(0 0% 100% / 0.6)',
                  }}
                />
                <span className="flex flex-col items-start leading-tight">
                  <span className="text-sm font-semibold text-foreground">Agente Ceres</span>
                </span>
                <span className="ml-auto text-text-muted group-hover:text-brand transition-colors">→</span>
              </button>
            </div>
            <div className="max-w-5xl mx-auto px-6 sm:px-10 pb-6 pt-4 grid grid-cols-1 sm:grid-cols-3 gap-x-8 gap-y-6">
              {NAV_GROUPS.map((g, ci) => {
                const Icon = g.icon;
                return (
                  <div key={g.title} className={ci > 0 ? 'sm:border-l border-border sm:pl-8' : ''}>
                    <div className="flex items-center gap-3 pb-3">
                      <span className="relative w-9 h-9 rounded-xl aero-glass flex items-center justify-center text-foreground">
                        <span className="absolute inset-0 rounded-xl pointer-events-none" style={{ background: 'radial-gradient(circle at 30% 40%, hsl(188 78% 52% / 0.22), transparent 70%)' }} />
                        <Icon className="relative w-4 h-4" strokeWidth={1.6} />
                      </span>
                      <span className="text-[12px] font-semibold text-foreground">{g.title}</span>
                      <span className="flex-1 h-px border-t border-border" />
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
          </nav>
        </div>
      </div>
    </>
  );
}