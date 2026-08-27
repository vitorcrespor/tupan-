import React, { useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { ResponsiveContainer, AreaChart, Area, LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Legend } from 'recharts';
import { Building2, ExternalLink, MapPin, Search, Sparkles } from 'lucide-react';
import TopBar from '@/components/tupan/TopBar';
import { Panel, SectionTitle, ContextTag, KpiCard } from '@/components/tupan/primitives';
import { CITIES } from '@/lib/tupanData';
import { formatBRL, formatM2, formatPct } from '@/lib/format';
import { CHART, tooltipStyle } from '@/lib/chartTheme';
import { enableChartExpansion } from '@/lib/featureFlags';
import { apiErrorMessage } from '@/api/client';
import { sendAgentMessage } from '@/api/agent';
import { getProperties, PROPERTY_KIND_OPTIONS } from '@/api/properties';
import ListingCard from '@/components/tupan/ListingCard';
import { AsyncEmpty, AsyncError, AsyncLoading } from '@/components/tupan/AsyncState';
import { getMetricHistory, limitMetricHistoryToMonths, metricHistoryToChartSeries } from '@/api/market';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';

const HORIZONS = [
  { id: 12, label: '12 meses' },
  { id: 24, label: '24 meses' },
  { id: 36, label: '36 meses' },
];

const METRIC_OPTIONS = [
  { id: 'price', label: 'Preço por m²', title: 'Preço/m² — tendência de longo prazo', key: 'price', color: CHART.aqua, formatter: formatM2, history: true },
  { id: 'inventory', label: 'Inventário', title: 'Inventário — tendência de longo prazo', key: 'inventory', color: CHART.lagoon, formatter: (value) => Math.round(value).toLocaleString('pt-BR'), history: false },
  { id: 'dom', label: 'Dias no mercado', title: 'DOM — tendência de longo prazo', key: 'dom', color: CHART.warning, formatter: (value) => `${Math.round(value)} dias`, history: false },
  { id: 'velocity', label: 'Velocidade de venda', title: 'Velocidade — tendência de longo prazo', key: 'velocity', color: CHART.mint, formatter: (value) => Number(value).toFixed(2), history: false },
];

function ChartState({ metric, query, data, height, children }) {
  const className = 'flex items-center justify-center px-6 text-center text-xs';
  if (!metric.history) return <div style={{ height }} className={`${className} text-text-muted`}>O backend ainda não fornece série histórica para esta métrica.</div>;
  if (query.isLoading) return <div style={{ height }} className={`${className} text-text-muted`}>Carregando histórico…</div>;
  if (query.isError) return <div role="alert" style={{ height }} className={`${className} text-negative`}>{apiErrorMessage(query.error)}</div>;
  if (data.length === 0) return <div style={{ height }} className={`${className} text-text-muted`}>Sem observações históricas para este recorte.</div>;
  return children;
}

export function MarketTrendMetrics({ embedded = false }) {
  const [regionName, setRegionName] = useState('all');
  const [horizon, setHorizon] = useState(24);
  const [primaryMetricId, setPrimaryMetricId] = useState('price');
  const [barMetricId, setBarMetricId] = useState('inventory');
  const [lineMetricId, setLineMetricId] = useState('dom');
  const neighborhoodOptions = CITIES.find((city) => city.name === 'São Paulo')?.neighborhoods || [];
  const area = regionName === 'all' ? undefined : regionName;

  const priceHistoryQuery = useQuery({
    queryKey: ['market-trends-price-m2', 'São Paulo', area],
    queryFn: ({ signal }) => getMetricHistory('price_m2', { city: 'São Paulo', area, signal }),
    retry: false,
  });
  const allPriceSeries = useMemo(
    () => metricHistoryToChartSeries(priceHistoryQuery.data).map((point) => ({ ...point, price: point.value })),
    [priceHistoryQuery.data],
  );
  const data = useMemo(() => limitMetricHistoryToMonths(allPriceSeries, horizon), [allPriceSeries, horizon]);

  const primaryMetric = METRIC_OPTIONS.find((option) => option.id === primaryMetricId) || METRIC_OPTIONS[0];
  const barMetric = METRIC_OPTIONS.find((option) => option.id === barMetricId) || METRIC_OPTIONS[1];
  const lineMetric = METRIC_OPTIONS.find((option) => option.id === lineMetricId) || METRIC_OPTIONS[2];
  const latestPrice = data.at(-1)?.price;
  const kpiOptions = [
    { id: 'price', label: 'Último preço por m²', value: latestPrice == null ? '—' : formatM2(latestPrice), tag: 'DATA', sub: `${data.length} observações`, series: data, seriesValueFormatter: formatM2 },
    { id: 'inventory', label: 'Variação de inventário', value: '—', tag: 'MODEL', sub: 'Histórico indisponível', series: [] },
    { id: 'dom', label: 'DOM médio', value: '—', tag: 'DATA', sub: 'Histórico indisponível', series: [] },
    { id: 'velocity', label: 'Velocidade média', value: '—', tag: 'AI', sub: 'Histórico indisponível', series: [] },
  ];
  const contextData = (metric) => ({
    metric: metric.label,
    period: `${horizon} meses`,
    series: metric.history ? data.map((point) => ({ label: point.label, value: point.price })) : [],
  });

  return (
    <>
      {!embedded && <TopBar title="Tendências de Mercado" subtitle="Análise histórica de longo prazo · São Paulo" />}
      <div className={embedded ? 'space-y-4' : 'flex-1 overflow-y-auto p-5 space-y-4'}>
        <Panel className="rounded-[22px] border-white/70 bg-card/55 p-4 shadow-[0_5px_18px_hsl(220_12%_18%/0.09),inset_0_1px_0_hsl(0_0%_100%/0.82)] backdrop-blur-xl">
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] uppercase text-text-muted">Região</span>
              <Select value={regionName} onValueChange={setRegionName}>
                <SelectTrigger className="h-8 w-auto min-w-[160px]"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todas as regiões</SelectItem>
                  {neighborhoodOptions.map((name) => <SelectItem key={name} value={name}>{name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] uppercase text-text-muted">Horizonte</span>
              <Select value={String(horizon)} onValueChange={(value) => setHorizon(Number(value))}>
                <SelectTrigger className="h-8 w-auto min-w-[120px]"><SelectValue /></SelectTrigger>
                <SelectContent>{HORIZONS.map((item) => <SelectItem key={item.id} value={String(item.id)}>{item.label}</SelectItem>)}</SelectContent>
              </Select>
            </div>
          </div>
        </Panel>

        <div className="mx-auto grid w-full max-w-[820px] grid-cols-1 gap-x-5 gap-y-6 md:grid-cols-2">
          {kpiOptions.map((option) => <KpiCard key={option.id} {...option} className="aspect-[16/10] min-h-[220px]" series={enableChartExpansion ? option.series : []} metricOptions={enableChartExpansion ? kpiOptions : []} />)}
        </div>

        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          <Panel className="aspect-[4/3] min-h-[320px] p-5" metricOptions={METRIC_OPTIONS} activeMetricId={primaryMetricId} onMetricSelect={(option) => setPrimaryMetricId(option.id)} contextItem={{ id: `chart-trends-${primaryMetric.key}`, type: 'Chart', label: primaryMetric.title, data: contextData(primaryMetric) }}>
          <SectionTitle right={<ContextTag type="DATA">{horizon}M</ContextTag>}>{primaryMetric.title}</SectionTitle>
          <ChartState metric={primaryMetric} query={priceHistoryQuery} data={data} height={240}>
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={data} margin={{ left: -10, right: 8, top: 8, bottom: 0 }}>
                <defs><linearGradient id="gPrimary" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={primaryMetric.color} stopOpacity={0.35} /><stop offset="100%" stopColor={primaryMetric.color} stopOpacity={0.02} /></linearGradient></defs>
                <CartesianGrid stroke={CHART.grid} strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="label" stroke={CHART.axis} fontSize={10} tickLine={false} axisLine={false} />
                <YAxis stroke={CHART.axis} fontSize={10} tickLine={false} axisLine={false} tickFormatter={primaryMetric.formatter} />
                <Tooltip contentStyle={tooltipStyle} formatter={(value) => primaryMetric.formatter(value)} />
                <Area type="monotone" dataKey="price" stroke={primaryMetric.color} strokeWidth={2} fill="url(#gPrimary)" />
              </AreaChart>
            </ResponsiveContainer>
          </ChartState>
        </Panel>
          <Panel className="aspect-[4/3] min-h-[320px] p-5" metricOptions={METRIC_OPTIONS} activeMetricId={barMetricId} onMetricSelect={(option) => setBarMetricId(option.id)} contextItem={{ id: `chart-trends-bar-${barMetric.key}`, type: 'Chart', label: `${barMetric.label} — movimento`, data: contextData(barMetric) }}>
            <SectionTitle right={<ContextTag type="MODEL">{horizon}M</ContextTag>}>{barMetric.label} — movimento</SectionTitle>
            <ChartState metric={barMetric} query={priceHistoryQuery} data={data} height={240}>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={data} margin={{ left: -10, right: 8, top: 4, bottom: 0 }}>
                  <CartesianGrid stroke={CHART.grid} strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="label" stroke={CHART.axis} fontSize={10} tickLine={false} axisLine={false} />
                  <YAxis stroke={CHART.axis} fontSize={10} tickLine={false} axisLine={false} tickFormatter={barMetric.formatter} />
                  <Tooltip contentStyle={tooltipStyle} cursor={{ fill: CHART.grid, opacity: 0.3 }} formatter={(value) => barMetric.formatter(value)} />
                  <Bar dataKey="price" fill={barMetric.color} radius={[6, 6, 0, 0]} barSize={14} />
                </BarChart>
              </ResponsiveContainer>
            </ChartState>
          </Panel>
          <Panel className="aspect-[4/3] min-h-[320px] p-5" metricOptions={METRIC_OPTIONS} activeMetricId={lineMetricId} onMetricSelect={(option) => setLineMetricId(option.id)} contextItem={{ id: `chart-trends-line-${lineMetric.key}`, type: 'Chart', label: `${lineMetric.label} — tendência`, data: contextData(lineMetric) }}>
            <SectionTitle right={<ContextTag type="DATA">{horizon}M</ContextTag>}>{lineMetric.label} — tendência</SectionTitle>
            <ChartState metric={lineMetric} query={priceHistoryQuery} data={data} height={240}>
              <ResponsiveContainer width="100%" height={240}>
                <LineChart data={data} margin={{ left: -10, right: 8, top: 4, bottom: 0 }}>
                  <CartesianGrid stroke={CHART.grid} strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="label" stroke={CHART.axis} fontSize={10} tickLine={false} axisLine={false} />
                  <YAxis stroke={CHART.axis} fontSize={10} tickLine={false} axisLine={false} tickFormatter={lineMetric.formatter} />
                  <Tooltip contentStyle={tooltipStyle} formatter={(value) => lineMetric.formatter(value)} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line type="monotone" dataKey="price" name={lineMetric.label} stroke={lineMetric.color} strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </ChartState>
          </Panel>
        </div>
      </div>
    </>
  );
}

function EstateAnalysisWorkspace() {
  const navigate = useNavigate();
  const [regionName, setRegionName] = useState('all');
  const [kind, setKind] = useState('all');
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState(null);
  const [analysis, setAnalysis] = useState({ status: 'idle', propertyId: null, text: '', error: null });
  const neighborhoodOptions = CITIES.find((city) => city.name === 'São Paulo')?.neighborhoods || [];
  const area = regionName === 'all' ? undefined : regionName;

  const estatesQuery = useQuery({
    queryKey: ['estate-analysis-properties', area, kind],
    queryFn: ({ signal }) => getProperties({ city: 'São Paulo', area, kind: kind === 'all' ? undefined : kind, signal }),
    retry: false,
  });

  const estates = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase('pt-BR');
    if (!normalized) return estatesQuery.data?.items || [];
    return (estatesQuery.data?.items || []).filter((property) => [property.title, property.address, property.neighborhood, property.property_type]
      .filter(Boolean)
      .some((value) => String(value).toLocaleLowerCase('pt-BR').includes(normalized)));
  }, [estatesQuery.data?.items, query]);

  const selectedEstate = selected ? estates.find((estate) => estate.id === selected.id) || selected : null;

  const runAnalysis = async () => {
    if (!selectedEstate || analysis.status === 'loading') return;
    setAnalysis({ status: 'loading', propertyId: selectedEstate.id, text: '', error: null });
    try {
      const response = await sendAgentMessage({
        message: `Analise este imóvel para um corretor imobiliário. Use apenas o contexto anexado; deixe claro o que não estiver disponível. Explique o posicionamento de preço, os principais sinais de mercado e a próxima ação recomendada em no máximo três parágrafos curtos.`,
        contextItems: [{ id: `estate-analysis-${selectedEstate.id}`, type: 'Property', label: selectedEstate.title, data: selectedEstate }],
      });
      setAnalysis({ status: 'success', propertyId: selectedEstate.id, text: response?.message?.content || 'A Ceres não retornou uma análise para este imóvel.', error: null });
    } catch (error) {
      setAnalysis({ status: 'error', propertyId: selectedEstate.id, text: '', error });
    }
  };

  return (
    <>
      <TopBar title="Análise de imóveis" subtitle={estatesQuery.isLoading ? 'Carregando imóveis…' : `${estatesQuery.data?.page?.total ?? estates.length} imóveis · Seleção visual e análise da Ceres`} />
      <div className="flex-1 overflow-y-auto p-6 space-y-6">
        <Panel className="rounded-[22px] border-white/75 bg-card/48 p-4 shadow-soft-lg">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex h-9 min-w-[220px] flex-1 items-center gap-2 rounded-xl border border-border/75 bg-card/60 px-3 backdrop-blur-sm transition-colors focus-within:border-brand/45">
              <Search className="h-3.5 w-3.5 text-text-muted" />
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar por imóvel, endereço ou bairro…" className="min-w-0 flex-1 bg-transparent text-xs text-text-secondary outline-none" />
            </div>
            <Select value={regionName} onValueChange={setRegionName}>
              <SelectTrigger className="h-9 w-auto min-w-[164px]"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todas as regiões</SelectItem>
                {neighborhoodOptions.map((name) => <SelectItem key={name} value={name}>{name}</SelectItem>)}
              </SelectContent>
            </Select>
            <Select value={kind} onValueChange={setKind}>
              <SelectTrigger className="h-9 w-auto min-w-[156px]"><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Todos os tipos</SelectItem>
                {PROPERTY_KIND_OPTIONS.map((option) => <SelectItem key={option.value} value={option.value}>{option.label}</SelectItem>)}
              </SelectContent>
            </Select>
          </div>
        </Panel>

        <div className="grid items-start gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
          <section aria-label="Lista de imóveis">
            {estatesQuery.isLoading && <AsyncLoading className="h-64" label="Carregando imóveis para análise…" />}
            {estatesQuery.isError && <AsyncError error={estatesQuery.error} />}
            {!estatesQuery.isLoading && !estatesQuery.isError && estates.length === 0 && <AsyncEmpty className="h-64">Nenhum imóvel corresponde aos filtros selecionados.</AsyncEmpty>}
            {!estatesQuery.isLoading && !estatesQuery.isError && estates.length > 0 && (
              <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 2xl:grid-cols-3">
                {estates.map((estate) => (
                  <ListingCard
                    key={estate.id}
                    property={estate}
                    onClick={setSelected}
                    onAdd={(property) => setSelected(property)}
                  />
                ))}
              </div>
            )}
          </section>

          <aside className="xl:sticky xl:top-4">
            <Panel className="rounded-[22px] border-positive/20 bg-[linear-gradient(145deg,hsl(var(--card)/.70),hsl(161_53%_94%/.36))] p-5 shadow-[0_18px_46px_hsl(160_40%_32%/.10),inset_0_1px_0_hsl(0_0%_100%/.90)]">
              <div className="mb-4 flex items-start gap-3 pr-8">
                <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl border border-positive/25 bg-positive/10 text-positive"><Building2 className="h-4 w-4" /></span>
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-[0.15em] text-positive">Ceres Analysis</p>
                  <h2 className="mt-0.5 text-sm font-semibold text-foreground">{selectedEstate ? selectedEstate.title : 'Selecione um imóvel'}</h2>
                </div>
              </div>

              {!selectedEstate && <div className="rounded-2xl border border-dashed border-border/80 bg-card/35 px-5 py-10 text-center text-xs leading-relaxed text-text-muted">Escolha um cartão de imóvel para ver seus indicadores e pedir uma leitura contextual à Ceres.</div>}

              {selectedEstate && <div className="space-y-4">
                <div className="flex items-center gap-1.5 text-xs text-text-muted"><MapPin className="h-3.5 w-3.5" />{selectedEstate.neighborhood}, {selectedEstate.city}</div>
                <div className="grid grid-cols-2 gap-2">
                  <div className="rounded-xl border border-white/70 bg-card/45 p-3"><p className="text-[9px] font-semibold uppercase tracking-wide text-text-muted">Preço listado</p><p className="mt-1 text-sm font-semibold text-foreground tnum">{formatBRL(selectedEstate.price)}</p></div>
                  <div className="rounded-xl border border-white/70 bg-card/45 p-3"><p className="text-[9px] font-semibold uppercase tracking-wide text-text-muted">Preço / m²</p><p className="mt-1 text-sm font-semibold text-foreground tnum">{formatM2(selectedEstate.price_per_m2)}</p></div>
                  <div className="rounded-xl border border-white/70 bg-card/45 p-3"><p className="text-[9px] font-semibold uppercase tracking-wide text-text-muted">Sugestão AVM</p><p className="mt-1 text-sm font-semibold text-brand tnum">{formatBRL(selectedEstate.suggested_price)}</p></div>
                  <div className="rounded-xl border border-white/70 bg-card/45 p-3"><p className="text-[9px] font-semibold uppercase tracking-wide text-text-muted">Desvio</p><p className="mt-1 text-sm font-semibold text-text-secondary tnum">{formatPct(selectedEstate.price_deviation)}</p></div>
                </div>
                {selectedEstate.api_property?.summary && <p className="rounded-xl border border-border/65 bg-card/35 p-3 text-xs leading-relaxed text-text-secondary">{selectedEstate.api_property.summary}</p>}
                <div className="space-y-2">
                  <button type="button" onClick={runAnalysis} disabled={analysis.status === 'loading'} className="flex h-10 w-full items-center justify-center gap-2 rounded-xl bg-brand text-xs font-medium text-brand-foreground transition-colors hover:bg-brand/90 disabled:cursor-wait disabled:opacity-70"><Sparkles className={`h-3.5 w-3.5 ${analysis.status === 'loading' ? 'animate-pulse' : ''}`} />{analysis.status === 'loading' && analysis.propertyId === selectedEstate.id ? 'Analisando com a Ceres…' : 'Analisar com Ceres'}</button>
                  <button type="button" onClick={() => navigate(`/properties/${selectedEstate.id}`)} className="flex h-9 w-full items-center justify-center gap-2 rounded-xl border border-border bg-card/45 text-xs text-text-secondary transition-colors hover:text-foreground"><ExternalLink className="h-3.5 w-3.5" />Ver inteligência completa</button>
                </div>
                {analysis.status === 'error' && analysis.propertyId === selectedEstate.id && <AsyncError error={analysis.error} onRetry={runAnalysis} />}
                {analysis.status === 'success' && analysis.propertyId === selectedEstate.id && <div className="rounded-2xl border border-positive/20 bg-positive/5 p-3"><p className="mb-2 text-[10px] font-bold uppercase tracking-[0.13em] text-positive">Leitura da Ceres</p><div className="prose prose-sm max-w-none text-xs leading-relaxed text-text-secondary [&_p]:my-1.5 [&_strong]:text-foreground"><ReactMarkdown>{analysis.text}</ReactMarkdown></div></div>}
              </div>}
            </Panel>
          </aside>
        </div>
      </div>
    </>
  );
}

export default function MarketTrends() {
  return <EstateAnalysisWorkspace />;
}




