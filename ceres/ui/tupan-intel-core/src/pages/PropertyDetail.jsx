import React, { useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ResponsiveContainer, Radar, RadarChart, PolarAngleAxis, PolarGrid, PolarRadiusAxis } from 'recharts';
import { ArrowLeft, FileText, MapPin, Sparkles } from 'lucide-react';
import TopBar from '@/components/tupan/TopBar';
import EstimateProvenance from '@/components/tupan/EstimateProvenance';
import { ContextTag, MetricRow, Panel, ScoreBar, SectionTitle } from '@/components/tupan/primitives';
import { useApp } from '@/lib/AppContext';
import { classColor, formatBRL, formatM2, formatPct } from '@/lib/format';
import { apiErrorMessage } from '@/api/client';
import { getEstateAnalysis } from '@/api/analysis';
import { estateToView } from '@/api/properties';
import { statusLabel, valuationLabel } from '@/lib/labels';
import { liquidityHorizonDays as liquidityHorizonForPeriod, timePeriodLabel } from '@/lib/tupanData';
import { CHART } from '@/lib/chartTheme';
import { AsyncEmpty } from '@/components/tupan/AsyncState';

function valueOrDash(value) {
  return value == null ? '—' : value;
}

export default function PropertyDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { sendToAgent, timePeriod } = useApp();
  const liquidityHorizonDays = liquidityHorizonForPeriod(timePeriod);

  const analysisQuery = useQuery({
    queryKey: ['estate-analysis', id, liquidityHorizonDays],
    queryFn: ({ signal }) => getEstateAnalysis(id, { signal, liquidity_horizon_days: liquidityHorizonDays }),
    enabled: Boolean(id), retry: false,
  });
  const analysis = analysisQuery.data;
  const property = analysis ? estateToView(analysis.estate) : null;
  const valuation = analysis?.valuation;
  const isPropertyLoading = analysisQuery.isLoading;
  const isPropertyError = analysisQuery.isError;
  const propertyError = analysisQuery.error;
  const isValuationLoading = analysisQuery.isLoading;
  const isValuationError = analysisQuery.isError;
  const valuationError = analysisQuery.error;
  const warnings = analysis?.timing.components.filter(component => component.state !== 'success') || [];
  const stats = analysis?.local_statistics;
  const location = analysis?.location_metrics;

  const profile = useMemo(() => [
    { name: 'Luxo', value: property?.profile_scores?.luxury ?? null },
    { name: 'Lazer', value: property?.profile_scores?.leisure ?? null },
    { name: 'Localização', value: property?.profile_scores?.location ?? null },
    { name: 'Alavancagem', value: property?.profile_scores?.leverage ?? null },
  ], [property]);

  const valuationDeviationPct = valuation?.difference_percent ?? null;
  const valuationDifference = valuation?.difference ?? null;

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
      <div className="workspace-content workspace-stack flex-1 overflow-y-auto">
        <div className="property-analysis-layout">
          <section className="property-summary">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-lg font-semibold text-foreground">{title}</h2>
                {property.source_name === 'ceres_demo_academic_v1' && <p className="mt-2 text-xs text-text-secondary">{property.summary}</p>}
                <div className="flex items-center gap-1.5 text-xs text-text-muted mt-1"><MapPin className="w-3 h-3" />{address}</div>
              </div>

            </div>
            <div className="grid grid-cols-3 gap-4 mt-6">
              {[
                { l: 'Quartos', v: property.bedrooms }, { l: 'Banhos', v: property.bathrooms }, { l: 'Vagas', v: property.parking_spaces },
                { l: 'Área', v: property.area_m2 == null ? null : `${property.area_m2}m²` }, { l: 'Idade', v: property.property_age == null ? null : `${property.property_age}a` }, { l: 'Status', v: statusLabel(property.status) },
              ].map((item) => (
                <div key={item.l}><div className="text-[10px] uppercase text-text-muted">{item.l}</div><div className="text-sm font-medium text-foreground">{valueOrDash(item.v)}</div></div>
              ))}
            </div>
          </section>
          <section className="property-valuation">
            <SectionTitle right={<span className="text-xs text-text-secondary">{valuationStatus}</span>}>Avaliação</SectionTitle>
            <p className="text-xs text-text-secondary">Valor estimado · AVM</p>
            <div className="property-valuation__value">{isValuationLoading ? 'Calculando…' : formatBRL(valuation?.estimated_price)}</div>
            <div className="grid gap-x-6 sm:grid-cols-2">
              <MetricRow label="Preço de pedido" value={formatBRL(valuation ? valuation.listed_price : property.price)} />
              <MetricRow label="Preço/m² listado" value={formatM2(valuation ? valuation.price_per_m2 : property.price_per_m2)} />
            </div>
            {isValuationLoading && <div className="py-4 text-xs text-text-muted">Executando inferência do modelo…</div>}
            {isValuationError && <div role="alert" className="my-3 rounded border border-negative/30 bg-negative/10 p-2 text-xs text-negative">{apiErrorMessage(valuationError)}</div>}
            {!isValuationLoading && !isValuationError && valuation && <>
              <MetricRow label="Diferença" value={formatBRL(valuationDifference)} />
              <MetricRow label="Classificação" value={<span className={classColor(valuation.valuation_class)}>{valuationLabel(valuation.valuation_class || 'Unavailable')}</span>} />
              <MetricRow label="Desvio" value={<span className={classColor(valuation.valuation_class)}>{formatPct(valuationDeviationPct)}</span>} />
              <MetricRow label="Preço/m² estimado" value={formatM2(valuation.estimated_price_per_m2)} />
              <MetricRow
                label={valuation.interval_level == null ? 'Faixa estimada' : `Faixa estimada (${Math.round(valuation.interval_level * 100)}%)`}
                value={valuation.lower_bound == null || valuation.upper_bound == null ? '—' : `${formatBRL(valuation.lower_bound)} — ${formatBRL(valuation.upper_bound)}`}
              />
            </>}
            <MetricRow label="Última venda" value={formatBRL(property.last_sale_price)} />
            {analysis?.data_quality && <details className="mt-3 text-xs text-text-secondary">
              <summary>Completude {analysis.data_quality.completeness.toLocaleString('pt-BR')}% · qualidade {analysis.data_quality.quality.toLocaleString('pt-BR')}/100</summary>
              <p className="mt-2">Indicadores da política {analysis.data_quality.policy_version}; não são probabilidade de acerto da AVM.</p>
              {analysis.data_quality.missing_fields.length > 0 && <p>Campos ausentes: {analysis.data_quality.missing_fields.join(', ')}</p>}
              {[...analysis.data_quality.critical_reasons, ...analysis.data_quality.warnings].map(reason => <p key={reason}>{reason}</p>)}
            </details>}
            {analysis?.avm_diagnostics && <details className="mt-3 text-xs text-text-secondary">
              <summary>Sobre o modelo</summary>
              <p>{analysis.avm_diagnostics.model_type} · contrato {analysis.avm_diagnostics.schema_version ?? '—'}</p>
              <p>Alvo: {analysis.avm_diagnostics.target ?? 'Não registrado'} · {analysis.avm_diagnostics.training_rows ?? '—'} amostras de treinamento.</p>
              {analysis.avm_diagnostics.uncertainty_status === 'calibrated'
                ? <>
                  <p>Intervalo calibrado por {analysis.avm_diagnostics.uncertainty_method || 'conformal'}.</p>
                  <p>{analysis.avm_diagnostics.calibration_sample_count ?? '—'} observações de calibração · cobertura fora do tempo {analysis.avm_diagnostics.out_of_time_coverage == null ? '—' : `${(analysis.avm_diagnostics.out_of_time_coverage * 100).toLocaleString('pt-BR', {maximumFractionDigits: 1})}%`}.</p>
                  {analysis.avm_diagnostics.out_of_time_median_width_pct != null && <p>Largura mediana fora do tempo: {analysis.avm_diagnostics.out_of_time_median_width_pct.toLocaleString('pt-BR', {maximumFractionDigits: 1})}%.</p>}
                </>
                : <p>Intervalo calibrado indisponível neste modelo em produção.</p>}
              {analysis.avm_diagnostics.model_version && <p>Versão do modelo: {analysis.avm_diagnostics.model_version}.</p>}
            </details>}
            {property.last_sale_date && <p className="text-xs text-text-muted">Venda registrada em {property.last_sale_date}</p>}
            {warnings.map(warning => <p key={warning.name} role="status" className="my-2 text-xs text-warning">{warning.message || `${warning.name}: informação indisponível.`}</p>)}
            {!isValuationLoading && !isValuationError && !valuation && <div className="py-4 text-xs text-text-muted">Avaliação indisponível.</div>}
            <button onClick={() => sendToAgent([{ id: `prop-${property.id}`, type: 'Property', label: title, data: property }], `Explique a avaliação de ${title}.`)} className="mt-4 px-4 h-9 rounded bg-brand text-brand-foreground text-xs font-medium hover:bg-brand/90 flex items-center justify-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5" /> Explicar avaliação
            </button>
          </section>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Panel className="p-4">
            <SectionTitle right={<ContextTag type="DATA">Mercado</ContextTag>}>Contexto de mercado</SectionTitle>
            <MetricRow label="DOM do imóvel" value={property.days_on_market == null ? '—' : `${property.days_on_market} dias`} />
            <MetricRow label={`Liquidez · ${timePeriodLabel(timePeriod)}`} value={property.liquidity_score == null ? '—' : `${property.liquidity_score}/100`} />
            <MetricRow label="DOM médio dos comparáveis" value={stats?.average_days_on_market == null ? '—' : `${Math.round(stats.average_days_on_market)} dias`} />
            <MetricRow label="Referência de pedido/m² (mediana)" value={formatM2(stats?.median_price_per_m2)} />
            <MetricRow label="Referência de pedido (média)" value={formatBRL(stats?.average_asking_price)} />
            <MetricRow label="Referência de pedido (mediana)" value={formatBRL(stats?.median_asking_price)} />
            <MetricRow label="Referência de pedido/m² (média)" value={formatM2(stats?.average_price_per_m2)} />
            <MetricRow label="Inventário da célula" value={location?.metrics.inventory ?? '—'} />
            <MetricRow label="Aquecimento da célula" value={property.market_heat == null ? '—' : `${Math.round(property.market_heat)}/100`} />
            {location?.metrics.transaction_count != null && <MetricRow label="Transações observadas na célula" value={location.metrics.transaction_count} />}
            {location?.calculated_at && <p className="text-xs text-text-muted">Agregação publicada em {location.calculated_at.slice(0, 10)}</p>}
            {location && <details className="mt-2 text-xs text-text-muted">
              <summary>Proveniência da agregação geográfica</summary>
              <p>{location.scope === 'platform' ? 'Mercado global publicado' : 'Agregação da organização'} · H3 {location.h3_resolution ?? '—'} · {location.city || 'escopo amplo'}{location.area ? ` · ${location.area}` : ''}.</p>
              <p>Período: {location.period_start || '—'} a {location.period_end || '—'} · versão de entrada: {location.input_version || 'não informada'}.</p>
              {location.metrics.partial_coverage === true && <p>Cobertura parcial: alguns registros do período não tinham os atributos necessários para este agregado.</p>}
            </details>}
            {analysis?.market_context.map((item, index) => <div key={`${item.metric}-${index}`} className="mt-2 text-xs text-text-secondary">
              <MetricRow label={item.metric} value={`${item.value.toLocaleString('pt-BR')} ${item.unit || ''}`} />
              <span>{item.source_name} · observação {item.observed_on} · {item.scope === 'platform' ? 'mercado global' : 'organização'}</span>
            </div>)}
            <p className="mt-3 text-xs text-text-muted">As referências acima são dados determinísticos, não interpretação da IA. {valuation?.uncertainty_status === 'calibrated' ? 'A faixa exibida usa calibração fora do tempo.' : 'Faixa calibrada disponível somente após promoção de um modelo validado.'}</p>
          </Panel>
          <Panel className="p-4">
            <SectionTitle right={<ContextTag type="MODEL">Ceres 4L</ContextTag>}>Perfil do imóvel</SectionTitle>
            {profile.some((metric) => metric.value != null) ? <ResponsiveContainer width="100%" height={180}>
              <RadarChart data={profile}>
                <PolarGrid stroke={CHART.grid} strokeDasharray="3 3" />
                <PolarAngleAxis dataKey="name" tick={{ fill: CHART.axis, fontSize: 11 }} />
                <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fill: CHART.axis, fontSize: 10 }} stroke={CHART.grid} strokeDasharray="3 3" />
                <Radar dataKey="value" stroke={CHART.aqua} fill={CHART.aqua} fillOpacity={0.18} />
              </RadarChart>
            </ResponsiveContainer> : <AsyncEmpty className="py-6">Perfil ainda não disponível para este imóvel.</AsyncEmpty>}
            <div className="space-y-2 mt-2">
              {profile.map((metric) => metric.value == null
                ? <MetricRow key={metric.name} label={metric.name} value="—" />
                : <ScoreBar key={metric.name} label={metric.name} value={metric.value} />
              )}
            </div>
          </Panel>
          <Panel className="p-4 md:col-span-2">
            <SectionTitle>Imóveis comparáveis</SectionTitle>
            <p className="mb-3 text-xs text-text-muted">{stats ? `${analysis.comparables.length} exibidos · ${stats.comparable_count} elegíveis · ${analysis.comparable_metadata?.scored_count ?? 0} pontuados` : 'Suporte indisponível'} · imóveis ativos da organização, do mesmo tipo; raio de 2,5 km quando há coordenadas, senão cidade/bairro.</p>
            {analysis.comparables.length ? <div className="overflow-x-auto"><table className="ceres-table w-full">
              <thead><tr>{['Imóvel', 'Semelhança', 'Pedido', 'Estimativa registrada', 'Pedido/m²', 'Configuração', 'DOM', 'Distância'].map(label => <th key={label} scope="col">{label}</th>)}</tr></thead>
              <tbody>{analysis.comparables.map(peer => <tr key={peer.id}>
                <td><button className="text-brand text-left" onClick={() => navigate(`/properties/${encodeURIComponent(peer.id)}`)}>{peer.title || 'Imóvel sem título'}</button><small className="block text-text-muted">{[peer.area, peer.city].filter(Boolean).join(', ') || peer.property_type || 'Local não informado'}</small></td>
                <td title={peer.similarity_feature_version}>{peer.similarity_score == null ? '—' : peer.similarity_score.toLocaleString('pt-BR', { minimumFractionDigits: 3, maximumFractionDigits: 3 })}<small className="block text-text-muted">cosseno</small></td>
                <td>{formatBRL(peer.asking_price)}</td><td>{formatBRL(peer.estimated_price)}{peer.estimated_price != null && <EstimateProvenance provenance={peer.estimate_provenance} />}</td><td>{formatM2(peer.price_per_m2)}</td>
                <td>{[
                  peer.area_m2 == null ? null : `${peer.area_m2} m²`,
                  peer.rooms == null ? null : `${peer.rooms} q.`,
                  peer.bathrooms == null ? null : `${peer.bathrooms} b.`,
                  peer.parking_spaces == null ? null : `${peer.parking_spaces} v.`,
                ].filter(Boolean).join(' · ') || '—'}</td>
                <td>{peer.days_on_market == null ? '—' : `${peer.days_on_market}d`}</td>
                <td>{peer.distance_meters == null ? '—' : `${Math.round(peer.distance_meters)} m`}</td>
              </tr>)}</tbody>
            </table></div> : <div className="py-4 text-xs text-text-secondary">{warnings.some(item => item.name === 'comparables') ? 'Consulta aos comparáveis indisponível.' : 'Nenhum comparável encontrado para este recorte.'}</div>}
          </Panel>
        </div>

        <div className="flex flex-wrap gap-2">
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
