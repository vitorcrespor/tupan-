import React, { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from 'recharts';
import { Sparkles } from 'lucide-react';
import TopBar from '@/components/tupan/TopBar';
import { ContextTag, Panel, SectionTitle } from '@/components/tupan/primitives';
import { useApp } from '@/lib/AppContext';
import { formatM2, formatNumber, formatPct } from '@/lib/format';
import { apiErrorMessage } from '@/api/client';
import { CHART, tooltipStyle } from '@/lib/chartTheme';
import { formatMetricDate, getMarketCells, H3_RESOLUTION_OPTIONS, periodToDays, publishedMetricHistory } from '@/api/market';
import { useMarketAnalytics } from '@/lib/useMarketAnalytics';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

const formatVelocity = (value) => value != null && Number.isFinite(Number(value)) ? `${Number(value).toFixed(2)} vendas/dia` : '—';

const METRICS = {
  Price: [
    { id: 'average_price_m2', label: 'Preço/m²', value: (cell) => cell.average_price_m2, format: formatM2, history: true },
    { id: 'price_growth_pct', label: 'Crescimento de preço', value: (cell) => cell.price_growth_pct, format: formatPct },
  ],
  Demand: [
    { id: 'market_heat', label: 'Aquecimento de mercado', value: (cell) => cell.market_heat, format: (value) => value == null ? '—' : `${Math.round(value)}/100` },
    { id: 'liquidity', label: 'Liquidez', value: (cell) => cell.liquidity, format: (value) => value == null ? '—' : `${Math.round(value)}/100` },
    { id: 'average_dom_days', label: 'Dias no mercado', value: (cell) => cell.average_dom_days, format: (value) => value == null ? '—' : `${Math.round(value)}d` },
  ],
  Inventory: [
    { id: 'inventory', label: 'Anúncios ativos', value: (cell) => cell.inventory, format: formatNumber },
    { id: 'sales_velocity', label: 'Velocidade de vendas', value: (cell) => cell.sales_velocity, format: formatVelocity },
  ],
};

const CATEGORY_LABELS = { Price: 'Preço', Demand: 'Demanda', Inventory: 'Inventário' };
const cellName = (cell) => cell?.label || 'Célula H3';
const scoreText = (score) => score == null ? '—' : `${Math.round(score)}/100`;

function historyChartData(primary, comparison) {
  const points = new Map();
  (primary?.values || []).forEach((point) => points.set(point.date, { date: point.date, a: point.value }));
  (comparison?.values || []).forEach((point) => {
    const key = point.date;
    points.set(key, { ...(points.get(key) || { date: key }), b: point.value });
  });
  return [...points.values()].sort((a, b) => a.date.localeCompare(b.date)).map((point) => ({ ...point, label: formatMetricDate(point.date) }));
}

export default function MarketIntelligence({ embedded = false }) {
  const { sendToAgent, filters, setFilters, setSelectedRegion, timePeriod } = useApp();
  const [category, setCategory] = useState('Price');
  const [metricId, setMetricId] = useState('average_price_m2');
  const [geo, setGeo] = useState('all');
  const [compare, setCompare] = useState('none');

  const metric = METRICS[category].find((item) => item.id === metricId) || METRICS[category][0];
  const cellFilters = useMemo(() => ({ city: filters.city || undefined, h3Resolution: filters.h3Resolution || 9, liquidityHorizonDays: periodToDays(timePeriod) }), [filters.city, filters.h3Resolution, timePeriod]);

  const allCellsQuery = useQuery({
    queryKey: ['market-intelligence-cells', cellFilters],
    queryFn: ({ signal }) => getMarketCells({ ...cellFilters, signal }),
  });
  const cells = allCellsQuery.data?.cells || [];

  const primaryCell = cells.find(cell => cell.h3_index === geo);
  const comparisonCell = cells.find(cell => cell.h3_index === compare);
  const metricKey = ({average_price_m2:'price_m2',price_growth_pct:'price_growth',average_dom_days:'dom',inventory:'active_listings'})[metric.id] || metric.id;
  const historyScope = geo === 'all'
    ? { city: cellFilters.city, liquidityHorizonDays: cellFilters.liquidityHorizonDays }
    : { h3Index: geo, liquidityHorizonDays: cellFilters.liquidityHorizonDays };
  const marketQuery = useMarketAnalytics(historyScope);
  const hasHistory = true;
  const primaryHistoryQuery = {...marketQuery, data:publishedMetricHistory(marketQuery.data,metricKey)};
  const comparisonHistoryQuery = {data:undefined,isError:false,error:null};

  const chartCells = geo === 'all' ? cells : primaryCell ? [primaryCell] : [];
  const barData = chartCells
    .map((cell) => ({ name: cell.label, value: metric.value(cell), h3_index: cell.h3_index }))
    .filter((item) => item.value != null);
  const scatter = cells
    .filter((cell) => cell.market_heat != null && cell.average_price_m2 != null)
    .map((cell) => ({ x: cell.market_heat, y: cell.average_price_m2, z: cell.inventory, name: cell.label }));
  const historyData = historyChartData(primaryHistoryQuery.data, comparisonHistoryQuery.data);
  const historyReason = primaryHistoryQuery.data?.values.find((point) => point.value == null && point.reason)?.reason || primaryHistoryQuery.data?.source.reason || null;
  const cellOptions = [...cells].sort((a, b) => a.label.localeCompare(b.label));
  const promptData = { metric: metricKey, city: cellFilters.city, h3_resolution: cellFilters.h3Resolution };

  return (
    <>
      {!embedded && <TopBar title="Inteligência de Mercado" subtitle="Análises geográficas calculadas por células H3" />}
      <div className={embedded ? "space-y-6" : "workspace-content workspace-stack flex-1 overflow-y-auto"}>
        <div className="analysis-toolbar">
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] uppercase text-text-muted">Métrica</span>
              <Select value={category} onValueChange={(value) => { setCategory(value); setMetricId(METRICS[value][0].id); }}>
                <SelectTrigger className="h-8 w-auto min-w-[110px]"><SelectValue /></SelectTrigger>
                <SelectContent>{Object.keys(METRICS).map((key) => <SelectItem key={key} value={key}>{CATEGORY_LABELS[key]}</SelectItem>)}</SelectContent>
              </Select>
              <Select value={metricId} onValueChange={setMetricId}>
                <SelectTrigger className="h-8 w-auto min-w-[150px]"><SelectValue /></SelectTrigger>
                <SelectContent>{METRICS[category].map((item) => <SelectItem key={item.id} value={item.id}>{item.label}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] uppercase text-text-muted">Geografia</span>
              <Select value={geo} onValueChange={setGeo}>
                <SelectTrigger className="h-8 w-auto min-w-[180px]"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todas as células H3</SelectItem>
                  {cellOptions.map((cell) => <SelectItem key={cell.h3_index} value={cell.h3_index}>{cell.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] uppercase text-text-muted">Comparar</span>
              <Select value={compare} onValueChange={setCompare}>
                <SelectTrigger className="h-8 w-auto min-w-[180px]"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Nenhuma</SelectItem>
                  {cellOptions.filter((cell) => cell.h3_index !== geo).map((cell) => <SelectItem key={cell.h3_index} value={cell.h3_index}>{cell.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="text-[10px] uppercase text-text-muted">Agregação</span>
              <Select value={String(cellFilters.h3Resolution)} onValueChange={(value) => {
                setSelectedRegion(null);
                setGeo('all');
                setCompare('none');
                // Keep map and intelligence views on the same published H3 snapshot.
                // This is a presentation preference, never a backend calculation.
                setFilters((current) => ({ ...current, h3Resolution: Number(value) }));
              }}>
                <SelectTrigger aria-label="Resolução H3" className="h-8 w-auto min-w-[132px]"><SelectValue /></SelectTrigger>
                <SelectContent>{H3_RESOLUTION_OPTIONS.map((resolution) => <SelectItem key={resolution.value} value={String(resolution.value)}>{resolution.label}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <button disabled={geo !== 'all' || compare !== 'none'} title={geo !== 'all' || compare !== 'none' ? 'Interpretação de células específicas ainda não conectada' : undefined} onClick={() => sendToAgent([{ id: `mi-${metric.id}-${geo}`, type: 'Metric', label: metric.label, data: promptData }], `Explique ${metric.label} para ${geo === 'all' ? 'as células H3 consultadas' : cellName(primaryCell)}.`)} className="ml-auto h-8 px-3.5 rounded-lg bg-brand text-brand-foreground text-xs font-medium hover:bg-brand/90 flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5" /> Explicar esta análise
            </button>
          </div>
        </div>

        {allCellsQuery.isError && <div role="alert" className="rounded border border-negative/30 bg-negative/10 p-3 text-xs text-negative">{apiErrorMessage(allCellsQuery.error)}</div>}
        {allCellsQuery.isLoading && <div className="flex items-center justify-center py-16"><div className="w-8 h-8 border-4 border-border border-t-brand rounded-full animate-spin" /></div>}
        {!allCellsQuery.isLoading && !allCellsQuery.isError && cells.length === 0 && <div className="py-12 text-center text-xs text-text-muted">Nenhuma célula H3 retornada para este mercado.</div>}

        {!allCellsQuery.isLoading && <>
          <div className="analysis-split">
            <Panel className="p-4">
              <SectionTitle right={<ContextTag type="DATA">Histórico</ContextTag>}>{metric.label} — Tendência</SectionTitle>
              {hasHistory && <p className="mb-2 text-xs text-text-muted">{geo === 'all' ? cellFilters.city : cellName(primaryCell)} · {primaryHistoryQuery.data.unit} · {primaryHistoryQuery.data.source.label}</p>}
              {hasHistory && primaryHistoryQuery.isLoading && <div className="h-[240px] flex items-center justify-center text-xs text-text-muted">Carregando histórico…</div>}
              {hasHistory && primaryHistoryQuery.isError && <div role="alert" className="h-[240px] flex items-center justify-center text-xs text-negative text-center px-6">{apiErrorMessage(primaryHistoryQuery.error)}</div>}
              {hasHistory && !primaryHistoryQuery.isLoading && !primaryHistoryQuery.isError && comparisonHistoryQuery.isError && <div role="alert" className="mb-2 rounded border border-negative/30 bg-negative/10 p-2 text-xs text-negative">O histórico da célula de comparação não pôde ser carregado: {apiErrorMessage(comparisonHistoryQuery.error)}</div>}
              {hasHistory && !primaryHistoryQuery.isLoading && !primaryHistoryQuery.isError && historyData.length === 0 && <div className="h-[240px] flex items-center justify-center text-xs text-text-muted">Sem pontos históricos para este recorte.</div>}
              {hasHistory && !primaryHistoryQuery.isLoading && !primaryHistoryQuery.isError && historyData.length > 0 && <ResponsiveContainer width="100%" height={240}>
                <LineChart data={historyData} margin={{ left: -10, right: 8, top: 4, bottom: 0 }}>
                  <CartesianGrid stroke={CHART.grid} strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="label" stroke={CHART.axis} fontSize={10} tickLine={false} axisLine={false} />
                  <YAxis stroke={CHART.axis} fontSize={10} tickLine={false} axisLine={false} tickFormatter={(value) => value >= 1000 ? `${(value / 1000).toFixed(0)}K` : value} />
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                  <Line type="monotone" dataKey="a" name={geo === 'all' ? cellFilters.city : cellName(primaryCell)} stroke={CHART.aqua} strokeWidth={2} dot={false} />
                  {comparisonCell && <Line type="monotone" dataKey="b" name={cellName(comparisonCell)} stroke={CHART.positive} strokeWidth={2} dot={false} />}
                </LineChart>
              </ResponsiveContainer>}
              {hasHistory && !primaryHistoryQuery.isLoading && !primaryHistoryQuery.isError && historyReason && <p className="mt-2 text-xs text-text-muted">Lacunas na série: {historyReason}</p>}
            </Panel>
            <Panel className="p-4">
              <SectionTitle right={<ContextTag type="DATA">H3</ContextTag>}>{metric.label} por célula H3</SectionTitle>
              {allCellsQuery.isLoading && geo !== 'all' && <div className="h-[240px] flex items-center justify-center text-xs text-text-muted">Carregando célula H3…</div>}
              {allCellsQuery.isError && geo !== 'all' && <div role="alert" className="mb-2 rounded border border-negative/30 bg-negative/10 p-2 text-xs text-negative">{apiErrorMessage(allCellsQuery.error)}</div>}
              {!allCellsQuery.isLoading && (barData.length === 0 ? <div className="h-[240px] flex items-center justify-center text-xs text-text-muted">Sem valores para esta métrica.</div> : <ResponsiveContainer width="100%" height={240}>
                <BarChart data={barData} margin={{ left: -10, right: 8, top: 4, bottom: 0 }}>
                  <CartesianGrid stroke={CHART.grid} strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="name" stroke={CHART.axis} fontSize={9} tickLine={false} axisLine={false} angle={-30} textAnchor="end" height={60} />
                  <YAxis stroke={CHART.axis} fontSize={10} tickLine={false} axisLine={false} tickFormatter={(value) => value >= 1000 ? `${(value / 1000).toFixed(0)}K` : value} />
                  <Tooltip formatter={(value) => metric.format(value)} contentStyle={tooltipStyle} cursor={{ fill: CHART.aqua, fillOpacity: 0.12 }} />
                  <Bar dataKey="value" fill={CHART.aqua} radius={[8, 8, 0, 0]} barSize={18} />
                </BarChart>
              </ResponsiveContainer>)}
            </Panel>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <Panel className="p-4 lg:col-span-2">
              <SectionTitle right={<ContextTag type="MODEL">H3</ContextTag>}>Aquecimento de mercado vs Preço/m²</SectionTitle>
              {scatter.length === 0 ? <div className="h-[240px] flex items-center justify-center text-xs text-text-muted">As células retornadas não possuem aquecimento e preço/m² simultaneamente.</div> : <ResponsiveContainer width="100%" height={240}>
                <ScatterChart margin={{ left: -10, right: 12, top: 4, bottom: 4 }}>
                  <CartesianGrid stroke={CHART.grid} strokeDasharray="3 3" />
                  <XAxis type="number" dataKey="x" name="Aquecimento" stroke={CHART.axis} fontSize={10} tickLine={false} axisLine={false} />
                  <YAxis type="number" dataKey="y" name="Preço/m²" stroke={CHART.axis} fontSize={10} tickLine={false} axisLine={false} tickFormatter={(value) => `${(value / 1000).toFixed(0)}K`} />
                  <ZAxis type="number" dataKey="z" range={[60, 400]} />
                  <Tooltip contentStyle={tooltipStyle} cursor={{ stroke: CHART.aqua, strokeDasharray: '3 3' }} />
                  <Scatter data={scatter} fill={CHART.aqua} fillOpacity={0.6} />
                </ScatterChart>
              </ResponsiveContainer>}
            </Panel>
            <Panel className="p-4">
              <SectionTitle right={<ContextTag type="DATA">Comparar</ContextTag>}>Comparação de células</SectionTitle>
              {allCellsQuery.isLoading && <div className="py-12 text-center text-xs text-text-muted">Carregando célula de comparação…</div>}
              {allCellsQuery.isError && <div role="alert" className="mb-2 rounded border border-negative/30 bg-negative/10 p-2 text-xs text-negative">{apiErrorMessage(allCellsQuery.error)}</div>}
              {!allCellsQuery.isLoading && (!primaryCell || !comparisonCell ? <div className="py-12 text-center text-xs text-text-muted">Selecione duas células H3 para comparar valores calculados.</div> : <>
                <div className="grid grid-cols-3 gap-1 text-[10px] uppercase text-text-muted mb-2"><span>Métrica</span><span className="text-right truncate">{cellName(primaryCell)}</span><span className="text-right truncate">{cellName(comparisonCell)}</span></div>
                {[
                  { label: 'Preço/m²', primary: formatM2(primaryCell.average_price_m2), comparison: formatM2(comparisonCell.average_price_m2) },
                  { label: 'Crescimento', primary: formatPct(primaryCell.price_growth_pct), comparison: formatPct(comparisonCell.price_growth_pct) },
                  { label: 'DOM', primary: primaryCell.average_dom_days == null ? '—' : `${Math.round(primaryCell.average_dom_days)}d`, comparison: comparisonCell.average_dom_days == null ? '—' : `${Math.round(comparisonCell.average_dom_days)}d` },
                  { label: 'Inventário', primary: formatNumber(primaryCell.inventory), comparison: formatNumber(comparisonCell.inventory) },
                  { label: 'Velocidade', primary: formatVelocity(primaryCell.sales_velocity), comparison: formatVelocity(comparisonCell.sales_velocity) },
                  { label: 'Aquecimento', primary: scoreText(primaryCell.market_heat), comparison: scoreText(comparisonCell.market_heat) },
                  { label: `Liquidez · ${cellFilters.liquidityHorizonDays || '—'}d`, primary: scoreText(primaryCell.liquidity), comparison: scoreText(comparisonCell.liquidity) },
                ].map((row) => <div key={row.label} className="grid grid-cols-3 gap-1 py-1.5 border-b border-border/60 last:border-0 text-xs"><span className="text-text-secondary">{row.label}</span><span className="text-right tnum text-foreground">{row.primary}</span><span className="text-right tnum text-foreground">{row.comparison}</span></div>)}
              </>)}
            </Panel>
          </div>
        </>}
      </div>
    </>
  );
}
