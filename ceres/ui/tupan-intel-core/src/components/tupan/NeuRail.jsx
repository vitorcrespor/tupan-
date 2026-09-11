import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, Map, Briefcase, Sparkles, Settings, X, ChevronLeft, Menu,
} from 'lucide-react';
import Orb2D from '@/components/tupan/Orb2D';

const GROUPS = [
  {
    label: 'Workspace',
    items: [
      { key: 'overview', label: 'Overview', icon: LayoutDashboard, to: '/overview' },
      {
        key: 'market', label: 'Market', icon: Map, sub: [
          { label: 'Market Map', to: '/market-map' },
        ],
      },
      {
        key: 'portfolio', label: 'Portfolio', icon: Briefcase, sub: [
          { label: 'Portfolio', to: '/portfolio' },
          { label: 'Properties', to: '/properties' },
        ],
      },
    ],
  },
  {
    label: 'Intelligence',
    items: [
      {
        key: 'agent', label: 'Ceres Agent', icon: Sparkles, sub: [
          { label: 'Intelligence Agent', to: '/agent' },
          { label: 'Voice Agent', to: '/voice' },
          { label: 'Agent Log', to: '/agent-log' },
        ],
      },
      {
        key: 'admin', label: 'Settings', icon: Settings, sub: [
          { label: 'Data Management', to: '/data' },
          { label: 'General Settings', to: '/settings' },
        ],
      },
    ],
  },
];

const ALL_ITEMS = GROUPS.flatMap((g) => g.items);

export default function NeuRail() {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [openKey, setOpenKey] = useState(null);
  const [collapsed, setCollapsed] = useState(false);

  const activeKey = useMemo(() => {
    const match = ALL_ITEMS.find((it) =>
      it.to === pathname || (it.sub || []).some((s) => pathname.startsWith(s.to))
    );
    return match?.key || null;
  }, [pathname]);

  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') setOpenKey(null); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const openItem = ALL_ITEMS.find((it) => it.key === openKey) || null;

  return (
    <>
      <style>{`
        .neu-rail{
          --neu-surface: hsl(190 46% 96%);
          --neu-surface-2: hsl(190 40% 93%);
          --neu-light: hsl(0 0% 100% / .95);
          --neu-dark: hsl(196 32% 66% / .55);
          background: var(--neu-surface);
          box-shadow: 0 14px 32px -12px hsl(196 60% 30% / .22), 0 2px 6px hsl(196 50% 40% / .10),
            inset 0 1px 0 hsl(0 0% 100% / .7);
          transition: border-radius .38s cubic-bezier(.6,.02,.1,1);
        }
        .neu-divider{
          background: var(--neu-surface);
          box-shadow: inset 1px 1px 2px var(--neu-dark), inset -1px -1px 2px var(--neu-light);
        }
        .neu-btn{
          background: linear-gradient(145deg, var(--neu-surface), var(--neu-surface-2));
          box-shadow: -3px -3px 6px var(--neu-light), 3px 3px 6px var(--neu-dark);
          transition: box-shadow .22s ease, color .22s ease, background .22s ease;
        }
        .neu-btn:hover, .neu-btn:focus-visible{
          outline: none;
          box-shadow: inset 2px 2px 5px var(--neu-dark), inset -2px -2px 5px var(--neu-light);
        }
        .neu-btn[data-active="true"]{
          background: linear-gradient(145deg, hsl(178 60% 84%), hsl(174 62% 66%));
          box-shadow: inset 2px 2px 5px hsl(180 40% 45% / .45),
            inset -2px -2px 5px hsl(0 0% 100% / .7), 0 0 12px hsl(180 70% 50% / .3);
        }
        .neu-socket{
          box-shadow: inset 2px 2px 4px var(--neu-dark), inset -2px -2px 4px var(--neu-light);
        }
        .neu-dark-btn{
          background: radial-gradient(120% 120% at 35% 30%, hsl(200 22% 26%), hsl(200 24% 19%));
          box-shadow: -2px -2px 4px hsl(0 0% 100% / .6), 2px 2px 5px hsl(200 30% 40% / .5);
          transition: box-shadow .2s ease;
        }
        .neu-dark-btn:hover, .neu-dark-btn:focus-visible{
          outline: none;
          box-shadow: inset 1px 1px 3px hsl(0 0% 0% / .45), inset -1px -1px 3px hsl(0 0% 100% / .15);
        }
        .neu-panel{ flex-basis:0; transition: flex-basis .32s cubic-bezier(.22,1,.36,1); }
        .neu-rail[data-open="true"] .neu-panel{ flex-basis:214px; }
        .neu-panel-inner{
          box-shadow: inset 5px 0 8px -6px var(--neu-dark);
          opacity:0; transform: translateX(6px);
          transition: opacity .28s ease .06s, transform .3s ease .06s;
        }
        .neu-rail[data-open="true"] .neu-panel-inner{ opacity:1; transform:none; }
        @media (prefers-reduced-motion: reduce){
          .neu-rail, .neu-panel, .neu-panel-inner, .neu-btn{ transition:none; }
        }
      `}</style>

      {collapsed ? (
        <div className="shrink-0 h-screen sticky top-0">
          <button
            type="button"
            aria-label="Expand navigation"
            aria-expanded={false}
            title="Expand navigation"
            onClick={() => setCollapsed(false)}
            className="neu-btn absolute top-5 left-5 z-40 w-[42px] h-[42px] rounded-full flex items-center justify-center text-text-muted"
          >
            <Menu className="w-4 h-4" />
          </button>
        </div>
      ) : (
        <div className="shrink-0 h-screen sticky top-0 flex items-center px-3 py-8">
          <nav
            aria-label="Primary"
            data-open={openItem ? 'true' : 'false'}
            className="neu-rail flex flex-row items-stretch rounded-[26px] overflow-hidden"
          >
            <div className="shrink-0 flex flex-col gap-1.5 p-2 items-stretch w-[196px]">
              <button
                type="button"
                onClick={() => { setOpenKey(null); navigate('/voice'); }}
                aria-label="Talk to Ceres"
                aria-current={pathname === '/voice' ? 'page' : undefined}
                title="Talk to Ceres"
                className="neu-socket rounded-full flex items-center h-[38px] gap-2.5 pl-1 pr-3.5"
              >
                <Orb2D size={30} drift={6} />
                <span className="text-[13px] font-semibold tracking-tight text-foreground whitespace-nowrap">Talk to Ceres</span>
              </button>

              {GROUPS.map((group) => (
                <React.Fragment key={group.label}>
                  <div role="separator" className="neu-divider h-[3px] my-[5px] rounded-full w-full" />
                  <span className="px-3 pb-0.5 text-[9px] font-semibold uppercase tracking-[0.16em] text-text-muted">{group.label}</span>
                  <ul aria-label={group.label} className="list-none m-0 p-0 flex flex-col gap-1.5 items-stretch">
                    {group.items.map((item) => {
                      const Icon = item.icon;
                      const isActive = activeKey === item.key;
                      return (
                        <li key={item.key} className="relative group">
                          <button
                            type="button"
                            aria-label={item.label}
                            aria-haspopup={item.sub ? 'true' : undefined}
                            aria-expanded={item.sub ? openKey === item.key : undefined}
                            aria-current={isActive ? 'page' : undefined}
                            data-active={isActive}
                            onClick={() => {
                              if (item.sub) setOpenKey(openKey === item.key ? null : item.key);
                              else { setOpenKey(null); navigate(item.to); }
                            }}
                            className={`neu-btn h-[38px] rounded-full flex items-center cursor-pointer w-full gap-2.5 px-3.5 ${isActive ? 'text-[hsl(186_70%_22%)]' : 'text-text-muted'}`}
                          >
                            <Icon className="w-[16px] h-[16px] shrink-0" strokeWidth={1.7} />
                            <span className={`text-[13px] whitespace-nowrap ${isActive ? 'font-semibold' : 'font-medium text-text-secondary'}`}>{item.label}</span>
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                </React.Fragment>
              ))}

              <div className="neu-divider h-[3px] my-[5px] rounded-full w-full" />
              <button
                type="button"
                aria-label="Collapse navigation"
                aria-expanded={false}
                title="Collapse navigation"
                onClick={() => { setCollapsed(true); setOpenKey(null); }}
                className="neu-btn h-[38px] rounded-full flex items-center cursor-pointer text-text-muted w-full gap-2.5 px-3.5"
              >
                <ChevronLeft className="w-[15px] h-[15px]" />
                <span className="text-[13px] font-medium whitespace-nowrap">Collapse</span>
              </button>
            </div>

            <div className="neu-panel shrink-0 overflow-hidden">
              <div
                aria-hidden={!openItem}
                className="neu-panel-inner w-[214px] h-full box-border pt-4 pr-4 pb-[18px] pl-3.5 flex flex-col gap-3"
              >
                <div className="flex items-center justify-between gap-2.5">
                  <span className="text-sm font-semibold tracking-tight text-foreground whitespace-nowrap">
                    {openItem?.label}
                  </span>
                  <button
                    type="button"
                    aria-label="Close submenu"
                    onClick={() => setOpenKey(null)}
                    className="neu-dark-btn shrink-0 w-[30px] h-[30px] rounded-full flex items-center justify-center text-[hsl(190_40%_94%)]"
                  >
                    <X className="w-3.5 h-3.5" />
                  </button>
                </div>
                <ul className="list-none m-0 p-0 flex flex-col gap-2">
                  {(openItem?.sub || []).map((s) => {
                    const current = pathname.startsWith(s.to);
                    return (
                      <li key={s.to}>
                        <button
                          type="button"
                          aria-current={current ? 'true' : undefined}
                          data-active={current}
                          onClick={() => navigate(s.to)}
                          className={`neu-btn w-full text-left rounded-xl px-3.5 py-2.5 text-[13px] font-medium cursor-pointer ${current ? 'text-[hsl(186_70%_22%)]' : 'text-text-secondary'}`}
                        >
                          {s.label}
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </div>
            </div>
          </nav>
        </div>
      )}
    </>
  );
}