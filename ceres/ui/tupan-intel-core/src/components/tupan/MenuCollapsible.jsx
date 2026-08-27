import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

export default function MenuCollapsible({ items }) {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const { pathname } = useLocation();

  return (
    <div className="flex flex-col items-center w-full max-w-xs">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex items-center gap-1.5 h-7 px-3 rounded-full border border-white/50 text-text-secondary/80 hover:text-foreground transition-all duration-300 hover:border-brand/50 backdrop-blur-md"
        style={{ background: 'rgba(255,255,255,0.16)' }}
      >
        <span
          className="w-1.5 h-1.5 rounded-full"
          style={{ background: 'radial-gradient(circle at 34% 28%, hsl(188 88% 76%), hsl(188 78% 54%))', boxShadow: '0 0 6px -1px hsl(188 82% 52% / 0.6)' }}
        />
        <span className="text-[10px] font-mono tracking-[0.2em] uppercase">Menu</span>
        <svg
          viewBox="0 0 24 24"
          className="w-3 h-3 transition-transform duration-300"
          style={{ transform: open ? 'rotate(180deg)' : 'none', fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round' }}
        >
          <path d="M6 9l6 6 6-6" />
        </svg>
      </button>

      <div
        className="grid w-full"
        style={{ gridTemplateRows: open ? '1fr' : '0fr', transition: 'grid-template-rows 0.42s cubic-bezier(0.22,1,0.36,1)' }}
      >
        <div className="overflow-hidden min-h-0">
          <nav
            className="mt-3 aero-glass rounded-2xl p-2 flex flex-col gap-0.5"
            style={{ opacity: open ? 1 : 0, transition: 'opacity 0.3s ease 0.08s' }}
            aria-label="Primary"
          >
            {items.map((it, idx) => {
              const Icon = it.icon;
              const active = pathname === it.to || pathname.startsWith(it.to + '/');
              return (
                <button
                  key={it.to}
                  onClick={() => navigate(it.to)}
                  className={`flex items-center gap-2.5 w-full px-3 py-2 rounded-xl text-left text-[13px] transition-colors ${
                    active ? 'text-foreground font-semibold bg-brand/10' : 'text-muted-foreground hover:text-foreground hover:bg-foreground/[0.04]'
                  }`}
                >
                  <span className="font-mono text-[10px] text-text-muted w-5">{String(idx + 1).padStart(2, '0')}</span>
                  <Icon className="w-3.5 h-3.5 text-brand" />
                  <span className="flex-1">{it.label}</span>
                  <span className={`w-1.5 h-1.5 rounded-full ${active ? 'bg-brand' : 'bg-foreground/20'}`} />
                </button>
              );
            })}
          </nav>
        </div>
      </div>
    </div>
  );
}