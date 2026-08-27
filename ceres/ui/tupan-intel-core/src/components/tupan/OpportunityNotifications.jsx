import React, { useEffect, useMemo, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { useQuery } from '@tanstack/react-query';
import { Bell, ExternalLink, Sparkles, TrendingDown } from 'lucide-react';
import { getPortfolioAnalytics } from '@/api/portfolio';
import { sendAgentMessage } from '@/api/agent';
import { apiErrorMessage } from '@/api/client';
import { formatBRL } from '@/lib/format';
import { useApp } from '@/lib/AppContext';

export default function OpportunityNotifications() {
  const { sendToAgent } = useApp();
  const [open, setOpen] = useState(false);
  const containerRef = useRef(null);
  const portfolioQuery = useQuery({
    queryKey: ['header-hot-opportunities'],
    queryFn: ({ signal }) => getPortfolioAnalytics({ signal }),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  const opportunities = useMemo(() => {
    const candidates = Array.isArray(portfolioQuery.data?.below_estimate) ? portfolioQuery.data.below_estimate : [];
    return candidates
      .filter((property) => typeof property.price_gap === 'number' && property.price_gap < 0)
      .sort((a, b) => a.price_gap - b.price_gap)
      .slice(0, 3);
  }, [portfolioQuery.data?.below_estimate]);
  const opportunityKey = opportunities.map((property) => property.property_id).join('|');

  const aiQuery = useQuery({
    queryKey: ['header-hot-opportunities-ai', opportunityKey],
    queryFn: ({ signal }) => sendAgentMessage({
      message: 'Atue como o monitor de oportunidades da Ceres. Com base somente nos imóveis anexados, identifique a oportunidade prioritária e explique em até dois parágrafos curtos por que ela merece atenção agora. Não cite métricas, modelos, fórmulas, percentuais ou níveis de confiança; expresse apenas a prioridade comercial e a próxima ação recomendada.',
      contextItems: opportunities.map((property) => ({
        id: `notification-opportunity-${property.property_id}`,
        type: 'Property',
        label: property.title,
        data: property,
      })),
      signal,
    }),
    enabled: open && opportunities.length > 0,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  useEffect(() => {
    const closeOnOutsidePointer = (event) => {
      if (containerRef.current && !containerRef.current.contains(event.target)) setOpen(false);
    };
    document.addEventListener('pointerdown', closeOnOutsidePointer);
    return () => document.removeEventListener('pointerdown', closeOnOutsidePointer);
  }, []);

  const openOpportunity = (property) => {
    sendToAgent(
      [{ id: `notification-opportunity-${property.property_id}`, type: 'Property', label: property.title, data: property }],
      `Explique por que ${property.title} aparece como uma oportunidade identificada pela Ceres e qual deve ser a próxima ação comercial. Use apenas as evidências anexadas.`,
    );
  };

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-label="Abrir oportunidades da Ceres"
        aria-expanded={open}
        className={`relative flex h-8 w-8 items-center justify-center rounded-full border border-border/80 bg-card/38 text-text-secondary shadow-[0_2px_8px_hsl(var(--foreground)/0.08),inset_0_1px_0_hsl(0_0%_100%/0.16)] backdrop-blur-2xl transition-colors hover:text-foreground ${open ? 'border-positive/40 bg-positive/10 text-positive' : ''}`}
      >
        <Bell className="h-4 w-4" />
        {!portfolioQuery.isLoading && opportunities.length > 0 && <span className="absolute -right-0.5 -top-0.5 grid h-3.5 min-w-3.5 place-items-center rounded-full border border-card bg-positive px-0.5 text-[8px] font-bold leading-none text-white">{opportunities.length}</span>}
      </button>

      {open && (
        <aside className="absolute right-0 top-10 z-50 w-[360px] max-w-[calc(100vw-2rem)] overflow-hidden rounded-[22px] border border-border/85 bg-[linear-gradient(145deg,hsl(var(--card)/.96),hsl(var(--elevated)/.82))] shadow-[0_24px_60px_hsl(var(--foreground)/.24),inset_0_1px_0_hsl(0_0%_100%/.16)] backdrop-blur-2xl">
          <div className="border-b border-border/65 px-4 py-3.5">
            <div className="flex items-start gap-2.5">
              <span className="grid h-8 w-8 shrink-0 place-items-center rounded-xl border border-positive/25 bg-positive/10 text-positive"><Sparkles className="h-3.5 w-3.5" /></span>
              <div className="min-w-0 flex-1">
                <p className="text-[10px] font-bold uppercase tracking-[0.15em] text-positive">Ceres Monitor</p>
                <h2 className="mt-0.5 text-sm font-semibold text-foreground">Oportunidades quentes</h2>
                <p className="mt-0.5 text-[10px] text-text-muted">Oportunidades priorizadas pela IA</p>
              </div>
              <span className="rounded-full border border-positive/20 bg-positive/10 px-2 py-0.5 text-[10px] font-semibold text-positive">{opportunities.length}</span>
            </div>
          </div>

          <div className="max-h-[min(520px,calc(100vh-7rem))] space-y-3 overflow-y-auto p-3">
            {portfolioQuery.isLoading && <div className="flex h-28 items-center justify-center text-xs text-text-muted"><span className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-border border-t-brand" />Procurando oportunidades…</div>}
            {portfolioQuery.isError && <div role="alert" className="rounded-xl border border-negative/30 bg-negative/10 p-3 text-xs text-negative">{apiErrorMessage(portfolioQuery.error)}</div>}
            {!portfolioQuery.isLoading && !portfolioQuery.isError && opportunities.length === 0 && <div className="rounded-xl border border-dashed border-border/75 bg-card/35 px-5 py-8 text-center text-xs leading-relaxed text-text-muted">Nenhuma oportunidade foi priorizada pela Ceres neste momento.</div>}

            {opportunities.map((property, index) => {

              return (
                <article key={property.property_id} className="rounded-2xl border border-border/75 bg-card/52 p-3 shadow-[inset_0_1px_0_hsl(0_0%_100%/.14)]">
                  <div className="flex items-start gap-2.5">
                    <span className="grid h-6 w-6 shrink-0 place-items-center rounded-lg bg-positive/10 text-[10px] font-bold text-positive">{index + 1}</span>
                    <div className="min-w-0 flex-1">
                      <h3 className="truncate text-xs font-semibold text-foreground">{property.title}</h3>
                      <p className="mt-0.5 truncate text-[10px] text-text-muted">{property.region || 'Região não informada'} · {formatBRL(property.asking_price)}</p>
                    </div>
                    <TrendingDown className="mt-0.5 h-4 w-4 shrink-0 text-positive" />
                  </div>
                  <div className="mt-2 flex items-center justify-between gap-3 border-t border-border/55 pt-2">
                    <span className="text-[10px] text-text-muted">Sinal de oportunidade identificado pela Ceres</span>
                    <button type="button" onClick={() => openOpportunity(property)} className="inline-flex items-center gap-1 text-[10px] font-semibold text-brand hover:text-brand/80"><ExternalLink className="h-3 w-3" />Analisar</button>
                  </div>
                </article>
              );
            })}

            {opportunities.length > 0 && <div className="rounded-2xl border border-positive/20 bg-positive/5 p-3">
              <div className="mb-1.5 flex items-center gap-1.5"><Sparkles className="h-3.5 w-3.5 text-positive" /><span className="text-[10px] font-bold uppercase tracking-[0.12em] text-positive">Prioridade da Ceres</span></div>
              {aiQuery.isLoading && <p className="text-xs text-text-muted">A Ceres está priorizando estas oportunidades…</p>}
              {aiQuery.isError && <p role="alert" className="text-xs text-negative">{apiErrorMessage(aiQuery.error)}</p>}
              {aiQuery.isSuccess && <div className="prose prose-sm max-w-none text-xs leading-relaxed text-text-secondary [&_p]:my-1 [&_strong]:text-foreground"><ReactMarkdown>{aiQuery.data?.message?.content || 'A Ceres não retornou uma priorização para estas oportunidades.'}</ReactMarkdown></div>}
            </div>}
          </div>
        </aside>
      )}
    </div>
  );
}



