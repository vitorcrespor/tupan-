import React, { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LayoutDashboard, Map, Building2, Briefcase } from 'lucide-react';
import { AnimatedBeam } from '@/registry/magicui/animated-beam';
import { Ripple } from '@/registry/magicui/ripple';

const OPTIONS = [
  { label: 'Visão Geral', to: '/overview', icon: LayoutDashboard, corner: 'tl' },
  { label: 'Mapa de mercado', to: '/market-map', icon: Map, corner: 'bl' },
  { label: 'Imóveis', to: '/market-trends', icon: Building2, corner: 'tr' },
  { label: 'Portfólio', to: '/portfolio', icon: Briefcase, corner: 'br' },
];

const POS = {
  tl: { left: 'calc(50% - 250px)', top: 'calc(50% - 165px)' },
  bl: { left: 'calc(50% - 250px)', top: 'calc(50% + 120px)' },
  tr: { left: 'calc(50% + 250px)', top: 'calc(50% - 165px)' },
  br: { left: 'calc(50% + 250px)', top: 'calc(50% + 120px)' },
};

const BEAM_CFG = {
  tl: { curvature: 55, reverse: false },
  bl: { curvature: -55, reverse: false },
  tr: { curvature: -55, reverse: true },
  br: { curvature: 55, reverse: true },
};

export default function VoiceBeams({ orbRef, orb, dismissed = false, conversationActive = false, responding = false, contextArrival = false }) {
  const containerRef = useRef(null);
  const refs = { tl: useRef(null), bl: useRef(null), tr: useRef(null), br: useRef(null) };
  const navigate = useNavigate();
  const [hovered, setHovered] = useState(null);

  return (
    <div ref={containerRef} className="absolute inset-0 pointer-events-none">
      <div ref={orbRef} className={`voice-orb-position absolute left-1/2 top-1/2 z-10 ${conversationActive ? 'voice-orb-position--conversation' : ''}`}>
        <div className={`voice-orb-motion ${responding ? 'voice-orb-motion--responding' : ''}`}>
          <div className="voice-orb-ripple" aria-hidden="true"><Ripple className="opacity-80" /></div>
          {contextArrival && <span className="voice-orb-context-arrival" aria-hidden="true"><span className="voice-orb-context-arrival__flash" /><span className="voice-orb-context-arrival__wave" /><span className="voice-orb-context-arrival__wave voice-orb-context-arrival__wave--delayed" /></span>}
          <div className={contextArrival ? 'voice-orb-arrival-core' : ''}>{orb}</div>
        </div>
      </div>

      {OPTIONS.map((option, index) => {
        const Icon = option.icon;
        return (
          <div key={option.to} style={POS[option.corner]} className="absolute -translate-x-1/2 -translate-y-1/2 z-20">
            <button
              ref={refs[option.corner]}
              onClick={() => navigate(option.to)}
              onMouseEnter={() => setHovered(option.corner)}
              onMouseLeave={() => setHovered((current) => (current === option.corner ? null : current))}
              disabled={dismissed}
              tabIndex={dismissed ? -1 : undefined}
              style={{ animationDelay: `${index * 1.4}s`, animationDuration: `${8 + index * 1.7}s`, transitionDelay: dismissed ? `${index * 35}ms` : '0ms' }}
              className={`pointer-events-auto group flex items-center gap-2.5 h-12 pl-3 pr-4 rounded-2xl border border-border/70 bg-card/30 backdrop-blur-xl shadow-sm hover:bg-card/50 hover:border-brand/30 hover:shadow-soft transition-[opacity,transform,filter,background-color,border-color,box-shadow] duration-500 ease-out ${dismissed ? 'pointer-events-none scale-95 opacity-0 blur-[3px]' : 'aero-sheen vb-drift'}`}
            >
              <span className="shrink-0 w-9 h-9 rounded-xl border border-border/70 bg-elevated/70 flex items-center justify-center text-foreground/70 group-hover:border-brand/50 group-hover:text-brand group-hover:bg-brand/10 transition-all">
                <Icon className="w-4 h-4" strokeWidth={1.6} />
              </span>
              <span className="text-[12.5px] font-medium text-foreground/85 group-hover:text-foreground whitespace-nowrap transition-colors text-center">{option.label}</span>
            </button>
          </div>
        );
      })}

      <div aria-hidden="true" className={`absolute inset-0 z-0 transition-[opacity,filter] duration-500 ease-out ${dismissed ? 'opacity-0 blur-[2px]' : 'opacity-100'}`}>
        {OPTIONS.map((option, index) => (
          <AnimatedBeam key={option.to} containerRef={containerRef} fromRef={refs[option.corner]} toRef={orbRef} curvature={BEAM_CFG[option.corner].curvature} reverse={BEAM_CFG[option.corner].reverse} active={hovered === option.corner} pathWidth={1} duration={4.5 + index * 0.5} delay={index * 0.3} pathColor="hsl(var(--border))" pathOpacity={0.06} gradientStartColor="hsl(var(--aqua))" gradientStopColor="hsl(var(--lagoon))" refreshKey={conversationActive} refreshDuration={720} />
        ))}
      </div>
    </div>
  );
}