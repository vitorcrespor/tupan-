import React, { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import TopBar from '@/components/tupan/TopBar';
import FiltersPanel from '@/components/tupan/FiltersPanel';
import RegionPanel from '@/components/tupan/RegionPanel';
import Map3D from '@/components/tupan/Map3D';
import MapControls from '@/components/tupan/MapControls';
import { useApp } from '@/lib/AppContext';
import { formatM2, formatNumber, formatBRL, heatColor, heatLabel } from '@/lib/format';
import { apiErrorMessage } from '@/api/client';
import { getMarketCells, periodToDays } from '@/api/market';

export default function MarketMap() {
  const { selectedRegion, setSelectedRegion, filters, timePeriod } = useApp();
  const [tilt, setTilt] = useState(55);
  const [elevation, setElevation] = useState(1800);
  const [hovered, setHovered] = useState(null);

  const marketFilters = useMemo(() => ({
    city: filters.city || undefined,
    neighborhood: filters.neighborhood || undefined,
    h3Resolution: filters.h3Resolution || 9,
    liquidityHorizonDays: periodToDays(timePeriod),
  }), [filters.city, filters.h3Resolution, filters.neighborhood, timePeriod]);

  // H3 indexes identify a cell only within a chosen resolution. Do not retain
  // an incompatible side-panel selection when the published grid changes.
  useEffect(() => {
    setSelectedRegion(null);
  }, [marketFilters.h3Resolution, setSelectedRegion]);

  const {
    data: marketData,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['market-cells', marketFilters],
    queryFn: ({ signal }) => getMarketCells({ ...marketFilters, signal }),
  });

  const cells = marketData?.cells || [];
  const selectedCell = selectedRegion?.h3_index
    ? cells.find((cell) => cell.h3_index === selectedRegion.h3_index) || null
    : null;

  return (
    <>
      <TopBar title="Mapa de mercado" subtitle="Inteligência geográfica · Células H3">
        <FiltersPanel publishedOnly />
      </TopBar>
      <div className="flex-1 flex min-h-0">
        <div className="flex-1 relative isolate bg-background">
          {isLoading ? (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-8 h-8 border-4 border-border border-t-brand rounded-full animate-spin" />
            </div>
          ) : isError ? (
            <div role="alert" className="absolute inset-0 flex items-center justify-center px-8">
              <div className="aero-glass rounded-2xl p-6 max-w-sm text-center">
                <p className="text-sm text-foreground font-medium mb-1">Dados de mercado indisponíveis</p>
                <p className="text-xs text-text-secondary">{apiErrorMessage(error)}</p>
              </div>
            </div>
          ) : cells.length === 0 ? (
            <div className="absolute inset-0 flex items-center justify-center px-8">
              <div className="aero-glass rounded-2xl p-6 max-w-sm text-center">
                <p className="text-sm text-foreground font-medium mb-1">Nenhuma célula H3 encontrada</p>
                <p className="text-xs text-text-secondary">Ajuste os filtros para consultar outro recorte de mercado.</p>
              </div>
            </div>
          ) : (
            <Map3D
              cells={cells}
              tilt={tilt}
              elevation={elevation}
              onSelect={setSelectedRegion}
              onHover={setHovered}
            />
          )}

          {!isLoading && !isError && cells.length > 0 && (
            <>
              <div className="absolute bottom-4 left-4 z-[1100]">
                <span className="text-xs text-text-secondary">{cells.some(cell => cell.dataset_kind === 'transactions') ? 'Transações ITBI · cobertura parcial geocodificada' : 'Células publicadas · aquecimento indisponível'}</span>
              </div>
              <div className="absolute bottom-4 right-4 z-[1100]">
                <MapControls tilt={tilt} setTilt={setTilt} elevation={elevation} setElevation={setElevation} />
              </div>
              <div className="absolute top-4 right-4 z-[1100] aero-glass rounded-full px-4 py-2 text-[11px] text-text-secondary pointer-events-none">
                {cells.length} células H3 {marketFilters.h3Resolution} · publicação {cells[0]?.calculated_at?.slice(0, 10) || '—'}
              </div>
              {hovered && (
                <div className="absolute top-4 left-4 z-[1100] aero-glass aero-gloss rounded-2xl px-4 py-3 pointer-events-none min-w-[180px]">
                  <div className="text-sm font-semibold text-foreground">{hovered.label}</div>
                  <div className="text-[10px] text-text-muted mb-1.5">H3 {hovered.h3_index}</div>
                  {hovered.dataset_kind === 'transactions' ? <>
                    <div className="text-xs text-text-secondary">{formatNumber(hovered.transaction_count)} transações históricas</div>
                    <div className="text-xs text-text-secondary">Valor médio {formatBRL(hovered.average_transaction_price)}</div>
                    <div className="text-[11px] text-text-muted">{hovered.period_start} a {hovered.period_end} · amostra</div>
                  </> : <><div className="text-xs" style={{ color: heatColor(hovered.market_heat ?? 0) }}>
                    Aquecimento {hovered.market_heat == null ? '—' : `${hovered.market_heat.toFixed(0)}/100`} · {hovered.market_heat == null ? 'Indisponível' : heatLabel(hovered.market_heat)}
                  </div>
                  <div className="text-[11px] text-text-secondary">{formatM2(hovered.average_price_m2)}/m²</div>
                  <div className="text-[11px] text-text-muted">
                    {formatNumber(hovered.inventory)} anúncios · DOM {hovered.average_dom_days == null ? '—' : `${Math.round(hovered.average_dom_days)}d`}
                  </div>
                  <div className="text-[11px] text-text-secondary">Liquidez {hovered.liquidity == null ? '—' : `${Math.round(hovered.liquidity)}/100`} · {hovered.liquidity_details?.horizon_days || '—'}d</div>
                  </>}
                </div>
              )}
            </>
          )}
        </div>
        {selectedCell && <RegionPanel region={selectedCell} onClose={() => setSelectedRegion(null)} />}
      </div>
    </>
  );
}
