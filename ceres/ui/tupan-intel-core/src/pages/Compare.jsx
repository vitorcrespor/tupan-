import React, { useMemo, useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { ResponsiveContainer, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Legend } from 'recharts';
import { ArrowLeftRight, Sparkles, MapPin, Trophy } from 'lucide-react';
import TopBar from '@/components/tupan/TopBar';
import { Panel, SectionTitle, ContextTag } from '@/components/tupan/primitives';
import { useTupanData } from '@/lib/useTupanData';
import { useApp } from '@/lib/AppContext';
import { formatBRL, formatBRLCompact, formatM2, formatPct, classBadge } from '@/lib/format';
import { valuationLabel } from '@/lib/labels';
import { cn } from '@/lib/utils';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { CHART } from '@/lib/chartTheme';
import { AsyncEmpty, AsyncError, AsyncLoading } from '@/components/tupan/AsyncState';

// direction: high = higher wins, low = lower wins, fair = closer to zero wins, neutral = no winner
const SPEC = [
  { key: 'price', label: 'Preço de pedido', fmt: formatBRL, dir: 'low' },
  { key: 'price_per_m2', label: 'Preço/m²', fmt: formatM2, dir: 'low' },
  { key: 'suggested_price', label: 'AVM sugerido', fmt: formatBRL, dir: 'neutral' },
  { key: 'price_deviation', label: 'Desvio do AVM', fmt: (v) => formatPct(v), dir: 'fair' },
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
  { key: 'valuation_confidence', label: 'Confiança AVM', fmt: (v) => `${v}%`, dir: 'high' },
];

function compareRow(a, b, field, dir) {
  const av = a?.[field];
  const bv = b?.[field];
  if (av == null || bv == null) return { aWins: null, diff: null };
  let aWins = null;
  if (dir === 'high') aWins = av > bv;
  else if (dir === 'low') aWins = av < bv;
  else if (dir === 'fair') aWins = Math.abs(av) < Math.abs(bv);
  return { aWins, diff: bv - av };
}

function PropertyPicker({ label, accent, value, onChange, properties, emptyHint }) {
  return (
    <Panel className="p-4 flex flex-col gap-3" style={{ borderTop: `2px solid ${accent}` }}>
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-mono uppercase tracking-wider text-text-muted">{label}</span>
        <span className="w-2.5 h-2.5 rounded-full" style={{ background: accent, boxShadow: `0 0 10px -1px ${accent}` }} />
      </div>
      <Select value={value || 'none'} onValueChange={(v) => onChange(v === 'none' ? null : v)}>
        <SelectTrigger className="h-9 w-full rounded-full border-border/70 bg-card/70 backdrop-blur-sm text-xs">
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
    </Panel>
  );
}

export default function Compare() {
  const { properties, propertiesStatus, propertiesError } = useTupanData();
  const { sendToAgent } = useApp();
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

  const a = useMemo(() => properties.find((p) => p.id === aId) || null, [properties, aId]);
  const b = useMemo(() => properties.find((p) => p.id === bId) || null, [properties, bId]);

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

  const topDiffs = useMemo(() => {
    if (!a || !b) return [];
    return SPEC.filter((s) => s.dir !== 'neutral' && s.dir !== 'fair')
      .map((s) => {
        const av = a[s.key], bv = b[s.key];
        const base = Math.abs(av) || 1;
        return { ...s, av, bv, rel: Math.abs(bv - av) / base, abs: Math.abs(bv - av) };
      })
      .filter((s) => s.rel > 0.001)
      .sort((x, y) => y.rel - x.rel)
      .slice(0, 5);
  }, [a, b]);

  const both = a && b;

  return (
    <>
      <TopBar title="Comparar imóveis" subtitle="Análise lado a lado · diferenças destacadas" right={
        <button onClick={() => navigate('/properties')} className="h-8 px-3 rounded-full border border-border bg-elevated text-xs text-text-secondary hover:text-foreground flex items-center gap-1.5">
          Ver imóveis
        </button>
      } />
      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        {propertiesStatus === 'loading' && <AsyncLoading className="h-24" label="Carregando imóveis para comparação…" />}
        {propertiesStatus === 'error' && <AsyncError error={propertiesError} />}
        {propertiesStatus === 'success' && properties.length === 0 && <AsyncEmpty className="h-24">Não há imóveis disponíveis para comparar.</AsyncEmpty>}
        {propertiesStatus === 'success' && properties.length > 0 && <>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <PropertyPicker label="Imóvel A" accent={CHART.aqua} value={aId} onChange={setAId} properties={properties} emptyHint="Selecione o imóvel A" />
          <PropertyPicker label="Imóvel B" accent={CHART.lagoon} value={bId} onChange={setBId} properties={properties} emptyHint="Selecione o imóvel B" />
        </div>

        {!both && (
          <Panel className="p-10 flex flex-col items-center justify-center text-center gap-2">
            <ArrowLeftRight className="w-8 h-8 text-text-muted" strokeWidth={1.5} />
            <p className="text-sm text-text-secondary">Selecione dois imóveis acima para visualizar a comparação lado a lado.</p>
            <p className="text-xs text-text-muted">As principais diferenças nos dados serão destacadas automaticamente.</p>
          </Panel>
        )}

        {both && (
          <>
            {/* header cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {[{ p: a, accent: CHART.aqua, tag: 'A' }, { p: b, accent: CHART.lagoon, tag: 'B' }].map(({ p, accent, tag }) => (
                <Panel key={tag} className="p-4" style={{ borderTop: `2px solid ${accent}` }}>
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-full text-white" style={{ background: accent }}>Imóvel {tag}</span>
                        <span className={cn('text-[10px] px-1.5 py-0.5 rounded border', classBadge(p.valuation_class))}>{valuationLabel(p.valuation_class)}</span>
                      </div>
                      <h3 className="text-sm font-semibold text-foreground mt-1.5 truncate">{p.title}</h3>
                      <div className="flex items-center gap-1 text-[11px] text-text-muted mt-0.5"><MapPin className="w-3 h-3" />{p.neighborhood}, {p.city}</div>
                    </div>
                    <div className="text-right shrink-0">
                      <div className="text-lg font-semibold tnum text-foreground">{formatBRL(p.price)}</div>
                      <div className="text-[10px] text-text-muted tnum">{formatM2(p.price_per_m2)}/m² · {p.area_m2}m²</div>
                    </div>
                  </div>
                </Panel>
              ))}
            </div>

            {/* comparison table */}
            <Panel className="p-0 overflow-hidden">
              <div className="flex items-center justify-between px-4 h-11 border-b border-border">
                <span className="text-[11px] font-mono uppercase tracking-wider text-text-muted">Comparação de atributos</span>
                <ContextTag type="DATA">{SPEC.length} critérios</ContextTag>
              </div>
              <div className="grid grid-cols-[1fr_auto_1fr_auto] text-xs">
                {/* header row */}
                <div className="px-4 py-2 text-[10px] font-mono uppercase text-text-muted border-b border-border">Imóvel A</div>
                <div className="px-3 py-2" />
                <div className="px-4 py-2 text-[10px] font-mono uppercase text-text-muted border-b border-border text-right">Imóvel B</div>
                <div className="px-3 py-2 border-b border-border" />
                {SPEC.map((s) => {
                  const { aWins, diff } = compareRow(a, b, s.key, s.dir);
                  const aTone = aWins === true ? 'text-positive' : aWins === false ? 'text-negative' : 'text-foreground';
                  const bTone = aWins === true ? 'text-negative' : aWins === false ? 'text-positive' : 'text-foreground';
                  const winnerSide = aWins === true ? 'A' : aWins === false ? 'B' : null;
                  return (
                    <React.Fragment key={s.key}>
                      <div className={cn('px-4 py-2.5 tnum font-medium border-b border-border/50 flex items-center gap-1.5', aTone)}>
                        {aWins === true && <Trophy className="w-3 h-3 text-positive" />}
                        {s.fmt(a[s.key])}
                      </div>
                      <div className="px-3 py-2.5 border-b border-border/50 text-text-muted text-[11px] flex items-center justify-center text-center">{s.label}</div>
                      <div className={cn('px-4 py-2.5 tnum font-medium border-b border-border/50 text-right flex items-center justify-end gap-1.5', bTone)}>
                        {s.fmt(b[s.key])}
                        {aWins === false && <Trophy className="w-3 h-3 text-positive" />}
                      </div>
                      <div className="px-3 py-2.5 border-b border-border/50">
                        {diff != null && s.dir !== 'neutral' && (
                          <span className={cn('tnum text-[10px] px-1.5 py-0.5 rounded-full border', winnerSide ? 'border-border bg-elevated/60 text-text-secondary' : 'border-transparent text-text-muted')}>
                            {diff > 0 ? '+' : ''}{s.key === 'price' || s.key === 'suggested_price' ? formatBRLCompact(diff) : s.key === 'price_per_m2' ? formatM2(diff) : Number.isInteger(diff) ? diff : diff.toFixed(1)}
                          </span>
                        )}
                      </div>
                    </React.Fragment>
                  );
                })}
              </div>
            </Panel>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <Panel className="p-4">
                <SectionTitle right={<ContextTag type="MODEL">Ceres 4L</ContextTag>}>Perfil comparado</SectionTitle>
                <ResponsiveContainer width="100%" height={260}>
                  <RadarChart data={radarData} outerRadius="72%">
                    <PolarGrid stroke={CHART.grid} strokeDasharray="3 4" />
                    <PolarAngleAxis dataKey="axis" tick={{ fill: CHART.axis, fontSize: 10 }} />
                    <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fill: CHART.axis, fontSize: 9 }} stroke={CHART.grid} strokeDasharray="3 4" />
                    <Radar name="Imóvel A" dataKey="A" stroke={CHART.aqua} fill={CHART.aqua} fillOpacity={0.22} strokeWidth={2} />
                    <Radar name="Imóvel B" dataKey="B" stroke={CHART.lagoon} fill={CHART.lagoon} fillOpacity={0.18} strokeWidth={2} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                  </RadarChart>
                </ResponsiveContainer>
              </Panel>

              <Panel className="p-4">
                <SectionTitle right={<ContextTag type="AI">Destaques</ContextTag>}>Principais diferenças</SectionTitle>
                <div className="space-y-2.5">
                  {topDiffs.map((d) => {
                    const winner = d.bv > d.av ? (d.dir === 'high' ? b : a) : (d.dir === 'high' ? a : b);
                    const accent = winner === a ? CHART.aqua : CHART.lagoon;
                    const verb = d.dir === 'low' ? 'vantagem em' : 'destaque em';
                    return (
                      <div key={d.key} className="flex items-center gap-2.5 py-1.5 border-b border-border/50 last:border-0">
                        <span className="w-2 h-2 rounded-full shrink-0" style={{ background: accent }} />
                        <div className="flex-1 min-w-0">
                          <div className="text-xs text-foreground">{d.label}</div>
                          <div className="text-[10px] text-text-muted truncate">
                            {winner.title} tem {verb} {d.label.toLowerCase()} ({d.fmt(winner[d.key])} vs {d.fmt(winner === a ? b[d.key] : a[d.key])})
                          </div>
                        </div>
                        <span className="text-[10px] tnum text-text-secondary shrink-0">
                          {d.diff > 0 ? '+' : ''}{d.key === 'price' ? formatBRLCompact(d.diff) : Number.isInteger(d.diff) ? d.diff : d.diff.toFixed(1)}
                        </span>
                      </div>
                    );
                  })}
                </div>
                <button
                  onClick={() => sendToAgent(
                    [
                      { id: `prop-${a.id}`, type: 'Property', label: a.title, data: a },
                      { id: `prop-${b.id}`, type: 'Property', label: b.title, data: b },
                    ],
                    `Compare os imóveis ${a.title} (${a.neighborhood}) e ${b.title} (${b.neighborhood}) lado a lado e recomende o melhor investimento.`
                  )}
                  className="w-full mt-4 h-9 rounded-full bg-brand text-brand-foreground text-xs font-medium hover:bg-brand/90 flex items-center justify-center gap-1.5"
                >
                  <Sparkles className="w-3.5 h-3.5" /> Analisar comparação com Ceres
                </button>
              </Panel>
            </div>
          </>
        )}
        </>}
      </div>
    </>
  );
}
