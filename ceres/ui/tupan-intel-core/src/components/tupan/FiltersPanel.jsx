import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { X } from 'lucide-react';
import { useApp } from '@/lib/AppContext';
import { TIME_PERIODS } from '@/lib/tupanData';
import { getMarketRegions, H3_RESOLUTION_OPTIONS } from '@/api/market';
import { PROPERTY_KIND_OPTIONS } from '@/api/properties';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { Pill, PillButton } from '@/components/kibo-ui/pill';

function Field({ label, children }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-[10px] uppercase tracking-wide text-text-muted">{label}</label>
      {children}
    </div>
  );
}

export default function FiltersPanel({publishedOnly = false}) {
  const { filters, setFilters } = useApp();
  const { data: regions = [] } = useQuery({
    queryKey: ['geographic-regions', publishedOnly],
    queryFn: ({signal}) => getMarketRegions({publishedOnly, signal}),
  });

  const set = (k, v) => setFilters((f) => ({ ...f, [k]: v }));
  const active = Object.entries(filters).filter(([k, v]) => v != null && v !== '' && k !== 'period' && (!publishedOnly || ['city','neighborhood'].includes(k)));

  return (
    <div className="border-b border-border bg-surface">
      <div className="flex items-center gap-2 px-5 py-2 flex-wrap">
        <Select value={filters.city || 'all'} onValueChange={(v) => setFilters((f) => ({...f, city: v === 'all' ? null : v, neighborhood: null}))}>
          <SelectTrigger className="h-8 w-auto min-w-[120px]"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todas as cidades</SelectItem>
            {regions.map((c) => <SelectItem key={c.city} value={c.city}>{c.city}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={filters.neighborhood || 'all'} onValueChange={(v) => set('neighborhood', v === 'all' ? null : v)}>
          <SelectTrigger className="h-8 w-auto min-w-[150px]"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos os bairros</SelectItem>
            {regions.find((c) => c.city === filters.city)?.areas.map((n) => <SelectItem key={n} value={n}>{n}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select disabled={publishedOnly} value={filters.propertyType || 'all'} onValueChange={(v) => set('propertyType', v === 'all' ? null : v)}>
          <SelectTrigger className="h-8 w-auto min-w-[120px]"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Todos os tipos</SelectItem>
            {PROPERTY_KIND_OPTIONS.map((type) => <SelectItem key={type.value} value={type.value}>{type.label}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select disabled={publishedOnly} value={publishedOnly ? 'snapshot' : filters.period} onValueChange={(v) => set('period', v)}>
          <SelectTrigger className="h-8 w-auto min-w-[110px]"><SelectValue /></SelectTrigger>
          <SelectContent>
            {publishedOnly && <SelectItem value="snapshot">Publicação atual</SelectItem>}
            {TIME_PERIODS.map((p) => <SelectItem key={p.id} value={p.id}>{p.label}</SelectItem>)}
          </SelectContent>
        </Select>
        {publishedOnly && <Select value={String(filters.h3Resolution || 9)} onValueChange={(value) => set('h3Resolution', Number(value))}>
          <SelectTrigger aria-label="Resolução H3" className="h-8 w-auto min-w-[128px]"><SelectValue /></SelectTrigger>
          <SelectContent>
            {H3_RESOLUTION_OPTIONS.map((resolution) => <SelectItem key={resolution.value} value={String(resolution.value)}>{resolution.label}</SelectItem>)}
          </SelectContent>
        </Select>}
        <div className="flex items-center gap-1.5 text-xs text-text-muted">
          <span>Preço</span>
          <input disabled={publishedOnly} type="number" placeholder="Mín" value={filters.priceMin || ''} onChange={(e) => set('priceMin', e.target.value ? +e.target.value : null)} className="w-20 h-8 rounded-full border border-border/70 bg-card/70 backdrop-blur-sm px-3 text-xs font-mono text-text-secondary outline-none focus:border-brand/40" />
          <span>–</span>
          <input disabled={publishedOnly} type="number" placeholder="Máx" value={filters.priceMax || ''} onChange={(e) => set('priceMax', e.target.value ? +e.target.value : null)} className="w-20 h-8 rounded-full border border-border/70 bg-card/70 backdrop-blur-sm px-3 text-xs font-mono text-text-secondary outline-none focus:border-brand/40" />
        </div>
        <div className="flex items-center gap-1.5 text-xs text-text-muted ml-auto">
          <span>Aquec. mín</span>
          <input disabled={publishedOnly} type="range" min={0} max={100} value={filters.heatMin || 0} onChange={(e) => set('heatMin', +e.target.value)} className="w-24 accent-brand" />
          <span className="tnum w-7">{filters.heatMin || 0}</span>
        </div>
      </div>
      {active.length > 0 && (
        <div className="flex items-center gap-1.5 px-5 pb-2 flex-wrap">
          <span className="text-[10px] uppercase tracking-wide text-text-muted">Ativos:</span>
          {active.map(([k, v]) => (
            <Pill key={k} themed className="h-6 text-[10px]">
              {k}:{String(v)}
              <PillButton
                onClick={() => k === 'city' ? setFilters((f) => ({...f, city: null, neighborhood: null})) : set(k, null)}
                aria-label={`Clear ${k} filter`}
                className="size-3.5 [&_svg]:size-2.5 hover:bg-primary/15"
              >
                <X className="size-2.5" />
              </PillButton>
            </Pill>
          ))}
          <button onClick={() => setFilters({ city: null, neighborhood: null, propertyType: null, priceMin: null, priceMax: null, heatMin: null, period: '90d', h3Resolution: 9 })} className="text-[10px] text-text-muted hover:text-foreground underline">Limpar tudo</button>
        </div>
      )}
    </div>
  );
}
