import React, { useEffect, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Activity, ChevronDown, Database, FileText, Settings, UsersRound } from 'lucide-react';

const ADMIN_ITEMS = [
  { label: 'Gestão de dados', to: '/data', icon: Database, description: 'Dados imobiliários' },
  { label: 'Registro do agente', to: '/agent-log', icon: Activity, description: 'Atividade e rastros' },
  { label: 'Gerador de relatórios', to: '/report-builder', icon: FileText, description: 'Relatórios de mercado' },
  { label: 'Gestão de equipe', to: '/team-management', icon: UsersRound, description: 'Acesso e equipe' },
  { label: 'Configurações', to: '/settings', icon: Settings, description: 'Preferências da conta' },
];

export default function UserAdminMenu({ user, initials }) {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);
  const [rendered, setRendered] = useState(false);
  const ref = useRef(null);
  const closeTimerRef = useRef(null);
  const name = user?.full_name || user?.email || 'Corretor';

  const openMenu = () => {
    window.clearTimeout(closeTimerRef.current);
    setRendered(true);
    setOpen(true);
  };

  const closeMenu = () => {
    if (!rendered) return;
    setOpen(false);
    window.clearTimeout(closeTimerRef.current);
    closeTimerRef.current = window.setTimeout(() => setRendered(false), 180);
  };

  useEffect(() => {
    const closeOnOutsidePointer = (event) => {
      if (ref.current && !ref.current.contains(event.target)) closeMenu();
    };

    document.addEventListener('pointerdown', closeOnOutsidePointer);
    return () => {
      document.removeEventListener('pointerdown', closeOnOutsidePointer);
      window.clearTimeout(closeTimerRef.current);
    };
  }, [rendered]);

  const go = (to) => {
    navigate(to);
    closeMenu();
  };

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => (open ? closeMenu() : openMenu())}
        aria-label="Abrir menu da conta"
        aria-expanded={open}
        className={`flex h-8 items-center gap-2 rounded-full border border-border/80 bg-card/38 py-0.5 pl-2 pr-1 text-text-secondary shadow-[0_2px_8px_hsl(var(--foreground)/0.08),inset_0_1px_0_hsl(0_0%_100%/0.16)] backdrop-blur-2xl transition-colors hover:text-foreground ${open ? 'border-brand/35 bg-brand/10 text-foreground' : ''}`}
      >
        <span className="flex h-5 w-5 items-center justify-center rounded-full border border-brand/30 bg-brand/20 text-[10px] font-semibold text-brand">{initials}</span>
        <span className="max-w-[120px] truncate text-xs">{name}</span>
        <ChevronDown className={`h-3.5 w-3.5 text-text-muted transition-transform ${open ? 'rotate-180' : ''}`} />
      </button>

      {rendered && (
        <aside className={`user-admin-menu ${open ? 'user-admin-menu--enter' : 'user-admin-menu--exit'} absolute right-0 top-10 z-50 w-[276px] overflow-hidden rounded-[20px] border border-border/85 bg-[linear-gradient(145deg,hsl(var(--card)/.97),hsl(var(--elevated)/.86))] shadow-[0_22px_56px_hsl(var(--foreground)/.22),inset_0_1px_0_hsl(0_0%_100%/.16)] backdrop-blur-2xl`}>
          <div className="border-b border-border/65 px-3.5 py-3">
            <div className="flex items-center gap-2.5">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-xl border border-brand/25 bg-brand/10 text-xs font-semibold text-brand">{initials}</span>
              <div className="min-w-0">
                <p className="truncate text-xs font-semibold text-foreground">{name}</p>
                <p className="mt-0.5 text-[10px] text-text-muted">Painel da conta</p>
              </div>
            </div>
          </div>
          <div className="p-2">
            <p className="px-2.5 pb-1.5 pt-1 text-[9px] font-bold uppercase tracking-[0.15em] text-text-muted">Administrativo</p>
            <div className="space-y-1">
              {ADMIN_ITEMS.map((item) => {
                const Icon = item.icon;
                const active = pathname === item.to || pathname.startsWith(`${item.to}/`);
                return (
                  <button
                    key={item.to}
                    type="button"
                    onClick={() => go(item.to)}
                    className={`flex w-full items-center gap-2.5 rounded-xl px-2.5 py-2 text-left transition-colors ${active ? 'bg-brand/10 text-foreground' : 'text-text-secondary hover:bg-brand/8 hover:text-foreground'}`}
                  >
                    <span className={`grid h-7 w-7 shrink-0 place-items-center rounded-lg border ${active ? 'border-brand/30 bg-brand/15 text-brand' : 'border-border/70 bg-card/45 text-text-muted'}`}><Icon className="h-3.5 w-3.5" /></span>
                    <span className="min-w-0 flex-1"><span className="block text-[11px] font-medium">{item.label}</span><span className="block truncate text-[9px] text-text-muted">{item.description}</span></span>
                  </button>
                );
              })}
            </div>
          </div>
        </aside>
      )}
    </div>
  );
}
