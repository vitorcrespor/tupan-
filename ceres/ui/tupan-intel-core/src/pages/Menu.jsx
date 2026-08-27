import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import HologramSphere from '@/components/tupan/HologramSphere';
import { Ripple } from '@/registry/magicui/ripple';
import MenuCollapsible from '@/components/tupan/MenuCollapsible';
import { LayoutDashboard, Map, Briefcase, Building2, Activity, Database, Settings, Mic, Send } from 'lucide-react';

const ITEMS = [
  { to: '/overview', label: 'Visão Geral', icon: LayoutDashboard },
  { to: '/market-map', label: 'Mapa de mercado', icon: Map },
  { to: '/portfolio', label: 'Portfólio', icon: Briefcase },
  { to: '/properties', label: 'Imóveis', icon: Building2 },
  { to: '/agent-log', label: 'Registro do agente', icon: Activity },
  { to: '/data', label: 'Dados', icon: Database },
  { to: '/settings', label: 'Configurações', icon: Settings },
];

export default function Menu() {
  const navigate = useNavigate();
  const [q, setQ] = useState('');

  const send = () => navigate(q.trim() ? `/voice?q=${encodeURIComponent(q.trim())}` : '/voice');

  return (
    <div className="w-full">
      <div className="min-h-screen grid-bg flex flex-col items-center justify-between px-6 py-8">
        <div className="text-center">
        <h1 className="text-xl font-semibold tracking-[0.3em] text-foreground">CERES</h1>
        <p className="text-[10px] uppercase tracking-[0.3em] text-text-muted mt-1">Fale — ou escolha uma sala</p>
      </div>

      {/* Voice core with a collapsible menu below */}
      <div className="hidden md:flex flex-col items-center gap-5">
        <div className="relative w-[340px] h-[340px] flex items-center justify-center">
          <Ripple className="opacity-70" />
          <button
            onClick={() => navigate('/voice')}
            className="relative rounded-full transition-transform duration-300 hover:scale-[1.03]"
            title="Falar com Ceres"
          >
            <HologramSphere size={300} />
            <span className="absolute inset-0 flex flex-col items-center justify-center gap-1.5 pointer-events-none">
              <span className="w-12 h-12 rounded-full aero-glass flex items-center justify-center text-brand shadow-glow">
                <Mic className="w-5 h-5" />
              </span>
              <span className="text-[10px] uppercase tracking-[0.25em] text-text-secondary">Falar</span>
            </span>
          </button>
        </div>
        <MenuCollapsible items={ITEMS} />
      </div>

      {/* Mobile fallback */}
      <div className="md:hidden flex flex-col items-center gap-5 w-full max-w-sm">
        <button onClick={() => navigate('/voice')} className="relative">
          <HologramSphere size={220} points={1800} />
          <span className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <span className="w-11 h-11 rounded-full aero-glass flex items-center justify-center text-brand shadow-glow">
              <Mic className="w-5 h-5" />
            </span>
          </span>
        </button>
        <MenuCollapsible items={ITEMS} />
      </div>

      {/* Single chat bar */}
      <div className="w-full max-w-xl">
        <div className="aero-glass aero-gloss rounded-full h-12 flex items-center gap-2 pl-5 pr-2">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && send()}
            placeholder="Ou digite uma pergunta…"
            className="flex-1 bg-transparent outline-none text-sm text-foreground placeholder:text-text-muted"
          />
          <button
            onClick={send}
            className="w-9 h-9 rounded-full bg-brand text-brand-foreground flex items-center justify-center shadow-glow"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
      </div>
    </div>
  );
}