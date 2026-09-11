import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, PieChart, Pie, Cell } from 'recharts';
import TopBar from '@/components/tupan/TopBar';
import { Panel, SectionTitle, KpiCard, ContextTag } from '@/components/tupan/primitives';
import { enableChartExpansion } from '@/lib/featureFlags';
import { formatBRL, formatBRLCompact, formatM2, formatPct } from '@/lib/format';
import { propertyTypeLabel } from '@/lib/labels';
import { useApp } from '@/lib/AppContext';
import StatCard from '@/components/tupan/StatCard';
import { Sparkles, AlertTriangle, ChevronDown } from 'lucide-react';
import { apiErrorMessage } from '@/api/client';
import { CHART, tooltipStyle } from '@/lib/chartTheme';
import { getPortfolioAnalytics } from '@/api/portfolio';

const typeColors = [CHART.aqua, CHART.positive, CHART.warning, CHART.negative, CHART.lagoon];
const percent = (ratio) => ratio == null ? null : ratio * 100;

export default function Portfolio() {
  const { sendToAgent } = useApp();
  const portfolioQuery = useQuery({
    queryKey: ['portfolio-analytics'],
    queryFn: ({ signal }) => getPortfolioAnalytics({ signal }),
    retry: false,
  });
  const analytics = portfolioQuery.data ? {
    ...portfolioQuery.data,
    regional_concentration: Array.isArray(portfolioQuery.data.regional_concentration) ? portfolioQuery.data.regional_concentration : [],
    property_type_mix: Array.isArray(portfolioQuery.data.property_type_mix) ? portfolioQuery.data.property_type_mix : [],
    regional_performance: Array.isArray(portfolioQuery.data.regional_performance) ? portfolioQuery.data.regional_performance : [],
    above_estimate: Array.isArray(portfolioQuery.data.above_estimate) ? portfolioQuery.data.above_estimate : [],
    below_estimate: Array.isArray(portfolioQuery.data.below_estimate) ? portfolioQuery.data.below_estimate : [],
  } : null;

  if (portfolioQuery.isLoading) {
    return <div className="flex-1 flex items-center justify-center"><div className="w-8 h-8 border-4 border-border border-t-brand rounded-full animate-spin" /></div>;
  }

  if (portfolioQuery.isError || !analytics) {
    return (
      <>
        <TopBar title="Inteligência de Portfólio" subtitle="Análises de corretagem · Risco e Oportunidade" />
        <div className="workspace-content flex-1 overflow-y-auto">
          <div role="alert" className="rounded-lg border border-negative/30 bg-negative/10 p-4 text-sm text-negative">{apiErrorMessage(portfolioQuery.error)}</div>
        </div>
      </>
    );
  }

  const concentration = analytics.regional_concentration || [];
  const topConcentration = concentration.slice(0, 2).reduce((total, item) => total + item.share, 0);
  const typeData = (analytics.property_type_mix || []).map((item) => ({ name: propertyTypeLabel(item.kind), value: item.property_count }));
  const concData = concentration.slice(0, 8).map((item) => ({ name: item.region, value: Math.round(item.share * 100) }));
  const bestGrowthRegion = (analytics.regional_performance || []).find((item) => item.average_expected_growth != null);
  const kpiMetricOptions = [
    { id: 'portfolio-value', label: 'Valor total do portfólio', value: formatBRLCompact(analytics.portfolio_value), tag: 'DATA', series: [], seriesValueFormatter: formatBRLCompact },
    { id: 'active-properties', label: 'Imóveis ativos', value: analytics.active_listing_count, tag: 'DATA', sub: `${analytics.sold_listing_count} vendidos informados`, series: [] },
    { id: 'average-price', label: 'Preço médio do anúncio', value: formatBRLCompact(analytics.average_asking_price), tag: 'DATA', series: [], seriesValueFormatter: formatBRLCompact },
    { id: 'median-price', label: 'Mediana do preço do anúncio', value: formatBRLCompact(analytics.median_asking_price), tag: 'DATA', series: [], seriesValueFormatter: formatBRLCompact },
    { id: 'average-m2', label: 'Preço/m² médio', value: formatM2(analytics.average_price_per_m2), tag: 'DATA', series: [], seriesValueFormatter: formatM2 },
    { id: 'average-dom', label: 'DOM médio', value: analytics.average_dom_days == null ? '—' : `${Math.round(analytics.average_dom_days)}d`, tag: 'DATA', series: [], seriesValueFormatter: (value) => `${Math.round(value)}d` },
    { id: 'listing-age', label: 'Idade do anúncio', value: analytics.average_listing_age_days == null ? '—' : `${Math.round(analytics.average_listing_age_days)}d`, tag: 'DATA', series: [], seriesValueFormatter: (value) => `${Math.round(value)}d` },
    { id: 'overpriced', label: 'Acima da estimativa', value: analytics.above_estimate.length, tag: 'MODEL', sub: 'Estimativa persistida', series: [] },
    { id: 'underpriced', label: 'Abaixo da estimativa', value: analytics.below_estimate.length, tag: 'MODEL', sub: 'Estimativa persistida', series: [] },
    { id: 'avm-deviation', label: 'Gap médio da estimativa', value: formatPct(percent(analytics.average_price_gap)), tag: 'MODEL', series: [], seriesValueFormatter: (value) => formatPct(percent(value)) },
    { id: 'liquidity', label: 'Liquidez prevista', value: '—', tag: 'MODEL', sub: 'Não disponível', series: [] },
    { id: 'confidence', label: 'Confiança do modelo', value: '—', tag: 'MODEL', sub: 'Não disponível', series: [] },
  ];
  const evidence = [
    topConcentration > 0 && concentration.length > 0
      ? `${formatPct(percent(topConcentration), false)} do valor do portfólio está concentrado em ${concentration.slice(0, 2).map((item) => item.region).join(' e ')}.`
      : null,
    analytics.above_estimate.length > 0
      ? `${analytics.above_estimate.length} anúncio(s) estão acima da estimativa de preço persistida.`
      : null,
    bestGrowthRegion
      ? `${bestGrowthRegion.region} tem o maior crescimento esperado disponível: ${formatPct(percent(bestGrowthRegion.average_expected_growth))}.`
      : null,
  ].filter(Boolean);
  const insightText = evidence.length ? evidence.join(' ') : 'Não há evidência suficiente no portfólio persistido para gerar um resumo determinístico.';

  return (
    <>
      <TopBar title="Inteligência de Portfólio" subtitle="Análises de corretagem · Risco e Oportunidade" />
      <div className="workspace-content workspace-stack flex-1 overflow-y-auto">
        <section className="portfolio-summary" aria-label="Resumo do portfólio">
          <div><StatCard
          title="Valor do portfólio"
          value={analytics.portfolio_value}
          prefix="R$"
          change={null}
          changeLabel="Variação histórica"
          periodLabel="Dados atuais"
        /></div>
          <div className="grid grid-cols-1 gap-x-6 sm:grid-cols-2">
            {[kpiMetricOptions.slice(1, 6), kpiMetricOptions.slice(6)].map((group, index) => (
              <dl key={index} className="data-ledger">
                {group.map((option) => <div key={option.id}>
                  <dt>{option.label}</dt>
                  <dd>{option.value}{option.sub && <small>{option.sub}</small>}</dd>
                </div>)}
              </dl>
            ))}
          </div>
        </section>

        <div className="analysis-split">
          <Panel className="p-4" contextItem={{ id: 'portfolio-geographic-concentration', type: 'Chart', label: 'Concentração geográfica', data: { concentration } }}>
            <SectionTitle right={<ContextTag type="DATA">Exposição</ContextTag>}>Concentração geográfica</SectionTitle>
            {concData.length === 0 ? <div className="h-[220px] flex items-center justify-center text-xs text-text-muted">Sem regiões com valor de anúncio disponível.</div> : <ResponsiveContainer width="100%" height={220}>
              <BarChart data={concData} layout="vertical" margin={{ left: 24, right: 12, top: 0, bottom: 0 }}>
                <CartesianGrid stroke={CHART.grid} strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" stroke={CHART.axis} fontSize={10} tickLine={false} axisLine={false} unit="%" />
                <YAxis type="category" dataKey="name" stroke={CHART.axis} fontSize={11} tickLine={false} axisLine={false} width={100} />
                <Tooltip contentStyle={tooltipStyle} cursor={{ fill: CHART.aqua, fillOpacity: 0.12 }} formatter={(value) => `${value}%`} />
                <Bar dataKey="value" fill={CHART.aqua} radius={[0, 8, 8, 0]} barSize={12} />
              </BarChart>
            </ResponsiveContainer>}
          </Panel>
          <Panel className="p-4" contextItem={{ id: 'portfolio-property-type-mix', type: 'Chart', label: 'Concentração por tipo de imóvel', data: { distribution: analytics.property_type_mix } }}>
            <SectionTitle right={<ContextTag type="DATA">Mix</ContextTag>}>Concentração por tipo de imóvel</SectionTitle>
            {typeData.length === 0 ? <div className="h-[200px] flex items-center justify-center text-xs text-text-muted">Sem tipos de imóvel disponíveis.</div> : <div className="flex items-center gap-4">
              <ResponsiveContainer width={170} height={200}>
                <PieChart>
                  <Pie data={typeData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={44} outerRadius={70} paddingAngle={2}>
                    {typeData.map((_, index) => <Cell key={index} fill={typeColors[index % typeColors.length]} />)}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex-1 space-y-2">
                {typeData.map((item, index) => (
                  <div key={item.name} className="flex items-center justify-between text-xs">
                    <span className="flex items-center gap-2 text-text-secondary"><span className="w-2 h-2 rounded-full" style={{ background: typeColors[index % typeColors.length] }} />{item.name}</span>
                    <span className="tnum text-foreground">{item.value}</span>
                  </div>
                ))}
              </div>
            </div>}
          </Panel>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Panel className="p-4" contextItem={{ id: 'portfolio-above-estimate', type: 'Chart', label: 'Imóveis acima da estimativa', data: { properties: analytics.above_estimate } }}>
            <SectionTitle right={<ContextTag type="MODEL">Risco</ContextTag>}>Imóveis sobreavaliados</SectionTitle>
            <div className="space-y-1">
              {analytics.above_estimate.map((property) => (
                <div key={property.property_id} className="flex items-center justify-between py-2 border-b border-border/60 last:border-0">
                  <div className="min-w-0">
                    <div className="text-xs font-medium text-foreground truncate">{property.title}</div>
                    <div className="text-[10px] text-text-muted">{property.region || 'Região não informada'} · {formatBRL(property.asking_price)}</div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-[10px] px-1.5 py-0.5 rounded border bg-negative/10 text-negative border-negative/20">{formatPct(percent(property.price_gap))}</span>
                    <button onClick={() => sendToAgent([{ id: `portfolio-property-${property.property_id}`, type: 'Property', label: property.title, data: property }], `Explique a diferença entre o preço de anúncio e a estimativa de ${property.title}.`)} aria-label="Explicar diferença de preço" className="icon-control text-brand"><Sparkles className="w-3.5 h-3.5" /></button>
                  </div>
                </div>
              ))}
              {analytics.above_estimate.length === 0 && <div className="text-xs text-text-muted py-4 text-center">Nenhum imóvel com preço acima da estimativa persistida</div>}
            </div>
          </Panel>
          <Panel className="p-4" contextItem={{ id: 'portfolio-below-estimate', type: 'Chart', label: 'Imóveis abaixo da estimativa', data: { properties: analytics.below_estimate } }}>
            <SectionTitle right={<ContextTag type="MODEL">Oportunidade</ContextTag>}>Imóveis subavaliados</SectionTitle>
            <div className="space-y-1">
              {analytics.below_estimate.map((property) => (
                <div key={property.property_id} className="flex items-center justify-between py-2 border-b border-border/60 last:border-0">
                  <div className="min-w-0">
                    <div className="text-xs font-medium text-foreground truncate">{property.title}</div>
                    <div className="text-[10px] text-text-muted">{property.region || 'Região não informada'} · {formatBRL(property.asking_price)}</div>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-[10px] px-1.5 py-0.5 rounded border bg-positive/10 text-positive border-positive/20">{formatPct(percent(property.price_gap))}</span>
                    <button onClick={() => sendToAgent([{ id: `portfolio-property-${property.property_id}`, type: 'Property', label: property.title, data: property }], `Explique a diferença entre o preço de anúncio e a estimativa de ${property.title}.`)} aria-label="Explicar diferença de preço" className="icon-control text-brand"><Sparkles className="w-3.5 h-3.5" /></button>
                  </div>
                </div>
              ))}
              {analytics.below_estimate.length === 0 && <div className="text-xs text-text-muted py-4 text-center">Nenhum imóvel com preço abaixo da estimativa persistida</div>}
            </div>
          </Panel>
        </div>

        <Panel className="p-4" contextItem={{ id: 'portfolio-risk-summary', type: 'KPI', label: 'Resumo de risco do portfólio', data: { analytics } }}>
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-warning shrink-0 mt-0.5" />
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <h3 className="text-sm font-semibold text-foreground">Insight do portfólio</h3>
                <ContextTag type="DATA">Evidência</ContextTag>
              </div>
              <p className="text-xs text-text-secondary leading-relaxed">{insightText}</p>
            </div>
            <button onClick={() => sendToAgent([{ id: 'portfolio', type: 'Portfolio', label: 'Portfólio completo', data: { analytics } }], 'Interprete as evidências numéricas, os riscos, a concentração e as oportunidades do meu portfólio. Não recalcule os indicadores.') } className="shrink-0 h-8 px-3 rounded bg-brand text-brand-foreground text-xs font-medium hover:bg-brand/90 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5" /> Explicar
            </button>
          </div>
        </Panel>
        <details className="analysis-disclosure">
          <summary>Séries e indicadores <span className="text-xs font-normal text-text-secondary">12 indicadores <ChevronDown className="h-4 w-4" /></span></summary>
          <div className="portfolio-indicators pt-5">
            {kpiMetricOptions.map((option) => <KpiCard key={option.id} {...option} series={enableChartExpansion ? option.series : []} metricOptions={kpiMetricOptions} />)}
          </div>
        </details>
      </div>
    </>
  );
}
