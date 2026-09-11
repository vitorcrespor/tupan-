import React from 'react';
import { useAuth } from '@/lib/AuthContext';
import { useApp } from '@/lib/AppContext';
import { ChevronDown, ChevronUp } from 'lucide-react';
import OpportunityNotifications from './OpportunityNotifications';
import UserAdminMenu from './UserAdminMenu';
import { TIME_PERIODS } from '@/lib/tupanData';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

export default function TopBar({ title, subtitle, right = null, children = null }) {
  const { user } = useAuth();
  const { timePeriod, setTimePeriod, headerCollapsed, setHeaderCollapsed, navOpen, setNavOpen } = useApp();
  const collapsed = headerCollapsed;
  const initials = (user?.full_name || user?.email || 'BR').slice(0, 2).toUpperCase();

  return (
    <div className="ceres-topbar sticky top-0 z-40 shrink-0">
      <div
        className="grid"
        style={{
          gridTemplateRows: collapsed ? '0fr' : '1fr',
          transition: 'grid-template-rows 0.42s cubic-bezier(0.22,1,0.36,1)',
        }}
      >
        <div className={`${collapsed ? 'overflow-hidden' : 'overflow-visible'} min-h-0`}>
          <header
            className="ceres-topbar__header surface-panel"
            style={{ opacity: collapsed ? 0 : 1, transition: 'opacity 0.3s ease 0.08s' }}
          >
            <div className="flex min-w-0 items-center gap-3">
              <button
                onClick={() => setNavOpen((value) => !value)}
                data-main-nav-toggle
                aria-label="Abrir menu"
                aria-expanded={navOpen}
                title="Abrir menu"
                className="icon-control h-8 w-8 text-text-secondary hover:text-foreground"
              >
                <span className="w-4 h-4 rounded-full" style={{ background: 'radial-gradient(circle at 34% 28%, hsl(188 88% 76%), hsl(188 78% 54%) 52%, hsl(196 74% 42%))', boxShadow: '0 0 8px -1px hsl(188 82% 52% / 0.6)' }} />
              </button>
              <div className="flex min-w-0 flex-col gap-0.5 leading-tight">
                <h1 className="truncate font-heading text-[15px] font-semibold text-foreground" title={title}>{title}</h1>
                {subtitle && <span className="truncate text-[11px] text-text-secondary" title={subtitle}>{subtitle}</span>}
              </div>
            </div>
            <div className="ceres-topbar__actions flex items-center gap-2">
              {right}

              <Select value={timePeriod} onValueChange={setTimePeriod}>
                <SelectTrigger aria-label="Período de análise" className="h-8 w-[116px] shrink-0 px-3 text-xs text-text-secondary">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {TIME_PERIODS.map((p) => (
                    <SelectItem key={p.id} value={p.id} className="rounded-xl px-3 py-2 text-xs focus:bg-brand/10 focus:text-foreground">
                      {p.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <OpportunityNotifications />

              <UserAdminMenu user={user} initials={initials} />

              <button
                onClick={() => setHeaderCollapsed(true)}
                aria-label="Recolher cabeçalho"
                title="Recolher cabeçalho"
                className="w-8 h-8 rounded-full flex items-center justify-center text-text-muted hover:text-foreground hover:bg-foreground/5 transition-colors"
              >
                <ChevronUp className="w-4 h-4" strokeWidth={1.7} />
              </button>
            </div>
          </header>
          {children}
        </div>
      </div>
      <button
        onClick={() => setHeaderCollapsed(false)}
        aria-label="Expandir cabeçalho"
        title="Expandir cabeçalho"
        className={`icon-control absolute top-2 right-4 h-8 w-8 text-text-muted hover:text-foreground transition-opacity duration-200 ${
          collapsed ? 'opacity-100' : 'opacity-0 pointer-events-none'
        }`}
      >
        <ChevronDown className="w-4 h-4" strokeWidth={1.7} />
      </button>
    </div>
  );
}
