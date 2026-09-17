import React from 'react';
import { MapPin, Sparkles, X } from 'lucide-react';
import { useApp } from '@/lib/AppContext';
import { ContextTag, MetricRow, Panel, ScoreBar, SectionTitle } from './primitives';
import { formatM2, formatNumber, formatBRL, formatPct, heatColor, heatLabel } from '@/lib/format';

const scoreText = (score) => score == null ? '—' : `${Math.round(score)}/100`;
const velocityText = (velocity) => velocity == null ? '—' : `${velocity.toFixed(2)} vendas/dia`;

/** Renders one backend-calculated H3 market cell. */
export default function RegionPanel({ region, onClose }) {
  const { sendToAgent } = useApp();
  if (!region) return null;

  const title = region.neighborhood || region.label;

  return (
    <div className="w-[320px] shrink-0 border-l border-border bg-surface flex flex-col overflow-y-auto">
      <div className="flex items-center justify-between px-4 h-11 border-b border-border sticky top-0 bg-surface z-10">
        <div className="flex items-center gap-2 min-w-0">
          <MapPin className="w-4 h-4 text-brand shrink-0" />
          <div className="flex flex-col leading-tight min-w-0">
            <span className="text-sm font-semibold text-foreground truncate">{title}</span>
            <span className="text-[10px] text-text-muted truncate">{region.city || 'Cidade indisponível'} · H3 {region.h3_index}</span>
          </div>
        </div>
        <button onClick={onClose} className="text-text-muted hover:text-foreground"><X className="w-4 h-4" /></button>
      </div>
      <div className="p-4 space-y-4">
        {region.dataset_kind === 'transactions' ? <Panel className="p-3">
          <SectionTitle>Transações ITBI</SectionTitle>
          <MetricRow label="Transações observadas" value={formatNumber(region.transaction_count)} />
          {region.source_row_count != null && region.geocoded_row_count != null ? (
            <MetricRow
              label="Cobertura geocodificada da fonte"
              value={`${formatNumber(region.geocoded_row_count)} de ${formatNumber(region.source_row_count)}`}
            />
          ) : null}
          <MetricRow label="Valor médio declarado" value={formatBRL(region.average_transaction_price)} />
          <MetricRow label="Mediana declarada" value={formatBRL(region.median_transaction_price)} />
          <p className="mt-3 text-xs text-text-secondary">{region.period_start} a {region.period_end}. Amostra geocodificada da planilha acadêmica, com transferências integrais entre R$ 100 mil e R$ 3 milhões. Não representa toda a cidade.</p>
        </Panel> : <>
        <div className="grid grid-cols-2 gap-2">
          <div className="rounded border border-border bg-elevated/50 p-2.5">
            <div className="text-[10px] uppercase text-text-muted">Aquecimento de mercado</div>
            <div className="text-lg font-semibold tnum" style={{ color: heatColor(region.market_heat ?? 0) }}>{scoreText(region.market_heat)}</div>
            <div className="text-[10px]" style={{ color: heatColor(region.market_heat ?? 0) }}>{region.market_heat == null ? 'Indisponível' : heatLabel(region.market_heat)}</div>
          </div>
          <div className="rounded border border-border bg-elevated/50 p-2.5">
            <div className="text-[10px] uppercase text-text-muted">Inventário</div>
            <div className="text-lg font-semibold tnum text-foreground">{formatNumber(region.inventory)}</div>
            <div className="text-[10px] text-text-muted">anúncios ativos</div>
          </div>
        </div>

        <Panel className="p-3">
          <SectionTitle right={<ContextTag type="DATA">H3</ContextTag>}>Dados de mercado</SectionTitle>
          <MetricRow label="Preço/m²" value={formatM2(region.average_price_m2)} />
          <MetricRow label="Preço médio de anúncio" value={formatBRL(region.average_asking_price)} />
          <MetricRow label="Crescimento de preço" value={region.price_growth_pct == null ? '—' : <span className={region.price_growth_pct < 0 ? 'text-negative' : 'text-positive'}>{formatPct(region.price_growth_pct)}</span>} />
          <MetricRow label="DOM médio" value={region.average_dom_days == null ? '—' : `${Math.round(region.average_dom_days)} dias`} />
          <MetricRow label="Inventário" value={formatNumber(region.inventory)} />
          <MetricRow label="Velocidade de vendas" value={velocityText(region.sales_velocity)} />
        </Panel>

        <Panel className="p-3">
          <SectionTitle right={<ContextTag type="MODEL">Modelo</ContextTag>}>Liquidez</SectionTitle>
          {region.liquidity == null ? <MetricRow label="Liquidez" value="—" /> : <ScoreBar label="Liquidez" value={region.liquidity} />}
          <MetricRow label="Horizonte" value={region.liquidity_details?.horizon_days ? `${region.liquidity_details.horizon_days} dias` : 'Não selecionado'} />
          <MetricRow label="Suporte" value={region.liquidity_details?.observation_count == null ? 'Insuficiente' : `${formatNumber(region.liquidity_details.observation_count)} anúncios · ${formatNumber(region.liquidity_details.sale_event_count)} vendas`} />
        </Panel>
        </>}

        <button
          onClick={() => sendToAgent([{ id: `h3-${region.h3_index}`, type: 'Region', label: title, data: region }], `Analise a célula H3 ${region.h3_index} de ${title}, ${region.city || ''}.`)}
          className="w-full h-9 rounded bg-brand text-brand-foreground text-sm font-medium hover:bg-brand/90 flex items-center justify-center gap-2"
        >
          <Sparkles className="w-4 h-4" /> Analisar com Ceres
        </button>
      </div>
    </div>
  );
}
