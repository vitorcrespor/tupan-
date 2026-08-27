import React, { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, PieChart, Pie, Cell } from 'recharts';
import TopBar from '@/components/tupan/TopBar';
import { Panel, SectionTitle, KpiCard, ContextTag } from '@/components/tupan/primitives';
import AiBrief from '@/components/tupan/AiBrief';
import ListingCard from '@/components/tupan/ListingCard';
import { useApp } from '@/lib/AppContext';
import { useTupanData } from '@/lib/useTupanData';
import { computeMarketStats } from '@/lib/analytics';
import { formatBRLCompact, formatBRL, formatM2, formatPct, formatNumber, heatLabel } from '@/lib/format';
import { AlertTriangle, Sparkles, TrendingUp, TrendingDown } from 'lucide-react';
import { ChartAreaInteractive } from '@/components/charts/chart-area-interactive';
import { CHART, tooltipStyle } from '@/lib/chartTheme';
import { apiErrorMessage } from '@/api/client';
import { getMetricHistory, metricHistoryToChartSeries } from '@/api/market';
import { getPortfolioAnalytics } from '@/api/portfolio';
import { AsyncEmpty, AsyncError, AsyncLoading } from '@/components/tupan/AsyncState';
import MarketIntelligence from '@/pages/MarketIntelligence';
import { MarketTrendMetrics } from '@/pages/MarketTrends';

export default function Overview() {
  const { properties, regions, propertiesStatus, regionsStatus, propertiesError, regionsError } = useTupanData();
  const navigate = useNavigate();
  const { addAgentContext } = useApp();
  const featured = useMemo(
    () => [...(properties || [])].sort((a, b) => (b.market_heat || 0) - (a.market_heat || 0)).slice(0, 3),
    [properties]
  );
  const ms = useMemo(
    () => regionsStatus === 'success'
      ? computeMarketStats(regions)
      : { medianM2: null, avgHeat: null, avgDom: null, totalInventory: null, avgGrowth: null, avgVelocity: null },
    [regions, regionsStatus],
  );
  const portfolioQuery = useQuery({
    queryKey: ['overview-portfolio-analytics'],
    queryFn: ({ signal }) => getPortfolioAnalytics({ signal }),
    retry: false,
  });
  const ps = useMemo(() => {
    const analytics = portfolioQuery.data;
    if (!analytics) {
      return { totalValue: null, activeCount: null, avgPrice: null, median: null, avgM2: null, avgDom: null, avgDeviation: null, avgLiquidity: null, concentration: [], topConcentration: null, overpriced: [], underpriced: [], fair: [] };
    }
    const valuationItem = (item) => ({
      title: item.title,
      price: item.asking_price,
      suggested_price: item.estimated_price,
      price_deviation: item.price_gap == null ? null : item.price_gap * 100,
    });
    const concentration = (analytics.regional_concentration || []).map((item) => ({ name: item.region, value: item.portfolio_value, pct: item.share * 100 }));
    return {
      totalValue: analytics.portfolio_value,
      activeCount: analytics.active_listing_count,
      avgPrice: analytics.average_asking_price,
      median: analytics.median_asking_price,
      avgM2: analytics.average_price_per_m2,
      avgDom: analytics.average_dom_days,
      avgDeviation: analytics.average_price_gap == null ? null : analytics.average_price_gap * 100,
      avgLiquidity: null,
      concentration,
      topConcentration: concentration.slice(0, 2).reduce((total, item) => total + item.pct, 0),
      overpriced: (analytics.above_estimate || []).map(valuationItem),
      underpriced: (analytics.below_estimate || []).map(valuationItem),
      fair: [],
    };
  }, [portfolioQuery.data]);

  const priceHistoryQuery = useQuery({
    queryKey: ['overview-price-m2', 'São Paulo'],
    queryFn: ({ signal }) => getMetricHistory('price_m2', { city: 'São Paulo', signal }),
    retry: false,
  });
  const priceSeries = useMemo(() => metricHistoryToChartSeries(priceHistoryQuery.data), [priceHistoryQuery.data]);
  const latestPricePerM2 = priceSeries.at(-1)?.value ?? ms.medianM2;
  const domSeries = [];
  const invSeries = [];
  const kpiSeries = useMemo(() => ({
    portfolioValue: [],
    activeListings: [],
    medianM2: priceSeries,
    avgDom: domSeries,
    marketHeat: [],
    avgDeviation: [],
    liquidity: [],
  }), [priceSeries]);
  const kpiMetricOptions = [
    { id: 'portfolio-value', label: 'Valor do portfólio', value: formatBRLCompact(ps.totalValue), tag: 'DATA', series: kpiSeries.portfolioValue, seriesValueFormatter: formatBRLCompact },
    { id: 'active-listings', label: 'Anúncios ativos', value: ps.activeCount ?? '—', tag: 'DATA', series: kpiSeries.activeListings, seriesValueFormatter: formatNumber },
    { id: 'median-m2', label: 'Último preço/m²', value: formatM2(latestPricePerM2), tag: 'DATA', series: kpiSeries.medianM2, seriesValueFormatter: formatM2 },
    { id: 'avg-dom', label: 'DOM médio', value: ps.avgDom == null ? '—' : `${Math.round(ps.avgDom)}d`, tag: 'DATA', sub: 'dias', series: kpiSeries.avgDom, seriesValueFormatter: (value) => `${Math.round(value)}d` },
    { id: 'market-heat', label: 'Aquecimento de mercado', value: ms.avgHeat == null ? '—' : `${Math.round(ms.avgHeat)}/100`, tag: 'MODEL', sub: ms.avgHeat == null ? 'Indisponível' : heatLabel(ms.avgHeat), series: kpiSeries.marketHeat, seriesValueFormatter: (value) => `${Math.round(value)}/100` },
    { id: 'avm-deviation', label: 'Desvio médio AVM', value: formatPct(ps.avgDeviation), tag: 'MODEL', series: kpiSeries.avgDeviation, seriesValueFormatter: formatPct },
  ];

  const concData = ps.concentration.slice(0, 6).map((c) => ({ name: c.name, value: Math.round(c.pct) }));
  const distData = [
    { name: 'Sobreavaliado', value: ps.overpriced.length, color: CHART.negative },
    { name: 'Preço justo', value: ps.fair.length, color: CHART.aqua },
    { name: 'Subavaliado', value: ps.underpriced.length, color: CHART.positive },
  ];

  const alerts = useMemo(() => {
    const out = [];
    if (ps.topConcentration > 50) out.push({ tone: 'warn', icon: AlertTriangle, text: `${ps.topConcentration.toFixed(0)}% do valor do portfólio concentrado em ${ps.concentration.slice(0, 2).map((c) => c.name).join(' e ')}.` });
    ps.overpriced.slice(0, 2).forEach((p) => out.push({ tone: 'neg', icon: TrendingUp, text: `${p.title} sobreavaliado em ${formatPct(p.price_deviation)} (R$ ${Math.round((p.price - p.suggested_price) / 1000)}K acima do AVM).` }));
    ps.underpriced.slice(0, 1).forEach((p) => out.push({ tone: 'pos', icon: TrendingDown, text: `${p.title} subavaliado em ${formatPct(p.price_deviation)} — oportunidade de reprecificação.` }));
    if (ms.avgHeat > 70) out.push({ tone: 'pos', icon: TrendingUp, text: `Aquecimento de mercado em ${Math.round(ms.avgHeat)}/100 — ambiente de demanda forte.` });
    return out;
  }, [ps, ms]);

  const briefPrompt = `Portfólio: ${formatNumber(ps.activeCount)} anúncios ativos, valor total ${formatBRL(ps.totalValue)}, preço médio ${formatBRL(ps.avgPrice)}, mediana ${formatBRL(ps.median)}, preço/m² médio ${formatM2(ps.avgM2)}, DOM médio ${ps.avgDom == null ? '—' : Math.round(ps.avgDom)} dias, desvio médio do AVM ${formatPct(ps.avgDeviation)}, liquidez prevista ${ps.avgLiquidity == null ? '—' : `${Math.round(ps.avgLiquidity)}/100`}. Concentração geográfica: as 2 principais regiões concentram ${ps.topConcentration == null ? '—' : `${ps.topConcentration.toFixed(0)}%`} (${ps.concentration.slice(0, 2).map((c) => c.name).join(', ') || '—'}). ${ps.overpriced.length} anúncios acima da estimativa, ${ps.underpriced.length} abaixo da estimativa. Mercado: mediana de preço/m² ${formatM2(ms.medianM2)}, aquecimento médio ${ms.avgHeat == null ? '—' : `${Math.round(ms.avgHeat)}/100`}, DOM médio ${ms.avgDom == null ? '—' : Math.round(ms.avgDom)}, inventário total ${formatNumber(ms.totalInventory)}, crescimento médio ${formatPct(ms.avgGrowth)}.`;

  return (
    <>
      <TopBar title="Visão Geral" subtitle="Centro de Comando · São Paulo" />
      <div className="flex-1 overflow-y-auto p-6 lg:p-8 space-y-12">
        {portfolioQuery.isError && <AsyncError error={portfolioQuery.error} />}
        {portfolioQuery.isLoading && <AsyncLoading className="h-6" label="Carregando indicadores do portfólio…" />}
        {regionsStatus === 'error' && <AsyncError error={regionsError} />}
        {regionsStatus === 'loading' && <AsyncLoading className="h-6" label="Carregando indicadores regionais…" />}
        {regionsStatus === 'success' && regions.length === 0 && <AsyncEmpty className="h-6">Nenhum indicador regional está disponível.</AsyncEmpty>}

        <section aria-label="Inteligência Ceres" className="mx-auto w-full max-w-[1320px]">
          <Panel
            className="overflow-visible rounded-[24px] border-brand/20 bg-[linear-gradient(132deg,hsl(var(--card)/.70),hsl(182_54%_94%/.48)_48%,hsl(var(--card)/.62))] p-5 shadow-[0_18px_48px_hsl(185_40%_34%/.12),inset_0_1px_0_hsl(0_0%_100%/.96),inset_0_-18px_34px_hsl(188_60%_72%/.09)]"
            contextItem={{ id: 'overview-ceres-intelligence', type: 'AI Brief', label: 'Leitura Ceres do mercado', data: { prompt: briefPrompt, alerts: alerts.map((alert) => alert.text) } }}
          >
            <div className="mb-5 flex flex-wrap items-start justify-between gap-3 pr-10">
              <div className="flex items-start gap-3">
                <span className="grid h-10 w-10 shrink-0 place-items-center rounded-2xl border border-positive/25 bg-positive/10 text-positive shadow-[inset_0_1px_0_hsl(0_0%_100%/.75)]">
                  <Sparkles className="h-4 w-4" />
                </span>
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-positive">Ceres Intelligence</p>
                  <h2 className="mt-0.5 text-base font-semibold tracking-tight text-foreground">Comentário e insights prioritários</h2>
                  <p className="mt-1 text-xs text-text-muted">Interpretação da IA ancorada nos indicadores disponíveis e alertas calculados.</p>
                </div>
              </div>
              <ContextTag type="AI">Atualização ao vivo</ContextTag>
            </div>
            <div className="grid gap-5 lg:grid-cols-[minmax(0,1.7fr)_minmax(280px,1fr)]">
              <AiBrief prompt={briefPrompt} title="Comentário de mercado" className="rounded-2xl border border-white/75 bg-card/42 p-4 shadow-[inset_0_1px_0_hsl(0_0%_100%/.84)] backdrop-blur-xl" />
              <div className="rounded-2xl border border-white/75 bg-card/42 p-4 shadow-[inset_0_1px_0_hsl(0_0%_100%/.84)] backdrop-blur-xl">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <h3 className="text-[11px] font-semibold uppercase tracking-wider text-text-secondary">Insights dos dados</h3>
                  <span className="text-[10px] font-medium text-text-muted">{alerts.length}</span>
                </div>
                <div className="space-y-2">
                  {alerts.length === 0 && <div className="py-5 text-center text-xs text-text-muted">Sem insights calculados para os dados disponíveis.</div>}
                  {alerts.slice(0, 4).map((alert, index) => {
                    const Icon = alert.icon;
                    const tone = alert.tone === 'pos' ? 'text-positive' : alert.tone === 'neg' ? 'text-negative' : 'text-warning';
                    return (
                      <div key={`${alert.text}-${index}`} className="flex items-start gap-2.5 border-b border-border/55 py-2 last:border-0 last:pb-0">
                        <Icon className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${tone}`} />
                        <span className="text-xs leading-relaxed text-text-secondary">{alert.text}</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          </Panel>
        </section>

        <section aria-label="Resumo operacional" className="mx-auto w-full max-w-[1320px] space-y-5">
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-text-muted">Resumo</p>
              <h2 className="mt-1 text-base font-semibold tracking-tight text-foreground">Pulso do mercado e do portfólio</h2>
            </div>
            <ContextTag type="DATA">Agora</ContextTag>
          </div>
          <div className="grid grid-cols-1 gap-x-6 gap-y-8 sm:grid-cols-2 xl:grid-cols-3">
            {kpiMetricOptions.map((option) => <KpiCard key={option.id} {...option} className="aspect-[4/3] min-h-[270px]" metricOptions={kpiMetricOptions} />)}
          </div>
        </section>

        <section aria-label="Tendências de mercado" className="mx-auto w-full max-w-[1320px] space-y-4">
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-text-muted">Mercado</p>
              <h2 className="mt-1 text-base font-semibold tracking-tight text-foreground">Tendências de mercado</h2>
            </div>
            <ContextTag type="DATA">Histórico</ContextTag>
          </div>
          <MarketTrendMetrics embedded />
        </section>

        <section aria-label="Atividade e interesse" className="mx-auto w-full max-w-[1320px] space-y-4">
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-text-muted">Atividade</p>
              <h2 className="mt-1 text-base font-semibold tracking-tight text-foreground">Interesse e interação</h2>
            </div>
            <ContextTag type="DATA">90 dias</ContextTag>
          </div>
          <Panel className="overflow-visible rounded-[22px] p-0" contextItem={{ id: 'overview-visitors-interaction', type: 'Chart', label: 'Visitantes — Interação', data: { period: '90 dias', metrics: ['visitantes desktop', 'visitantes mobile'] } }}>
            <ChartAreaInteractive />
          </Panel>
        </section>

        <section aria-label="Diagnóstico do portfólio" className="mx-auto w-full max-w-[1320px] space-y-4">
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-text-muted">Portfólio</p>
              <h2 className="mt-1 text-base font-semibold tracking-tight text-foreground">Concentração e posicionamento</h2>
            </div>
            <ContextTag type="MODEL">AVM</ContextTag>
          </div>
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(250px,1fr)]">
          <Panel className="rounded-[18px] p-5 shadow-soft-lg" contextItem={{ id: 'overview-geographic-concentration', type: 'Chart', label: 'Concentração geográfica', data: { concentration: concData } }}>
            <SectionTitle right={<ContextTag type="DATA">Portfólio</ContextTag>}>Concentração geográfica</SectionTitle>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={concData} layout="vertical" margin={{ left: 20, right: 8, top: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="concGrad" x1="0" y1="0" x2="1" y2="0">
                    <stop offset="0%" stopColor={CHART.aqua} stopOpacity={0.45} />
                    <stop offset="100%" stopColor={CHART.lagoon} stopOpacity={0.95} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke={CHART.grid} strokeDasharray="3 4" horizontal={false} />
                <XAxis type="number" stroke={CHART.axis} fontSize={10} tickLine={false} axisLine={false} unit="%" />
                <YAxis type="category" dataKey="name" stroke={CHART.axis} fontSize={11} tickLine={false} axisLine={false} width={90} />
                <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: CHART.tooltipLabel }} cursor={{ fill: CHART.aqua, fillOpacity: 0.08 }} />
                <Bar dataKey="value" fill="url(#concGrad)" radius={[0, 8, 8, 0]} barSize={14} />
              </BarChart>
            </ResponsiveContainer>
          </Panel>
          <Panel className="rounded-[18px] p-5 shadow-soft-lg" contextItem={{ id: 'overview-price-positioning', type: 'Chart', label: 'Distribuição de posicionamento de preço', data: { distribution: distData } }}>
            <SectionTitle right={<ContextTag type="MODEL">AVM</ContextTag>}>Distribuição de posicionamento de preço</SectionTitle>
            <div className="flex items-center gap-4">
              <ResponsiveContainer width={160} height={180}>
                <PieChart>
                  <Pie data={distData} dataKey="value" nameKey="name" cx="50%" cy="50%" innerRadius={42} outerRadius={68} paddingAngle={3} stroke="hsl(190 55% 99%)" strokeWidth={2}>
                    {distData.map((d) => <Cell key={d.name} fill={d.color} />)}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} />
                </PieChart>
              </ResponsiveContainer>
              <div className="flex-1 space-y-2">
                {distData.map((d) => (
                  <div key={d.name} className="flex items-center justify-between text-xs">
                    <span className="flex items-center gap-2 text-text-secondary"><span className="w-2 h-2 rounded-full" style={{ background: d.color }} />{d.name}</span>
                    <span className="tnum text-foreground">{d.value}</span>
                  </div>
                ))}
              </div>
            </div>
          </Panel>
          </div>
        </section>

        <section id="market-metrics" aria-label="Análise geográfica de mercado" className="mx-auto w-full max-w-[1320px] space-y-5">
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-text-muted">Mercado</p>
              <h2 className="mt-1 text-base font-semibold tracking-tight text-foreground">Análise geográfica do mercado</h2>
            </div>
            <ContextTag type="MODEL">H3</ContextTag>
          </div>
          <MarketIntelligence embedded />
        </section>

        <section aria-label="Anúncios em destaque" className="mx-auto w-full max-w-[1320px] space-y-4">
          <div className="flex items-end justify-between gap-4">
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-text-muted">Imóveis</p>
              <h2 className="mt-1 text-base font-semibold tracking-tight text-foreground">Anúncios em destaque</h2>
            </div>
            <ContextTag type="DATA">Portfólio</ContextTag>
          </div>
          {propertiesStatus === 'loading' && <AsyncLoading className="h-40" label="Carregando imóveis em destaque…" />}
          {propertiesStatus === 'error' && <AsyncError error={propertiesError} />}
          {propertiesStatus === 'success' && featured.length === 0 && <AsyncEmpty className="h-40">Nenhum imóvel disponível para destacar.</AsyncEmpty>}
          {propertiesStatus === 'success' && featured.length > 0 && <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5 justify-items-center">
            {featured.map((p) => (
              <ListingCard
                key={p.id}
                property={p}
                onAdd={(prop) => addAgentContext({ id: prop.id, type: 'property', label: prop.title, data: prop })}
              />
            ))}
          </div>}
        </section>
      </div>
    </>
  );
}



