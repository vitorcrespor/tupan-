import React from 'react';
import { MapPin, Sparkles, X } from 'lucide-react';
import { useApp } from '@/lib/AppContext';
import { ContextTag, MetricRow, Panel, ScoreBar, SectionTitle } from './primitives';
import { formatM2, formatNumber, formatPct, heatColor, heatLabel } from '@/lib/format';

const scoreText = (score) => score == null ? '—' : `${Math.round(score)}/100`;
const velocityText = (velocity) => velocity == null ? '—' : `${velocity.toFixed(2)}/mês`;

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
        <div className="grid grid-cols-2 gap-2">
          <div className="rounded border border-border bg-elevated/50 p-2.5">
            <div className="text-[10px] uppercase text-text-muted">Aquecimento de mercado</div>
            <div className="text-lg font-semibold tnum" style={{ color: heatColor(region.market_heat ?? 0) }}>{scoreText(region.market_heat)}</div>
            <div className="text-[10px]" style={{ color: heatColor(region.market_heat ?? 0) }}>{region.market_heat == null ? 'Indisponível' : heatLabel(region.market_heat)}</div>
          </div>
          <div className="rounded border border-border bg-elevated/50 p-2.5">
            <div className="text-[10px] uppercase text-text-muted">Demanda</div>
            <div className="text-lg font-semibold tnum text-foreground">{scoreText(region.demand_score)}</div>
            <div className="text-[10px] text-text-muted">{formatNumber(region.inventory)} anúncios</div>
          </div>
        </div>

        <Panel className="p-3">
          <SectionTitle right={<ContextTag type="DATA">H3</ContextTag>}>Dados de mercado</SectionTitle>
          <MetricRow label="Preço/m²" value={formatM2(region.average_price_m2)} />
          <MetricRow label="Crescimento de preço" value={region.price_growth_pct == null ? '—' : <span className="text-positive">{formatPct(region.price_growth_pct)}</span>} />
          <MetricRow label="DOM médio" value={region.average_dom_days == null ? '—' : `${Math.round(region.average_dom_days)} dias`} />
          <MetricRow label="Inventário" value={formatNumber(region.inventory)} />
          <MetricRow label="Velocidade de vendas" value={velocityText(region.sales_velocity)} />
        </Panel>

        <Panel className="p-3">
          <SectionTitle right={<ContextTag type="MODEL">Demanda</ContextTag>}>Escore de demanda</SectionTitle>
          {region.market_heat == null ? <MetricRow label="Aquecimento de mercado" value="—" /> : <ScoreBar label="Aquecimento de mercado" value={region.market_heat} />}
          <div className="h-2" />
          {region.demand_score == null ? <MetricRow label="Demanda espacial" value="—" /> : <ScoreBar label="Demanda espacial" value={region.demand_score} />}
          <div className="h-2" />
          <MetricRow label="Liquidez" value="Indisponível no contrato" />
        </Panel>

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
