import React, { useEffect, useRef, useState } from 'react';
import { cn } from '@/lib/utils';
import { useApp } from '@/lib/AppContext';

// Size the big number so strings of different length fill the same fraction
// of the card. cqi tracks the section container width.
function numberSizing(displayStr) {
  const len = displayStr.length;
  const cqw = Math.round(155 / len);
  let capRem;
  if (len <= 3) capRem = 5.5;
  else if (len <= 4) capRem = 5;
  else if (len <= 5) capRem = 4.3;
  else if (len <= 6) capRem = 3.7;
  else if (len <= 8) capRem = 3;
  else capRem = 2.4;
  return { cqw, capRem };
}

const easeOut = (t) => 1 - Math.pow(1 - t, 3);

const DOTS = [
  { cx: 14, cy: 14, d: '0.54s' }, { cx: 38, cy: 14, d: '0.36s' },
  { cx: 62, cy: 14, d: '0.18s' }, { cx: 86, cy: 14, d: '0s' },
  { cx: 38, cy: 38, d: '0.54s' }, { cx: 62, cy: 38, d: '0.36s' },
  { cx: 86, cy: 38, d: '0.18s' }, { cx: 62, cy: 62, d: '0.54s' },
  { cx: 86, cy: 62, d: '0.36s' }, { cx: 86, cy: 86, d: '0.54s' },
];

export default function StatCard({
  title = 'Valor do portfólio',
  value = 0,
  prefix = 'R$',
  decimals = 0,
  change = null,
  changeLabel = 'Variação',
  periodLabel = 'este mês',
  loading = false,
}) {
  const targetVal = Math.round(value || 0);
  const { addSavedInsight, savedInsights } = useApp();
  const sectionRef = useRef(null);
  const [revealed, setRevealed] = useState(false);
  const [display, setDisplay] = useState(0);

  const finalStr = `${prefix} ${targetVal.toLocaleString('pt-BR')}`;
  const sizing = numberSizing(finalStr.replace(/\s/g, ''));
  const numStyle = { fontSize: `clamp(1.9rem, ${sizing.cqw}cqi, ${sizing.capRem}rem)` };

  useEffect(() => {
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) {
      setDisplay(targetVal);
      setRevealed(true);
      return;
    }
    const el = sectionRef.current;
    if (!el || !targetVal) {
      setDisplay(targetVal);
      setRevealed(true);
      return;
    }
    let observed = false;
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting && !observed) {
          observed = true;
          observer.disconnect();
          setRevealed(true);
          const duration = 1400;
          let startTime = null;
          const tick = (ts) => {
            if (!startTime) startTime = ts;
            const progress = Math.min((ts - startTime) / duration, 1);
            setDisplay(Math.round(easeOut(progress) * targetVal));
            if (progress < 1) requestAnimationFrame(tick);
            else setDisplay(targetVal);
          };
          requestAnimationFrame(tick);
        }
      });
    }, { threshold: 0.25 });
    observer.observe(el);
    return () => observer.disconnect();
  }, [targetVal]);

  const numberText = loading ? '···' : `${prefix} ${display.toLocaleString('pt-BR')}`;
  const hasChange = Number.isFinite(change);
  const changeUp = hasChange ? change >= 0 : true;
  const insightId = `stat-${title.toLowerCase().replace(/[^a-z0-9]+/gi, '-')}`;
  const added = savedInsights.some((item) => item.id === insightId);

  return (
    <section
      ref={sectionRef}
      className={cn('sc1-section flex justify-center', revealed && 'sc1-revealed')}
        >
        <button
          type="button"
          onClick={() => addSavedInsight({ id: insightId, type: 'KPI', label: title, data: { value: numberText, change, period: periodLabel } })}
          className={cn('absolute bottom-5 right-5 z-10 grid h-7 w-7 place-items-center rounded-full border text-sm font-light shadow-[0_4px_12px_hsl(220_12%_18%/0.10)] backdrop-blur-sm transition-all hover:-translate-y-0.5', added ? 'border-brand/35 bg-brand/15 text-brand' : 'border-white/80 bg-card/65 text-text-muted hover:border-brand/45 hover:bg-brand/10 hover:text-brand')}
          aria-label={added ? 'Indicador adicionado' : 'Adicionar ao painel de contexto'}
        >
          {added ? '✓' : '+'}
        </button>
      <div
        className="relative flex flex-col justify-between gap-[clamp(28px,8cqi,48px)] overflow-hidden rounded-[2rem] border border-white/80 p-[clamp(24px,6cqi,36px)] w-full max-w-[480px] min-h-[clamp(210px,55cqi,300px)] shadow-[0_18px_45px_hsl(220_12%_18%/0.12),inset_0_1px_0_hsl(0_0%_100%/0.92)] backdrop-blur-2xl"
        style={{
          backgroundColor: 'hsl(var(--card) / 0.52)',
          backgroundImage:
            'radial-gradient(125% 125% at 100% 0%, hsl(0 0% 100% / 0.52) 0%, hsl(220 12% 82% / 0.15) 30%, transparent 62%)',
        }}
      >
        {/* grain noise overlay */}
        <svg className="sc1-grain" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">
          <filter id="sc1-grain-filter">
            <feTurbulence type="fractalNoise" baseFrequency="1.1" numOctaves="3" stitchTiles="stitch" />
            <feColorMatrix type="saturate" values="0" />
            <feComponentTransfer>
              <feFuncR type="linear" slope="1.25" intercept="-0.12" />
              <feFuncG type="linear" slope="1.25" intercept="-0.12" />
              <feFuncB type="linear" slope="1.25" intercept="-0.12" />
            </feComponentTransfer>
          </filter>
          <rect width="100%" height="100%" filter="url(#sc1-grain-filter)" />
        </svg>

        {/* top: title + descending dot-grid accent */}
        <div className="relative flex items-start justify-between gap-4">
          <h3
            className="m-0 font-heading font-medium leading-[1.2] tracking-[-0.02em] text-foreground min-w-0"
            style={{ fontSize: 'clamp(1.3rem, 7cqi, 1.9rem)' }}
          >
            {title}
          </h3>
          <svg
            className="shrink-0 [width:clamp(2.5rem,16cqi,4.75rem)] [height:clamp(2.5rem,16cqi,4.75rem)]"
            aria-hidden="true"
            viewBox="0 0 100 100"
            xmlns="http://www.w3.org/2000/svg"
          >
            {DOTS.map((dt, i) => (
              <circle
                key={i}
                className="sc1-dot"
                style={{ '--sc1-d': dt.d }}
                cx={dt.cx}
                cy={dt.cy}
                r={9}
                fill="hsl(var(--foreground) / 0.32)"
              />
            ))}
          </svg>
        </div>

        {/* bottom: big number + detail pairs */}
        <div className="relative flex flex-wrap items-end justify-between gap-[clamp(16px,4cqi,28px)]">
          <div
            className="flex items-start leading-none tracking-[-0.05em] tnum font-heading font-bold text-foreground"
            style={numStyle}
          >
            <span>{numberText}</span>
          </div>

          <dl className="flex flex-wrap gap-x-[clamp(20px,6cqi,32px)] gap-y-3 m-0 p-0 list-none">
            <div className="min-w-0">
              <dt className="block m-0 mb-0.5 text-text-muted" style={{ fontSize: 'clamp(0.85rem,4.2cqi,1rem)' }}>
                {changeLabel}
              </dt>
              <dd
                className={cn('m-0 font-medium', changeUp ? 'text-positive' : 'text-negative')}
                style={{ fontSize: 'clamp(0.95rem,4.6cqi,1.15rem)' }}
              >
                {hasChange ? `${changeUp ? '▲' : '▼'} ${Math.abs(change).toFixed(1)}%` : '—'}
              </dd>
            </div>
            <div className="min-w-0">
              <dt className="block m-0 mb-0.5 text-text-muted" style={{ fontSize: 'clamp(0.85rem,4.2cqi,1rem)' }}>
                Período
              </dt>
              <dd className="m-0 font-medium text-foreground" style={{ fontSize: 'clamp(0.95rem,4.6cqi,1.15rem)' }}>
                {periodLabel}
              </dd>
            </div>
          </dl>
        </div>
      </div>
    </section>
  );
}
