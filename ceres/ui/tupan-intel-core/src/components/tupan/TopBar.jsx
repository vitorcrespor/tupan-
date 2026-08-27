import React from 'react';
import { useAuth } from '@/lib/AuthContext';
import { useApp } from '@/lib/AppContext';
import { Search, ChevronDown, ChevronUp } from 'lucide-react';
import OpportunityNotifications from './OpportunityNotifications';
import UserAdminMenu from './UserAdminMenu';
import { TIME_PERIODS } from '@/lib/tupanData';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

export default function TopBar({ title, subtitle, right, children }) {
  const { user } = useAuth();
  const { timePeriod, setTimePeriod, headerCollapsed, setHeaderCollapsed, navOpen, setNavOpen } = useApp();
  const collapsed = headerCollapsed;
  const initials = (user?.full_name || user?.email || 'BR').slice(0, 2).toUpperCase();

  return (
    <div className="sticky top-0 z-20 relative">
      <div
        className="grid"
        style={{
          gridTemplateRows: collapsed ? '0fr' : '1fr',
          transition: 'grid-template-rows 0.42s cubic-bezier(0.22,1,0.36,1)',
        }}
      >
        <div className={`${collapsed ? 'overflow-hidden' : 'overflow-visible'} min-h-0`}>
          <header
            className="h-12 flex items-center justify-between px-5 border-b border-border/80 bg-gradient-to-r from-card/80 via-card/58 to-card/74 shadow-[0_6px_20px_hsl(var(--foreground)/0.10),inset_0_1px_0_hsl(0_0%_100%/0.16),inset_0_-1px_0_hsl(var(--border)/0.18)] backdrop-blur-2xl"
            style={{ opacity: collapsed ? 0 : 1, transition: 'opacity 0.3s ease 0.08s' }}
          >
            <div className="flex items-center gap-3">
              <button
                onClick={() => setNavOpen(!navOpen)}
                aria-label="Open menu"
                title="Open menu"
                className="w-8 h-8 rounded-full flex items-center justify-center text-text-secondary hover:text-foreground hover:bg-foreground/5 transition-colors"
              >
                <span className="w-4 h-4 rounded-full" style={{ background: 'radial-gradient(circle at 34% 28%, hsl(188 88% 76%), hsl(188 78% 54%) 52%, hsl(196 74% 42%))', boxShadow: '0 0 8px -1px hsl(188 82% 52% / 0.6)' }} />
              </button>
              <div className="flex flex-col leading-tight">
                <h1 className="text-sm font-mono text-foreground tracking-wide">{title}</h1>
                {subtitle && <span className="text-[11px] font-mono text-text-muted tracking-wide">{subtitle}</span>}
              </div>
            </div>
            <div className="flex items-center gap-2">
              {right}
              <div className="hidden md:flex items-center gap-1.5 px-3 h-8 rounded-full border border-border/80 bg-card/38 text-text-muted text-xs shadow-[0_2px_8px_hsl(var(--foreground)/0.08),inset_0_1px_0_hsl(0_0%_100%/0.16)] backdrop-blur-2xl">
                <Search className="w-3.5 h-3.5" />
                <input placeholder="Buscar…" className="bg-transparent outline-none w-40 placeholder:text-text-muted text-text-secondary" />
                <kbd className="text-[9px] px-1 rounded bg-elevated border border-border">⌘K</kbd>
              </div>
              <Select value={timePeriod} onValueChange={setTimePeriod}>
                <SelectTrigger className="h-8 w-[116px] px-3 text-xs text-text-secondary">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="rounded-2xl border-border/80 bg-card/95 p-1.5 shadow-[0_18px_38px_hsl(196_42%_24%/0.2)] backdrop-blur-xl">
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
                aria-label="Collapse header"
                title="Collapse header"
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
        aria-label="Expand header"
        title="Expand header"
        className={`absolute top-2 right-4 w-8 h-8 rounded-full flex items-center justify-center text-text-muted hover:text-foreground bg-card/60 border border-border/70 backdrop-blur-md transition-opacity duration-200 ${
          collapsed ? 'opacity-100' : 'opacity-0 pointer-events-none'
        }`}
      >
        <ChevronDown className="w-4 h-4" strokeWidth={1.7} />
      </button>
    </div>
  );
}




