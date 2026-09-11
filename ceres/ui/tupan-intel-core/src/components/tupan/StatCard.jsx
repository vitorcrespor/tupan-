import React, { useEffect, useRef, useState } from 'react';
import { cn } from '@/lib/utils';
import { useApp } from '@/lib/AppContext';

const easeOut = (t) => 1 - Math.pow(1 - t, 3);

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
  const [display, setDisplay] = useState(0);

  useEffect(() => {
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (prefersReduced) {
      setDisplay(targetVal);
      return;
    }
    const el = sectionRef.current;
    if (!el || !targetVal) {
      setDisplay(targetVal);
      return;
    }
    let observed = false;
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting && !observed) {
          observed = true;
          observer.disconnect();
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
      className="sc1-section relative"
        >
        <button
          type="button"
          onClick={() => addSavedInsight({ id: insightId, type: 'KPI', label: title, data: { value: numberText, change, period: periodLabel } })}
          className={cn('icon-control absolute bottom-5 right-5 z-10 text-sm font-light transition-colors', added ? 'border-brand/35 bg-brand/15 text-brand' : 'text-text-muted hover:text-brand')}
          aria-label={added ? 'Indicador adicionado' : 'Adicionar ao painel de contexto'}
        >
          {added ? '✓' : '+'}
        </button>
      <div
        className="relative flex w-full flex-col gap-6 py-2 pr-14"
      >
        <div className="relative flex items-start justify-between gap-4">
          <h3
            className="m-0 text-sm font-medium text-text-secondary"
          >
            {title}
          </h3>
        </div>

        {/* bottom: big number + detail pairs */}
        <div className="relative flex flex-wrap items-end justify-between gap-6">
          <div
            className="flex items-start text-4xl leading-tight tracking-tight tnum font-heading font-semibold text-foreground"
          >
            <span>{numberText}</span>
          </div>

          <dl className="flex flex-wrap gap-x-6 gap-y-3 m-0 p-0 list-none">
            <div className="min-w-0">
              <dt className="block m-0 mb-0.5 text-xs text-text-secondary">
                {changeLabel}
              </dt>
              <dd
                className={cn('m-0 font-medium', hasChange ? (changeUp ? 'text-positive' : 'text-negative') : 'text-text-muted')}
              >
                {hasChange ? `${changeUp ? '▲' : '▼'} ${Math.abs(change).toFixed(1)}%` : '—'}
              </dd>
            </div>
            <div className="min-w-0">
              <dt className="block m-0 mb-0.5 text-xs text-text-secondary">
                Período
              </dt>
              <dd className="m-0 font-medium text-foreground">
                {periodLabel}
              </dd>
            </div>
          </dl>
        </div>
      </div>
    </section>
  );
}
