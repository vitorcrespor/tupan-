import React, { useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ResponsiveContainer, Radar, RadarChart, PolarAngleAxis, PolarGrid, PolarRadiusAxis } from 'recharts';
import { ArrowLeft, FileText, MapPin, Sparkles } from 'lucide-react';
import TopBar from '@/components/tupan/TopBar';
import { ContextTag, MetricRow, Panel, ScoreBar, SectionTitle } from '@/components/tupan/primitives';
import { useApp } from '@/lib/AppContext';
import { classBadge, formatBRL, formatM2, formatPct } from '@/lib/format';
import { cn } from '@/lib/utils';
import { apiErrorMessage } from '@/api/client';
import { getPropertyForecast } from '@/api/forecast';
import { getProperty, getPropertyValuation } from '@/api/properties';

function valueOrDash(value) {
  return value == null ? '—' : value;
}

export default function PropertyDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { sendToAgent } = useApp();

  const {
    data: property,
    isLoading: isPropertyLoading,
    isError: isPropertyError,
    error: propertyError,
  } = useQuery({
    queryKey: ['property', id],
    queryFn: ({ signal }) => getProperty(id, { signal }),
    enabled: Boolean(id),
  });

  const {
    data: valuation,
    isLoading: isValuationLoading,
    isError: isValuationError,
    error: valuationError,
  } = useQuery({
    queryKey: ['property-valuation', id],
    queryFn: ({ signal }) => getPropertyValuation(id, { signal }),
    enabled: Boolean(id && property),
    retry: false,
  });

  const {
    data: forecast,
    isLoading: isForecastLoading,
    isError: isForecastError,
    error: forecastError,
  } = useQuery({
    queryKey: ['property-forecast', id, 180],
    queryFn: ({ signal }) => getPropertyForecast(id, { timeSpanDays: 180, signal }),
    enabled: Boolean(id && property),
    retry: false,
  });

  const profile = useMemo(() => [
    { name: 'Luxo', value: property?.profile_scores?.luxury ?? null },
    { name: 'Lazer', value: property?.profile_scores?.leisure ?? null },
    { name: 'Localização', value: property?.profile_scores?.location ?? null },
    { name: 'Alavancagem', value: property?.profile_scores?.leverage ?? null },
  ], [property]);

  const valuationDeviationPct = valuation?.difference_percent ?? (valuation?.deviation == null ? null : valuation.deviation * 100);
  const valuationDifference = valuation?.difference ?? (valuation ? valuation.current_price - valuation.suggested_price : null);
  const forecastGrowthPct = forecast?.expected_growth_pct ?? null;

  if (!id) {
    return <div className="flex-1 flex items-center justify-center text-text-muted text-sm">Identificador do imóvel ausente.</div>;
  }
  if (isPropertyLoading) {
    return <div className="flex-1 flex items-center justify-center"><div className="w-8 h-8 border-4 border-border border-t-brand rounded-full animate-spin" /></div>;
  }
  if (isPropertyError) {
    return <div role="alert" className="flex-1 flex items-center justify-center p-5 text-negative text-sm">{apiErrorMessage(propertyError)}</div>;
  }
  if (!property) {
    return <div className="flex-1 flex items-center justify-center text-text-muted text-sm">Imóvel não encontrado.</div>;
  }

  const title = property.title;
  const address = [property.address, property.neighborhood, property.city].filter((value) => value && value !== '—').join(', ') || 'Endereço indisponível';
  const valuationStatus = isValuationLoading
    ? 'Avaliação em andamento'
    : valuation
      ? 'Avaliação disponível'
      : 'Avaliação indisponível';

  return (
    <>
      <TopBar title={title} subtitle={`${property.neighborhood}, ${property.city}`} right={
        <button onClick={() => navigate('/properties')} className="h-8 px-3 rounded border border-border bg-elevated text-xs text-text-secondary hover:text-foreground flex items-center gap-1.5">
          <ArrowLeft className="w-3.5 h-3.5" /> Voltar
        </button>
      } />
      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Panel className="p-4 lg:col-span-2">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-lg font-semibold text-foreground">{title}</h2>
                <div className="flex items-center gap-1.5 text-xs text-text-muted mt-1"><MapPin className="w-3 h-3" />{address}</div>
              </div>
              <span className={cn('text-[10px] px-2 py-1 rounded border', classBadge('Unavailable'))}>{valuationStatus}</span>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
              <div><div className="text-[10px] uppercase text-text-muted">Preço de pedido</div><div className="text-xl font-semibold tnum text-foreground">{formatBRL(property.price)}</div></div>
              <div><div className="text-[10px] uppercase text-text-muted">Preço/m²</div><div className="text-xl font-semibold tnum text-foreground">{formatM2(property.price_per_m2)}</div></div>
              <div><div className="text-[10px] uppercase text-text-muted">Sugerido (AVM)</div><div className="text-xl font-semibold tnum text-brand">{isValuationLoading ? 'Calculando…' : formatBRL(valuation?.suggested_price)}</div></div>
              <div><div className="text-[10px] uppercase text-text-muted">Desvio</div><div className={cn('text-xl font-semibold tnum', valuationDeviationPct > 5 ? 'text-negative' : valuationDeviationPct < -5 ? 'text-positive' : 'text-text-secondary')}>{isValuationLoading ? '…' : formatPct(valuationDeviationPct)}</div></div>
            </div>
            <div className="grid grid-cols-3 md:grid-cols-6 gap-2 mt-4 pt-4 border-t border-border">
              {[
                { l: 'Quartos', v: property.bedrooms }, { l: 'Banhos', v: property.bathrooms }, { l: 'Vagas', v: property.parking_spaces },
                { l: 'Área', v: property.area_m2 == null ? null : `${property.area_m2}m²` }, { l: 'Idade', v: property.property_age == null ? null : `${property.property_age}a` }, { l: 'Status', v: null },
              ].map((item) => (
                <div key={item.l}><div className="text-[10px] uppercase text-text-muted">{item.l}</div><div className="text-sm font-medium text-foreground">{valueOrDash(item.v)}</div></div>
              ))}
            </div>
          </Panel>
          <Panel className="p-4">
            <SectionTitle right={<ContextTag type="MODEL">AVM</ContextTag>}>Avaliação</SectionTitle>
            {isValuationLoading && <div className="py-4 text-xs text-text-muted">Executando inferência do modelo…</div>}
            {isValuationError && <div role="alert" className="my-3 rounded border border-negative/30 bg-negative/10 p-2 text-xs text-negative">{apiErrorMessage(valuationError)}</div>}
            {!isValuationLoading && !isValuationError && valuation && <>
              <MetricRow label="Preço listado" value={formatBRL(valuation.listed_price ?? valuation.current_price)} />
              <MetricRow label="Preço sugerido" value={formatBRL(valuation.estimated_price ?? valuation.suggested_price)} />
              <MetricRow label="Diferença" value={formatBRL(valuationDifference)} />
              <MetricRow label="Desvio" value={<span className={valuationDeviationPct > 5 ? 'text-negative' : valuationDeviationPct < -5 ? 'text-positive' : 'text-text-secondary'}>{formatPct(valuationDeviationPct)}</span>} />
              <MetricRow label="Preço/m² listado" value={formatM2(valuation.price_per_m2 ?? property.price_per_m2)} />
              <MetricRow label="Preço/m² estimado" value={formatM2(valuation.estimated_price_per_m2)} />
              <MetricRow label="Última venda" value={formatBRL(property.last_sale_price)} />
              <MetricRow label="Modelo" value={valuation.model_available ? 'Disponível' : 'Indisponível'} />
            </>}
            {!isValuationLoading && !isValuationError && !valuation && <div className="py-4 text-xs text-text-muted">Avaliação indisponível.</div>}
            <button onClick={() => sendToAgent([{ id: `prop-${property.id}`, type: 'Property', label: title, data: property }], `Explique a avaliação de ${title}.`)} className="w-full mt-3 h-9 rounded bg-brand text-brand-foreground text-xs font-medium hover:bg-brand/90 flex items-center justify-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5" /> Explicar avaliação
            </button>
          </Panel>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Panel className="p-4">
            <SectionTitle right={<ContextTag type="DATA">Mercado</ContextTag>}>Contexto de mercado</SectionTitle>
            <MetricRow label="Aquecimento de mercado" value="—" />
            <MetricRow label="DOM do imóvel" value={property.days_on_market == null ? '—' : `${property.days_on_market} dias`} />
            <MetricRow label="Crescimento previsto (6M)" value={isForecastLoading ? 'Calculando…' : forecastGrowthPct == null ? '—' : <span className={forecastGrowthPct >= 0 ? 'text-positive' : 'text-negative'}>{formatPct(forecastGrowthPct)}</span>} />
            <MetricRow label="Inventário" value="—" />
            <MetricRow label="Escore de liquidez" value="—" />
            {isForecastError && <div role="alert" className="mt-3 rounded border border-negative/30 bg-negative/10 p-2 text-xs text-negative">{apiErrorMessage(forecastError)}</div>}
          </Panel>
          <Panel className="p-4">
            <SectionTitle right={<ContextTag type="MODEL">Ceres 4L</ContextTag>}>Perfil do imóvel</SectionTitle>
            <ResponsiveContainer width="100%" height={180}>
              <RadarChart data={profile}>
                <PolarGrid stroke="#E8DFD0" strokeDasharray="3 3" />
                <PolarAngleAxis dataKey="name" tick={{ fill: '#8A7A68', fontSize: 10 }} />
                <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fill: '#9A8A78', fontSize: 9 }} stroke="#E8DFD0" strokeDasharray="3 3" />
                <Radar dataKey="value" stroke="#DC6A4A" fill="#DC6A4A" fillOpacity={0.3} />
              </RadarChart>
            </ResponsiveContainer>
            <div className="space-y-2 mt-2">
              {profile.map((metric) => metric.value == null
                ? <MetricRow key={metric.name} label={metric.name} value="—" />
                : <ScoreBar key={metric.name} label={metric.name} value={metric.value} />
              )}
            </div>
          </Panel>
          <Panel className="p-4">
            <SectionTitle right={<ContextTag type="DATA">—</ContextTag>}>Imóveis comparáveis</SectionTitle>
            <div className="py-8 text-center text-xs text-text-muted">Comparáveis não são fornecidos pelo contrato de propriedades atual.</div>
          </Panel>
        </div>

        <div className="flex gap-2">
          <button onClick={() => sendToAgent([{ id: `prop-${property.id}`, type: 'Property', label: title, data: property }], `Analise ${title} em ${property.neighborhood}.`)} className="h-9 px-4 rounded bg-brand text-brand-foreground text-xs font-medium hover:bg-brand/90 flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5" /> Analisar com Ceres
          </button>
          <button onClick={() => sendToAgent([{ id: `prop-${property.id}`, type: 'Property', label: title, data: property }], `Explique a avaliação de ${title}.`)} className="h-9 px-4 rounded border border-border bg-elevated text-xs text-text-secondary hover:text-foreground flex items-center gap-1.5">
            <FileText className="w-3.5 h-3.5" /> Explicar avaliação
          </button>
        </div>
      </div>
    </>
  );
}
