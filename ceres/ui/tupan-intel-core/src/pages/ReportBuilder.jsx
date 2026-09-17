import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { formatM2, formatBRLCompact, formatNumber } from '@/lib/format';
import { CHART, tooltipStyle } from '@/lib/chartTheme';
import TopBar from '@/components/tupan/TopBar';
import { Panel, SectionTitle } from '@/components/tupan/primitives';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { FileDown, Sparkles, Loader2 } from 'lucide-react';
import { apiErrorMessage } from '@/api/client';
import { getMarketCells, getMetricHistory, limitMetricHistoryToMonths, metricHistoryToChartSeries } from '@/api/market';
import { sendAgentMessage } from '@/api/agent';
import { AsyncEmpty, AsyncError, AsyncLoading } from '@/components/tupan/AsyncState';
import { useApp } from '@/lib/AppContext';
import { getReportSummary } from '@/api/report';

const SECTIONS = [
  { id: 'kpis', label: 'Resumo de KPIs' },
  { id: 'priceTrend', label: 'Tendência de preço' },
  { id: 'inventory', label: 'Movimento de inventário' },
  { id: 'topProperties', label: 'Principais imóveis' },
  { id: 'aiInsights', label: 'Insights da IA' },
];

export default function ReportBuilder() {
  const { filters } = useApp();
  const reportCity = filters.city || undefined;
  const [regionId, setRegionId] = useState('all');
  const [horizon, setHorizon] = useState(12);
  const [enabled, setEnabled] = useState({ kpis: true, priceTrend: true, inventory: true, topProperties: true, aiInsights: true });
  const [aiText, setAiText] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiError, setAiError] = useState(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState(null);
  const previewRef = useRef(null);

  const regionsQuery = useQuery({
    queryKey: ['report-regions', reportCity, filters.h3Resolution || 9],
    queryFn: ({ signal }) => getMarketCells({ city: reportCity, h3Resolution: filters.h3Resolution || 9, signal }),
    retry: false,
  });
  const regions = useMemo(() => (regionsQuery.data?.cells || []).map((cell) => ({
    id: cell.id,
    label: cell.label,
    city: cell.city || null,
    area: cell.neighborhood || null,
  })), [regionsQuery.data]);
  const region = regionId === 'all' ? null : regions.find((item) => item.id === regionId) || null;
  const scopeCity = region?.city || reportCity;
  const area = region?.area || undefined;

  useEffect(() => {
    if (regionId !== 'all' && !regions.some((item) => item.id === regionId)) setRegionId('all');
  }, [regionId, regions]);

  const summaryQuery = useQuery({
    queryKey: ['report-summary', scopeCity, area],
    queryFn: ({ signal }) => getReportSummary({ city: scopeCity, area, signal }),
    retry: false,
  });
  const priceHistoryQuery = useQuery({
    queryKey: ['report-price-m2', scopeCity, area],
    queryFn: ({ signal }) => getMetricHistory('price_m2', { city: scopeCity, area, signal }),
    retry: false,
  });
  const priceData = useMemo(
    () => limitMetricHistoryToMonths(metricHistoryToChartSeries(priceHistoryQuery.data), horizon),
    [priceHistoryQuery.data, horizon],
  );
  const priceHistoryReason = priceData.find((point) => point.value == null && point.reason)?.reason || priceHistoryQuery.data?.source.reason || null;
  const summary = summaryQuery.data?.summary || null;
  const topProps = summaryQuery.data?.featured_estates || [];
  const velocity = summaryQuery.data?.market_metrics.find((metric) => metric.metric === 'sales_velocity') || null;

  const generateAI = async () => {
    if (!summary) return;
    setAiLoading(true);
    setAiError(null);
    try {
      const res = await sendAgentMessage({
        message: 'Você é um analista de mercado imobiliário. Escreva um resumo executivo de três parágrafos em português, destacando tendências, riscos e oportunidades. Use exclusivamente a evidência determinística autorizada do resumo de relatório.',
        reportScope: { city: scopeCity, area },
      });
      setAiText(res.message.content);
    } catch (error) {
      setAiError(error);
    } finally {
      setAiLoading(false);
    }
  };

  const exportPDF = async () => {
    if (!previewRef.current) return;
    setExporting(true);
    setExportError(null);
    try {
      const [{ default: html2canvas }, { jsPDF }] = await Promise.all([
        import('html2canvas'),
        import('jspdf'),
      ]);
      const canvas = await html2canvas(previewRef.current, { scale: 2, backgroundColor: '#ffffff' });
      const img = canvas.toDataURL('image/png');
      const pdf = new jsPDF({ orientation: 'portrait', unit: 'pt', format: 'a4' });
      const pageW = pdf.internal.pageSize.getWidth();
      const pageH = pdf.internal.pageSize.getHeight();
      const imgW = pageW;
      const imgH = (canvas.height * imgW) / canvas.width;
      let heightLeft = imgH;
      let position = 0;
      pdf.addImage(img, 'PNG', 0, position, imgW, imgH);
      heightLeft -= pageH;
      while (heightLeft > 0) {
        position -= pageH;
        pdf.addPage();
        pdf.addImage(img, 'PNG', 0, position, imgW, imgH);
        heightLeft -= pageH;
      }
      pdf.save(`relatorio-ceres-${new Date().toISOString().slice(0, 10)}.pdf`);
    } catch (error) {
      setExportError(error);
    } finally {
      setExporting(false);
    }
  };

  const toggle = (id) => setEnabled((s) => ({ ...s, [id]: !s[id] }));

  return (
    <>
      <TopBar title="Gerador de Relatórios" subtitle="Monte e exporte relatórios compartilháveis" />
      <div className="workspace-content flex-1 overflow-y-auto">
        <div className="grid grid-cols-1 lg:grid-cols-[280px_minmax(0,1fr)] gap-6">
          <Panel className="p-4 h-fit space-y-4">
            <SectionTitle>Seções</SectionTitle>
            <div className="flex flex-col gap-2">
              {SECTIONS.map((s) => (
                <label key={s.id} className="flex items-center gap-2 text-sm text-foreground cursor-pointer">
                  <input type="checkbox" checked={enabled[s.id]} onChange={() => toggle(s.id)} className="accent-brand w-4 h-4" />
                  {s.label}
                </label>
              ))}
            </div>
            <div className="space-y-2 pt-2 border-t border-border">
              {regionsQuery.isLoading && <AsyncLoading className="h-8" label="Carregando regiões…" />}
              {regionsQuery.isError && <AsyncError error={regionsQuery.error} />}
              <div>
                <span className="text-[10px] uppercase text-text-muted">Região</span>
                <Select value={regionId} onValueChange={setRegionId}>
                  <SelectTrigger className="h-8 w-full mt-1"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Todas as regiões</SelectItem>
                    {regions.map((r) => <SelectItem key={r.id} value={r.id}>{r.label}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <span className="text-[10px] uppercase text-text-muted">Horizonte</span>
                <Select value={String(horizon)} onValueChange={(v) => setHorizon(Number(v))}>
                  <SelectTrigger className="h-8 w-full mt-1"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {[6, 12, 24].map((h) => <SelectItem key={h} value={String(h)}>{h} meses</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <button onClick={exportPDF} disabled={exporting} className="w-full h-9 rounded-full bg-brand text-brand-foreground text-sm font-medium flex items-center justify-center gap-1.5 disabled:opacity-50">
              {exporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileDown className="w-4 h-4" />}
              {exporting ? 'Gerando…' : 'Exportar PDF'}
            </button>
            {exportError && <AsyncError error={exportError} />}
          </Panel>

          <div ref={previewRef} className="min-w-0 bg-card rounded-2xl border border-border p-4 sm:p-6 space-y-5">
            <div className="border-b border-border pb-3">
              <h1 className="text-2xl font-semibold text-foreground">Relatório de Mercado — Ceres</h1>
              <p className="text-sm text-text-secondary">{region ? region.label : 'Todas as regiões'} · {new Date().toLocaleDateString('pt-BR')}</p>
            </div>

            {enabled.kpis && (
              summaryQuery.isSuccess && summary ? <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[
                  { l: 'Preço/m² médio', v: formatM2(summary.average_price_per_m2), sub: `Pedido médio ${formatBRLCompact(summary.average_asking_price)} · ${summary.price_per_m2_count}/${summary.asking_price_count} observações` },
                  { l: 'Inventário ativo', v: formatNumber(summary.active_estate_count) },
                  { l: 'DOM médio', v: summary.average_days_on_market == null ? '—' : `${Math.round(summary.average_days_on_market)}d`, sub: `${summary.days_on_market_count} observações` },
                  { l: 'Velocidade', v: velocity?.value == null ? '—' : velocity.value.toFixed(2), sub: velocity?.unit || undefined },
                ].map((k) => (
                  <div key={k.l} className="rounded-xl border border-border bg-elevated/50 p-3">
                    <div className="text-[10px] uppercase text-text-muted">{k.l}</div>
                    <div className="text-lg font-semibold tnum text-foreground">{k.v}</div>
                    {k.sub && <div className="mt-1 text-[10px] text-text-muted">{k.sub}</div>}
                  </div>
                ))}
              </div> : summaryQuery.isError ? <AsyncError error={summaryQuery.error} /> : summaryQuery.isSuccess ? <AsyncEmpty className="h-20">O resumo do recorte não está disponível.</AsyncEmpty> : <AsyncLoading className="h-20" label="Carregando indicadores…" />
            )}

            {enabled.priceTrend && (
              <div>
                <h2 className="text-sm font-semibold text-foreground mb-2">Tendência de preço/m²</h2>
                {priceHistoryQuery.isLoading && <div className="h-[220px] flex items-center justify-center text-xs text-text-muted">Carregando histórico…</div>}
                {priceHistoryQuery.isError && <div role="alert" className="h-[220px] flex items-center justify-center px-6 text-center text-xs text-negative">{apiErrorMessage(priceHistoryQuery.error)}</div>}
                {!priceHistoryQuery.isLoading && !priceHistoryQuery.isError && !priceData.some((point) => point.value != null) && <div className="h-[220px] flex items-center justify-center text-center text-xs text-text-muted">Sem observações históricas de preço/m² para este recorte.</div>}
                {!priceHistoryQuery.isLoading && !priceHistoryQuery.isError && priceData.some((point) => point.value != null) && <ResponsiveContainer width="100%" height={220}>
                  <AreaChart data={priceData} margin={{ left: -10, right: 8, top: 4, bottom: 0 }}>
                    <defs>
                      <linearGradient id="rp" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={CHART.aqua} stopOpacity={0.35} />
                        <stop offset="100%" stopColor={CHART.aqua} stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke={CHART.grid} strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="label" stroke={CHART.axis} fontSize={10} tickLine={false} axisLine={false} />
                    <YAxis stroke={CHART.axis} fontSize={10} tickLine={false} axisLine={false} tickFormatter={(v) => (v >= 1000 ? (v / 1000).toFixed(0) + 'K' : v)} />
                    <Tooltip contentStyle={tooltipStyle} formatter={(v) => formatM2(v)} />
                    <Area type="monotone" dataKey="value" stroke={CHART.aqua} strokeWidth={2} fill="url(#rp)" />
                  </AreaChart>
                </ResponsiveContainer>}
                {!priceHistoryQuery.isLoading && !priceHistoryQuery.isError && priceHistoryReason && <p className="mt-2 text-xs text-text-muted">Lacunas na série: {priceHistoryReason}</p>}
              </div>
            )}

            {enabled.inventory && (
              <div>
                <h2 className="text-sm font-semibold text-foreground mb-2">Movimento de inventário</h2>
                <div className="h-[200px] flex items-center justify-center px-6 text-center text-xs text-text-muted">O backend ainda não fornece série histórica de inventário.</div>
              </div>
            )}

            {enabled.topProperties && (
              <div>
                <h2 className="text-sm font-semibold text-foreground mb-2">Imóveis do recorte</h2>
                {summaryQuery.isLoading && <AsyncLoading className="h-20" label="Carregando imóveis…" />}
                {summaryQuery.isError && <AsyncError error={summaryQuery.error} />}
                {summaryQuery.isSuccess && summary && topProps.length === 0 && <AsyncEmpty className="h-20">Nenhum imóvel ativo está disponível neste recorte.</AsyncEmpty>}
                {summaryQuery.isSuccess && topProps.length > 0 &&
                <table className="ceres-table w-full">
                  <thead>
                    <tr className="text-text-muted text-left border-b border-border">
                      <th className="py-1.5 font-medium">Imóvel</th>
                      <th>Bairro</th>
                      <th className="text-right">Preço</th>
                      <th className="text-right">Atualização</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topProps.map((p) => (
                      <tr key={p.id} className="border-b border-border/50">
                        <td className="py-1.5 text-foreground">{p.title}</td>
                        <td className="text-text-secondary">{p.area || p.city || '—'}</td>
                        <td className="text-right tnum text-foreground">{formatBRLCompact(p.asking_price)}</td>
                        <td className="text-right tnum text-text-secondary">{new Date(p.updated_at).toLocaleDateString('pt-BR')}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                }
              </div>
            )}

            {enabled.aiInsights && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h2 className="text-sm font-semibold text-foreground">Insights da IA</h2>
                  <button onClick={generateAI} disabled={aiLoading || !summary} className="h-7 px-3 rounded-full bg-brand/10 text-brand text-xs font-medium flex items-center gap-1.5 disabled:opacity-50">
                    {aiLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                    {aiText ? 'Regenerar' : 'Gerar'}
                  </button>
                </div>
                {aiError ? <AsyncError error={aiError} /> : aiText ? <p className="text-sm text-text-secondary whitespace-pre-wrap leading-6">{aiText}</p> : <p className="text-sm text-text-muted">{summary ? 'Clique em "Gerar" para produzir o resumo executivo com IA.' : 'O resumo fica disponível quando os dados do relatório forem carregados.'}</p>}
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
