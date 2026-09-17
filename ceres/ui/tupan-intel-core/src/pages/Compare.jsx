import React, { useMemo, useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { getEstatePair } from '@/api/analysis';
import { estateToView } from '@/api/properties';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { ResponsiveContainer, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Legend } from 'recharts';
import { ArrowLeftRight, MapPin } from 'lucide-react';
import TopBar from '@/components/tupan/TopBar';
import EstimateProvenance from '@/components/tupan/EstimateProvenance';
import { Panel, SectionTitle, ContextTag } from '@/components/tupan/primitives';
import { useTupanData } from '@/lib/useTupanData';
import { useApp } from '@/lib/AppContext';
import { liquidityHorizonDays as liquidityHorizonForPeriod, timePeriodLabel } from '@/lib/tupanData';
import { formatBRL, formatBRLCompact, formatM2, formatPct } from '@/lib/format';
import { valuationLabel } from '@/lib/labels';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { CHART } from '@/lib/chartTheme';
import { AsyncEmpty, AsyncError, AsyncLoading } from '@/components/tupan/AsyncState';

// direction: high = higher wins, low = lower wins, fair = closer to zero wins, neutral = no winner
const SPEC = [
  { key: 'price', label: 'Preço de pedido', fmt: formatBRL, dir: 'low' },
  { key: 'price_per_m2', label: 'Preço/m²', fmt: formatM2, dir: 'low' },
  { key: 'suggested_price', label: 'Estimativa registrada', fmt: formatBRL, dir: 'neutral' },
  { key: 'price_deviation', label: 'Desvio da estimativa (%)', fmt: (v) => formatPct(v), dir: 'fair' },
  { key: 'area_m2', label: 'Área', fmt: (v) => `${v} m²`, dir: 'high' },
  { key: 'bedrooms', label: 'Quartos', fmt: (v) => v, dir: 'high' },
  { key: 'bathrooms', label: 'Banheiros', fmt: (v) => v, dir: 'high' },
  { key: 'parking_spaces', label: 'Vagas', fmt: (v) => v, dir: 'high' },
  { key: 'property_age', label: 'Idade', fmt: (v) => `${v} anos`, dir: 'low' },
  { key: 'days_on_market', label: 'Dias no mercado', fmt: (v) => `${v}d`, dir: 'low' },
  { key: 'market_heat', label: 'Aquecimento', fmt: (v) => `${v}/100`, dir: 'high' },
  { key: 'liquidity_score', label: 'Liquidez', fmt: (v) => `${v}/100`, dir: 'high' },
  { key: 'luxury_score', label: 'Luxo', fmt: (v) => v, dir: 'high' },
  { key: 'leisure_score', label: 'Lazer', fmt: (v) => v, dir: 'high' },
  { key: 'location_score', label: 'Localização', fmt: (v) => v, dir: 'high' },
  { key: 'leverage_score', label: 'Alavancagem', fmt: (v) => v, dir: 'high' },
];

function PropertyPicker({ label, value, onChange, properties, emptyHint }) {
  return (
    <div className="comparison-picker">
      <label htmlFor={label === 'Imóvel A' ? 'compare-a' : 'compare-b'}>{label}</label>
      <Select value={value || 'none'} onValueChange={(v) => onChange(v === 'none' ? null : v)}>
        <SelectTrigger id={label === 'Imóvel A' ? 'compare-a' : 'compare-b'} className="h-9 w-full text-xs">
          <SelectValue placeholder={emptyHint} />
        </SelectTrigger>
        <SelectContent className="rounded-2xl border-border/70 bg-card/95 backdrop-blur-md max-h-72">
          <SelectItem value="none" className="rounded-full text-xs">— Remover seleção —</SelectItem>
          {properties.map((p) => (
            <SelectItem key={p.id} value={p.id} className="rounded-lg text-xs">
              {p.title} · {p.neighborhood}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

export default function Compare() {
  const { timePeriod } = useApp();
  const liquidityHorizonDays = liquidityHorizonForPeriod(timePeriod);
  const { properties, propertiesStatus, propertiesError } = useTupanData();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [aId, setAId] = useState(params.get('a') || null);
  const [bId, setBId] = useState(params.get('b') || null);

  useEffect(() => {
    const next = new URLSearchParams();
    if (aId) next.set('a', aId);
    if (bId) next.set('b', bId);
    setParams(next, { replace: true });
  }, [aId, bId]);

  const pairQuery = useQuery({
    queryKey: ['estate-pair', aId, bId, liquidityHorizonDays],
    queryFn: ({signal}) => getEstatePair(aId, bId, {signal, liquidity_horizon_days: liquidityHorizonDays}),
    enabled: Boolean(aId && bId),
  });
  const a = pairQuery.data ? estateToView(pairQuery.data.a) : properties.find(p => p.id === aId);
  const b = pairQuery.data ? estateToView(pairQuery.data.b) : properties.find(p => p.id === bId);
  const metrics = pairQuery.data?.metrics || [];

  const radarData = useMemo(() => {
    if (!a || !b) return [];
    return [
      { axis: 'Luxo', A: a.luxury_score, B: b.luxury_score },
      { axis: 'Lazer', A: a.leisure_score, B: b.leisure_score },
      { axis: 'Localização', A: a.location_score, B: b.location_score },
      { axis: 'Alavancagem', A: a.leverage_score, B: b.leverage_score },
      { axis: 'Liquidez', A: a.liquidity_score, B: b.liquidity_score },
      { axis: 'Aquecimento', A: a.market_heat, B: b.market_heat },
    ];
  }, [a, b]);

  const topDiffs = metrics.filter(row => row.difference != null && row.difference !== 0).slice(0, 5)
    .map(row => ({...SPEC.find(spec => spec.key === row.key), ...row}));

  const both = a && b && pairQuery.isSuccess;

  return (
    <>
      <TopBar title="Comparar imóveis" subtitle="Análise lado a lado · diferenças destacadas" right={
        <button onClick={() => navigate('/properties')} className="h-8 px-3 rounded-lg border border-border bg-elevated text-xs text-text-secondary hover:text-foreground flex items-center gap-1.5">
          Ver imóveis
        </button>
      } />
      <div className="workspace-content workspace-stack flex-1 overflow-y-auto">
        {propertiesStatus === 'loading' && <AsyncLoading className="h-24" label="Carregando imóveis para comparação…" />}
        {propertiesStatus === 'error' && <AsyncError error={propertiesError} />}
        {propertiesStatus === 'success' && properties.length === 0 && <AsyncEmpty className="h-24">Não há imóveis disponíveis para comparar.</AsyncEmpty>}
        {propertiesStatus === 'success' && properties.length > 0 && <>
        {pairQuery.isFetching && <AsyncLoading className="h-16" label="Comparando dados autorizados…" />}
        {pairQuery.isError && <AsyncError error={pairQuery.error} />}
        <section aria-label="Comparação de atributos">
          <div className="overflow-x-auto">
            <table className="ceres-table comparison-matrix w-full">
              <thead className="border-b border-border">
                <tr>
                  <th scope="col" className="text-left"><h2 className="text-sm font-semibold">Comparação de atributos</h2><span className="mt-1 block text-xs font-normal text-text-secondary">{SPEC.length} critérios · liquidez em {timePeriodLabel(timePeriod)}</span></th>
                  {[{ property: a, id: aId, setId: setAId, tag: 'A' }, { property: b, id: bId, setId: setBId, tag: 'B' }].map(({ property, id, setId, tag }) => (
                    <th key={tag} scope="col">
                      <PropertyPicker label={`Imóvel ${tag}`} value={id} onChange={setId} properties={properties} emptyHint={`Selecione o imóvel ${tag}`} />
                      {property && <div className="mt-3 space-y-1 text-left font-normal">
                        <div className="text-sm font-medium text-foreground">{property.title}</div>
                        <div className="flex items-center gap-1 text-xs text-text-secondary"><MapPin className="h-3 w-3 shrink-0" />{property.neighborhood}, {property.city}</div>
                        <div className="text-xs text-text-secondary">{property.area_m2 ?? '—'} m² · {valuationLabel(property.valuation_class)}</div>
                      </div>}
                    </th>
                  ))}
                  <th scope="col" className="text-xs">Diferença (B − A)</th>
                </tr>
              </thead>
              {both && <tbody>
                {SPEC.map((spec) => {
                  const row = metrics.find(item => item.key === spec.key);
                  const diff = row?.difference;
                  return <tr key={spec.key} className="border-b border-border/60">
                    <th scope="row" className="text-left font-normal text-text-secondary">{spec.label}</th>
                    <td className="text-foreground">{row?.a_value == null ? '—' : spec.fmt(row.a_value)}{spec.key === 'suggested_price' && row?.a_value != null && <EstimateProvenance provenance={a.estimate_provenance} />}</td>
                    <td className="text-foreground">{row?.b_value == null ? '—' : spec.fmt(row.b_value)}{spec.key === 'suggested_price' && row?.b_value != null && <EstimateProvenance provenance={b.estimate_provenance} />}</td>
                    <td className="text-text-secondary">{diff != null
                      ? <>{diff > 0 ? '+' : ''}{spec.key === 'price' || spec.key === 'suggested_price' ? formatBRLCompact(diff) : spec.key === 'price_per_m2' ? formatM2(diff) : Number.isInteger(diff) ? diff : diff.toFixed(1)}{row?.unit === 'percentage_points' ? ' p.p.' : ''}</>
                      : '—'}</td>
                  </tr>;
                })}
              </tbody>}
            </table>
          </div>
          {!both && <div className="flex items-start gap-3 py-8 text-text-secondary">
            <ArrowLeftRight className="h-5 w-5 shrink-0" />
            <div><p className="text-sm">Selecione dois imóveis para visualizar a comparação lado a lado.</p><p className="mt-1 text-xs">As principais diferenças nos dados serão destacadas automaticamente.</p></div>
          </div>}
        </section>

        {both && <p className="text-xs text-text-secondary">
          Semelhança estrutural por cosseno: {pairQuery.data.similarity_score == null
            ? 'indisponível por dados estruturais incompletos'
            : pairQuery.data.similarity_score.toLocaleString('pt-BR', { minimumFractionDigits: 3, maximumFractionDigits: 3 })}.
          {' '}Usa área, quartos, banheiros e vagas; não representa confiança da avaliação.
        </p>}

        {both && (
          <>
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(18rem,1fr)_minmax(0,2fr)]">
              <Panel className="p-4">
                <SectionTitle right={<ContextTag type="MODEL">Ceres 4L</ContextTag>}>Perfil comparado</SectionTitle>
                {radarData.some((point) => point.A != null || point.B != null) ? <ResponsiveContainer width="100%" height={260}>
                  <RadarChart data={radarData} outerRadius="72%">
                    <PolarGrid stroke={CHART.grid} strokeDasharray="3 4" />
                    <PolarAngleAxis dataKey="axis" tick={{ fill: CHART.axis, fontSize: 10 }} />
                    <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fill: CHART.axis, fontSize: 9 }} stroke={CHART.grid} strokeDasharray="3 4" />
                    <Radar name="Imóvel A" dataKey="A" stroke={CHART.aqua} fill={CHART.aqua} fillOpacity={0.22} strokeWidth={2} />
                    <Radar name="Imóvel B" dataKey="B" stroke={CHART.lagoon} fill={CHART.lagoon} fillOpacity={0.18} strokeWidth={2} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                  </RadarChart>
                </ResponsiveContainer> : <AsyncEmpty className="py-6">Perfil comparativo ainda indisponível.</AsyncEmpty>}
              </Panel>

              <Panel className="p-4">
                <SectionTitle right={<ContextTag type="DATA">B − A</ContextTag>}>Diferenças disponíveis</SectionTitle>
                <div className="space-y-2.5">
                  {topDiffs.map(d => <div key={d.key} className="flex items-center justify-between gap-3 py-1.5 border-b border-border/50">
                    <div><div className="text-xs text-foreground">{d.label}</div>
                    <div className="text-[10px] text-text-secondary">{d.fmt(d.a_value)} · {d.fmt(d.b_value)}</div></div>
                    <span className="text-xs tnum">{d.difference > 0 ? '+' : ''}{d.key === 'price_deviation' ? d.difference.toFixed(1) + ' p.p.' : d.fmt(d.difference)}</span>
                  </div>)}
                  {topDiffs.length === 0 && <p className="text-xs text-text-secondary">Não há diferenças entre os atributos disponíveis.</p>}
                </div>
                <p className="mt-4 text-xs text-text-secondary">Até cinco diferenças, na ordem dos atributos. Estimativas registradas, não uma nova inferência AVM. Mais ou menos em um atributo não determina o melhor investimento.</p>
                <p className="mt-2 text-xs text-text-muted">A interpretação por IA de dois imóveis simultâneos ainda não está conectada.</p>
              </Panel>
            </div>
          </>
        )}
        </>}
      </div>
    </>
  );
}
