import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Map, Briefcase, Building2, Sparkles, Activity, Database, Settings,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import OrbModel from '@/components/tupan/OrbModel';

const NAV = [
  { to: '/overview', label: 'Overview', icon: LayoutDashboard },
  { to: '/market-map', label: 'Market Map', icon: Map },
  { to: '/portfolio', label: 'Portfolio', icon: Briefcase },
  { to: '/properties', label: 'Properties', icon: Building2 },
  { to: '/agent', label: 'Intelligence Agent', icon: Sparkles },
  { to: '/agent-log', label: 'Agent Log', icon: Activity },
  { to: '/data', label: 'Data', icon: Database },
  { to: '/settings', label: 'Settings', icon: Settings },
];

export default function Sidebar() {
  return (
    <aside className="w-[208px] shrink-0 h-screen sticky top-0 border-r border-border bg-background flex flex-col">
      <NavLink
        to="/voice"
        title="Talk to Ceres"
        className="h-12 flex items-center gap-1.5 px-3 border-b border-border hover:bg-elevated/60 transition-colors"
      >
        <OrbModel size={30} />
        <div className="flex flex-col leading-none">
          <span className="text-sm font-bold tracking-tight text-foreground">CERES</span>
          <span className="text-[9px] text-text-muted tracking-wider uppercase">Intelligence</span>
        </div>
      </NavLink>
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5">
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-2.5 px-3 py-1.5 rounded-full text-[13px] transition-colors',
                isActive
                  ? 'bg-brand/10 text-brand font-medium shadow-soft'
                  : 'text-text-secondary hover:text-foreground hover:bg-elevated/60'
              )
            }
          >
            <Icon className="w-4 h-4 shrink-0" />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="px-3 py-2.5 border-t border-border text-[10px] text-text-muted">
        <div className="flex items-center justify-between">
          <span>Ceres v2.4</span>
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-positive" /> Online
          </span>
        </div>
      </div>
    </aside>
  );
}