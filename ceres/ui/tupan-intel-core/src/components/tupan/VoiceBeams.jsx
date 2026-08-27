import React, { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LayoutDashboard, Map, Building2, Briefcase } from 'lucide-react';
import { AnimatedBeam } from '@/registry/magicui/animated-beam';

const OPTIONS = [
  { idx: '01', label: 'Visão Geral', to: '/overview', icon: LayoutDashboard, corner: 'tl' },
  { idx: '02', label: 'Mapa de mercado', to: '/market-map', icon: Map, corner: 'bl' },
  { idx: '03', label: 'Imóveis', to: '/market-trends', icon: Building2, corner: 'tr' },
  { idx: '04', label: 'Portfólio', to: '/portfolio', icon: Briefcase, corner: 'br' },
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

export default function VoiceBeams({ orbRef, orb }) {
  const containerRef = useRef(null);
  const refs = {
    tl: useRef(null),
    bl: useRef(null),
    tr: useRef(null),
    br: useRef(null),
  };
  const navigate = useNavigate();
  const [hovered, setHovered] = useState(null);

  return (
    <div ref={containerRef} className="absolute inset-0">
      {/* center orb */}
      <div
        ref={orbRef}
        className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-10"
      >
        {orb}
      </div>

      {/* four option nodes */}
      {OPTIONS.map((o, i) => {
        const Icon = o.icon;
        return (
          <div key={o.to} style={POS[o.corner]} className="absolute -translate-x-1/2 -translate-y-1/2 z-20">
            <button
              ref={refs[o.corner]}
              onClick={() => navigate(o.to)}
              onMouseEnter={() => setHovered(o.corner)}
              onMouseLeave={() => setHovered((h) => (h === o.corner ? null : h))}
              style={{ animationDelay: `${i * 1.4}s`, animationDuration: `${8 + i * 1.7}s` }}
              className="pointer-events-auto group flex items-center gap-2.5 h-12 pl-3 pr-4 rounded-2xl border border-border/70 bg-card/30 backdrop-blur-xl shadow-sm hover:bg-card/50 hover:border-brand/30 hover:shadow-soft transition-all duration-300 aero-sheen vb-drift"
            >
              <span className="shrink-0 w-9 h-9 rounded-xl border border-border/70 bg-elevated/70 flex items-center justify-center text-foreground/70 group-hover:border-brand/50 group-hover:text-brand group-hover:bg-brand/10 transition-all">
                <Icon className="w-4 h-4" strokeWidth={1.6} />
              </span>
              <span className="text-[12.5px] font-medium text-foreground/85 group-hover:text-foreground whitespace-nowrap transition-colors text-center">
                {o.label}
              </span>
            </button>
          </div>
        );
      })}

      {/* animated beams from each node to the orb */}
      {OPTIONS.map((o, i) => (
        <AnimatedBeam
          key={o.to}
          containerRef={containerRef}
          fromRef={refs[o.corner]}
          toRef={orbRef}
          curvature={BEAM_CFG[o.corner].curvature}
          reverse={BEAM_CFG[o.corner].reverse}
          active={hovered === o.corner}
          pathWidth={1}
          duration={4.5 + i * 0.5}
          delay={i * 0.3}
          pathColor="hsl(var(--border))"
          pathOpacity={0.06}
          gradientStartColor="hsl(var(--aqua))"
          gradientStopColor="hsl(var(--lagoon))"
        />
      ))}
    </div>
  );
}

