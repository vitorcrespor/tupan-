import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, PieChart, Pie, Cell } from 'recharts';
import TopBar from '@/components/tupan/TopBar';
import EstimateProvenance from '@/components/tupan/EstimateProvenance';
import { Panel, SectionTitle, KpiCard, ContextTag } from '@/components/tupan/primitives';
import { enableChartExpansion } from '@/lib/featureFlags';
import { formatBRL, formatBRLCompact, formatM2, formatPct } from '@/lib/format';
import { propertyTypeLabel } from '@/lib/labels';
import { useApp } from '@/lib/AppContext';
import StatCard from '@/components/tupan/StatCard';
import { Sparkles, AlertTriangle, ChevronDown } from 'lucide-react';
import { apiErrorMessage } from '@/api/client';
import { CHART, tooltipStyle } from '@/lib/chartTheme';
import { getPortfolios } from '@/api/portfolio';
import { usePortfolioAnalytics } from '@/lib/usePortfolioAnalytics';
import { timePeriodLabel } from '@/lib/tupanData';

const typeColors = [CHART.aqua, CHART.positive, CHART.warning, CHART.negative, CHART.lagoon];
const percent = (ratio) => ratio == null ? null : ratio * 100;

function portfolioLiquidityLabel(analytics) {
  if (analytics.liquidity_status === 'available') {
    return `${analytics.liquidity_eligible_estate_count} anúncio(s) elegível(is) · vendas do próprio portfólio`;
  }
  if (analytics.liquidity_status === 'horizon_not_selected') return 'Selecione um horizonte no cabeçalho';
  if (analytics.liquidity_status === 'no_active_listings') return 'Não há anúncios ativos neste portfólio';
  if (analytics.liquidity_status === 'missing_listing_duration') return 'Faltam durações de anúncios no portfólio';
  return 'Histórico próprio de anúncios e vendas insuficiente';
}

export default function Portfolio() {
  const { sendToAgent, selectedPortfolioId, setSelectedPortfolioId, timePeriod } = useApp();
  const portfoliosQuery = useQuery({queryKey: ['portfolios'], queryFn: ({signal}) => getPortfolios({signal})});
  const portfolioQuery = usePortfolioAnalytics();
  const analytics = portfolioQuery.data ? {
    ...portfolioQuery.data,
    regional_concentration: Array.isArray(portfolioQuery.data.regional_concentration) ? portfolioQuery.data.regional_concentration : [],
    property_type_mix: Array.isArray(portfolioQuery.data.property_type_mix) ? portfolioQuery.data.property_type_mix : [],
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
          <div role={String(portfolioQuery.error?.message || '').includes('Nenhum portfólio') ? 'status' : 'alert'} className="p-4 text-sm text-text-secondary">{apiErrorMessage(portfolioQuery.error)}</div>
        </div>
      </>
    );
  }

  const concentration = analytics.regional_concentration || [];
  const topConcentration = analytics.top_region_share;
  const typeData = (analytics.property_type_mix || []).map((item) => ({ name: propertyTypeLabel(item.kind), value: item.property_count }));
  const concData = concentration.slice(0, 8).map((item) => ({ name: item.region, value: Math.round(item.share * 100) }));
  const historySeries = (field) => (analytics.history || [])
    .filter((point) => Number.isFinite(point?.[field]))
    .map((point) => ({ label: point.observed_on, value: point[field] }));
  const observationSeriesLabel = 'últimas observações';
  const kpiMetricOptions = [
    { id: 'portfolio-value', label: 'Valor total do portfólio', value: formatBRLCompact(analytics.portfolio_value), tag: 'DATA', series: historySeries('portfolio_value'), seriesLabel: observationSeriesLabel, seriesValueFormatter: formatBRLCompact },
    { id: 'estimated-value', label: 'Valor estimado registrado', value: formatBRLCompact(analytics.estimated_value), tag: 'MODEL', sub: analytics.estimated_value == null ? 'Cobertura de estimativas incompleta' : `${analytics.estimated_count ?? 0} estimativas registradas`, series: [], seriesValueFormatter: formatBRLCompact },
    { id: 'active-properties', label: 'Imóveis ativos', value: analytics.active_listing_count ?? '—', tag: 'DATA', sub: 'Imóveis ativos do portfólio selecionado', series: historySeries('active_estate_count'), seriesLabel: observationSeriesLabel },
    { id: 'average-price', label: 'Preço médio do anúncio', value: formatBRLCompact(analytics.average_asking_price), tag: 'DATA', series: [], seriesValueFormatter: formatBRLCompact },
    { id: 'median-price', label: 'Mediana do preço do anúncio', value: formatBRLCompact(analytics.median_asking_price), tag: 'DATA', series: [], seriesValueFormatter: formatBRLCompact },
    { id: 'average-m2', label: 'Preço/m² médio', value: formatM2(analytics.average_price_per_m2), tag: 'DATA', series: [], seriesValueFormatter: formatM2 },
    { id: 'median-m2', label: 'Preço/m² mediano', value: formatM2(analytics.median_price_per_m2), tag: 'DATA', series: [], seriesValueFormatter: formatM2 },
    { id: 'average-dom', label: 'DOM médio', value: analytics.average_dom_days == null ? '—' : `${Math.round(analytics.average_dom_days)}d`, tag: 'DATA', series: historySeries('average_days_on_market'), seriesLabel: observationSeriesLabel, seriesValueFormatter: (value) => `${Math.round(value)}d` },
    {
      id: 'listing-age', label: 'Idade média do anúncio',
      value: analytics.average_listing_age_days == null ? '—' : `${Math.round(analytics.average_listing_age_days)}d`,
      tag: 'DATA',
      sub: analytics.listing_age_count > 0
        ? `${analytics.listing_age_count} anúncio(s) com data de publicação`
        : 'Sem datas de publicação suficientes',
      series: historySeries('average_listing_age_days'), seriesLabel: observationSeriesLabel, seriesValueFormatter: (value) => `${Math.round(value)}d`,
    },
    { id: 'overpriced', label: 'Acima da estimativa', value: analytics.above_count ?? '—', tag: 'MODEL', sub: 'Estimativa persistida', series: [] },
    { id: 'underpriced', label: 'Abaixo da estimativa', value: analytics.below_count ?? '—', tag: 'MODEL', sub: 'Estimativa persistida', series: [] },
    { id: 'avm-deviation', label: 'Gap médio da estimativa', value: formatPct(percent(analytics.average_price_gap)), tag: 'MODEL', series: historySeries('average_price_gap'), seriesLabel: observationSeriesLabel, seriesValueFormatter: (value) => formatPct(percent(value)) },
    {
      id: 'liquidity',
      label: `Liquidez prevista · ${timePeriodLabel(timePeriod)}`,
      value: analytics.liquidity_score == null ? '—' : `${Math.round(analytics.liquidity_score)}/100`,
      tag: 'DATA',
      sub: portfolioLiquidityLabel(analytics),
      series: [],
    },
  ];
  const evidence = [
    topConcentration > 0 && concentration.length > 0
      ? `${formatPct(percent(topConcentration), false)} do valor do portfólio está concentrado em ${concentration.slice(0, 2).map((item) => item.region).join(' e ')}.`
      : null,
    analytics.above_count > 0
      ? `${analytics.above_count} anúncio(s) estão acima da estimativa de preço persistida.`
      : null,
  ].filter(Boolean);
  const insightText = evidence.length ? evidence.join(' ') : 'Não há evidência suficiente no portfólio persistido para gerar um resumo determinístico.';

  return (
    <>
      <TopBar title="Inteligência de Portfólio" subtitle={analytics.portfolio.name} right={
        <select aria-label="Portfólio" className="h-9 rounded border border-border bg-elevated px-3 text-xs" value={selectedPortfolioId || analytics.portfolio.id} onChange={event => setSelectedPortfolioId(event.target.value)}>
          {(portfoliosQuery.data || [analytics.portfolio]).map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
        </select>
      } />
      <div className="workspace-content workspace-stack flex-1 overflow-y-auto">
        {analytics.portfolio.description && <p className="text-xs text-text-secondary">{analytics.portfolio.description}</p>}
        <p className="text-xs text-text-secondary">Estimativas com origem registrada: {analytics.estimate_lineage_count ?? '—'} de {analytics.estimated_count ?? '—'}. Com dados alterados desde o registro: {analytics.estimate_inputs_changed_count ?? '—'}. Estimativas registradas podem ter datas e origens diferentes.</p>
        {analytics.warnings.map(item => <p key={item.name} role="status" className="text-xs text-warning">{item.message || 'Parte da análise está indisponível.'}</p>)}
        <section className="portfolio-summary" aria-label="Resumo do portfólio">
          <div><StatCard
          title="Valor anunciado do portfólio"
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
          <Panel className="p-4" contextItem={{ id: 'portfolio-geographic-concentration', type: 'Chart', label: 'Concentração geográfica', data: { portfolio_id: analytics.portfolio.id } }}>
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
          <Panel className="p-4" contextItem={{ id: 'portfolio-property-type-mix', type: 'Chart', label: 'Concentração por tipo de imóvel', data: { portfolio_id: analytics.portfolio.id } }}>
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

        <p className="text-xs text-text-secondary">Preços informados: {analytics.asking_count ?? '—'} de {analytics.active_listing_count ?? '—'} imóveis ativos. Estimativas registradas: {analytics.estimated_count ?? '—'}. As listas abaixo exibem até 100 posições no total; as contagens consideram todo o portfólio.</p>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Panel className="p-4" contextItem={{ id: 'portfolio-above-estimate', type: 'Chart', label: 'Imóveis acima da estimativa', data: { portfolio_id: analytics.portfolio.id } }}>
            <SectionTitle right={<ContextTag type="MODEL">Risco</ContextTag>}>Anúncios acima da estimativa</SectionTitle>
            <div className="space-y-1">
              {analytics.above_estimate.map((property) => (
                <div key={property.property_id} className="flex items-center justify-between py-2 border-b border-border/60 last:border-0">
                  <div className="min-w-0">
                    <div className="text-xs font-medium text-foreground truncate">{property.title}</div>
                    <div className="text-[10px] text-text-muted">{property.region || 'Região não informada'} · {formatBRL(property.asking_price)}</div>
                    <EstimateProvenance provenance={property.estimate_provenance} />
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-[10px] px-1.5 py-0.5 rounded border bg-negative/10 text-negative border-negative/20">{formatPct(percent(property.price_gap))}</span>
                    <button onClick={() => sendToAgent([{ id: `portfolio-property-${property.property_id}`, type: 'Property', label: property.title, data: { id: property.property_id } }], `Explique a diferença entre o preço de anúncio e a estimativa de ${property.title}.`)} aria-label="Explicar diferença de preço" className="icon-control text-brand"><Sparkles className="w-3.5 h-3.5" /></button>
                  </div>
                </div>
              ))}
              {analytics.above_estimate.length === 0 && <div className="text-xs text-text-muted py-4 text-center">{analytics.positions_available ? 'Nenhum imóvel com preço acima da estimativa registrada' : 'Distribuição de preços indisponível'}</div>}
            </div>
          </Panel>
          <Panel className="p-4" contextItem={{ id: 'portfolio-below-estimate', type: 'Chart', label: 'Imóveis abaixo da estimativa', data: { portfolio_id: analytics.portfolio.id } }}>
            <SectionTitle right={<ContextTag type="MODEL">Oportunidade</ContextTag>}>Anúncios abaixo da estimativa</SectionTitle>
            <div className="space-y-1">
              {analytics.below_estimate.map((property) => (
                <div key={property.property_id} className="flex items-center justify-between py-2 border-b border-border/60 last:border-0">
                  <div className="min-w-0">
                    <div className="text-xs font-medium text-foreground truncate">{property.title}</div>
                    <div className="text-[10px] text-text-muted">{property.region || 'Região não informada'} · {formatBRL(property.asking_price)}</div>
                    <EstimateProvenance provenance={property.estimate_provenance} />
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-[10px] px-1.5 py-0.5 rounded border bg-positive/10 text-positive border-positive/20">{formatPct(percent(property.price_gap))}</span>
                    <button onClick={() => sendToAgent([{ id: `portfolio-property-${property.property_id}`, type: 'Property', label: property.title, data: { id: property.property_id } }], `Explique a diferença entre o preço de anúncio e a estimativa de ${property.title}.`)} aria-label="Explicar diferença de preço" className="icon-control text-brand"><Sparkles className="w-3.5 h-3.5" /></button>
                  </div>
                </div>
              ))}
              {analytics.below_estimate.length === 0 && <div className="text-xs text-text-muted py-4 text-center">{analytics.positions_available ? 'Nenhum imóvel com preço abaixo da estimativa registrada' : 'Distribuição de preços indisponível'}</div>}
            </div>
          </Panel>
        </div>

        <Panel className="p-4" contextItem={{ id: 'portfolio-risk-summary', type: 'KPI', label: 'Resumo de risco do portfólio', data: { portfolio_id: analytics.portfolio.id } }}>
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-warning shrink-0 mt-0.5" />
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <h3 className="text-sm font-semibold text-foreground">Insight do portfólio</h3>
                <ContextTag type="DATA">Evidência</ContextTag>
              </div>
              <p className="text-xs text-text-secondary leading-relaxed">{insightText}</p>
            </div>
            <button onClick={() => sendToAgent([{ id: 'portfolio', type: 'Portfolio', label: 'Portfólio completo', data: { id: analytics.portfolio.id } }], 'Interprete as evidências numéricas, os riscos, a concentração e as oportunidades do meu portfólio. Não recalcule os indicadores.') } className="shrink-0 h-8 px-3 rounded bg-brand text-brand-foreground text-xs font-medium hover:bg-brand/90 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5" /> Explicar
            </button>
          </div>
        </Panel>
        <details className="analysis-disclosure">
          <summary>Referências de mercado por região</summary>
          <p className="mt-2 text-xs text-text-secondary">Observações globais associadas às regiões do portfólio. A data representa a última observação da região; não garante a atualização de cada indicador.</p>
          <div className="overflow-x-auto"><table className="ceres-table w-full mt-3"><thead><tr><th>Região</th><th>Imóveis ativos</th><th>Preço/m² de referência</th><th>Aquecimento</th><th>Última observação</th></tr></thead>
          <tbody>{analytics.market_exposure.map((row,index) => <tr key={index}><td>{[row.area,row.city].filter(Boolean).join(', ') || 'Não informada'}</td><td>{row.estate_count}</td><td>{formatM2(row.average_price_m2)}</td><td>{row.market_heat == null ? '—' : `${Math.round(row.market_heat)}/100`}</td><td>{row.latest_observed_on || '—'}</td></tr>)}</tbody></table></div>
          {!analytics.market_exposure.length && <p className="py-3 text-xs text-text-secondary">Referências indisponíveis para este portfólio.</p>}
        </details>
        <details className="analysis-disclosure">
          <summary>Séries e indicadores <span className="text-xs font-normal text-text-secondary">{kpiMetricOptions.length} indicadores <ChevronDown className="h-4 w-4" /></span></summary>
          <div className="portfolio-indicators pt-5">
            {kpiMetricOptions.map((option) => <KpiCard key={option.id} {...option} series={enableChartExpansion ? option.series : []} metricOptions={kpiMetricOptions} />)}
          </div>
        </details>
      </div>
    </>
  );
}
