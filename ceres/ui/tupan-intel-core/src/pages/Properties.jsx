import React, { useDeferredValue, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Search, Sparkles, X, ExternalLink, MapPin, ArrowLeftRight } from 'lucide-react';
import TopBar from '@/components/tupan/TopBar';
import { Panel, MetricRow } from '@/components/tupan/primitives';
import { useApp } from '@/lib/AppContext';
import { formatBRL, formatM2, formatPct, classBadge, heatColor } from '@/lib/format';
import { propertyTypeLabel, statusLabel, valuationLabel } from '@/lib/labels';
import { cn } from '@/lib/utils';
import { apiErrorMessage } from '@/api/client';
import { getProperties, PROPERTY_KIND_OPTIONS, searchProperties } from '@/api/properties';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import {
  TableProvider,
  TableHeader,
  TableHeaderGroup,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  TableColumnHeader,
} from '@/components/kibo-ui/table';

export default function Properties() {
  const { sendToAgent } = useApp();
  const navigate = useNavigate();
  const [q, setQ] = useState('');
  const [type, setType] = useState('');
  const [selected, setSelected] = useState(null);
  const deferredQuery = useDeferredValue(q.trim());

  const { data: propertyPage, isLoading, isError, error } = useQuery({
    queryKey: ['properties', { query: deferredQuery, kind: type }],
    queryFn: ({ signal }) => (
      deferredQuery
        ? searchProperties({ query: deferredQuery, kind: type || undefined, signal })
        : getProperties({ kind: type || undefined, signal })
    ),
    placeholderData: (previousData) => previousData,
  });

  const rows = propertyPage?.items || [];

  const columns = useMemo(
    () => [
      {
        accessorKey: 'title',
        header: ({ column }) => <TableColumnHeader column={column} title="Imóvel" />,
        cell: ({ row }) => (
          <div className="flex flex-col">
            <span className="font-medium text-foreground">{row.original.title}</span>
            <span className="text-[10px] text-text-muted">{row.original.address}</span>
          </div>
        ),
      },
      {
        accessorKey: 'neighborhood',
        header: ({ column }) => <TableColumnHeader column={column} title="Bairro" />,
        cell: ({ row }) => <span className="text-text-secondary">{row.original.neighborhood}</span>,
      },
      {
        accessorKey: 'property_type',
        header: ({ column }) => <TableColumnHeader column={column} title="Tipo" />,
        cell: ({ row }) => <span className="text-text-secondary">{propertyTypeLabel(row.original.property_type)}</span>,
      },
      {
        accessorKey: 'price',
        header: ({ column }) => <TableColumnHeader column={column} title="Preço" />,
        cell: ({ row }) => <span className="tnum text-foreground">{formatBRL(row.original.price)}</span>,
      },
      {
        accessorKey: 'price_per_m2',
        header: ({ column }) => <TableColumnHeader column={column} title="Preço/m²" />,
        cell: ({ row }) => <span className="tnum text-text-secondary">{formatM2(row.original.price_per_m2)}</span>,
      },
      {
        accessorKey: 'suggested_price',
        header: ({ column }) => <TableColumnHeader column={column} title="AVM" />,
        cell: ({ row }) => <span className="tnum text-brand">{formatBRL(row.original.suggested_price)}</span>,
      },
      {
        accessorKey: 'price_deviation',
        header: ({ column }) => <TableColumnHeader column={column} title="Desvio" />,
        cell: ({ row }) => (
          <span className={cn('tnum', row.original.price_deviation > 5 ? 'text-negative' : row.original.price_deviation < -5 ? 'text-positive' : 'text-text-secondary')}>
            {formatPct(row.original.price_deviation)}
          </span>
        ),
      },
      {
        accessorKey: 'days_on_market',
        header: ({ column }) => <TableColumnHeader column={column} title="DOM" />,
        cell: ({ row }) => <span className="tnum text-text-secondary">{row.original.days_on_market == null ? '—' : `${row.original.days_on_market}d`}</span>,
      },
      {
        accessorKey: 'market_heat',
        header: ({ column }) => <TableColumnHeader column={column} title="Aquecimento" />,
        cell: ({ row }) => row.original.market_heat == null
          ? <span className="tnum text-text-muted">—</span>
          : <span className="tnum" style={{ color: heatColor(row.original.market_heat) }}>{row.original.market_heat}</span>,
      },
      {
        accessorKey: 'liquidity_score',
        header: ({ column }) => <TableColumnHeader column={column} title="Liquidez" />,
        cell: ({ row }) => <span className="tnum text-text-secondary">{row.original.liquidity_score ?? '—'}</span>,
      },
      {
        accessorKey: 'status',
        header: ({ column }) => <TableColumnHeader column={column} title="Status" />,
        cell: ({ row }) => (
          <span className={cn('text-[10px] px-1.5 py-0.5 rounded border', row.original.status === 'Active' ? 'bg-positive/10 text-positive border-positive/20' : 'bg-muted text-muted-foreground border-border')}>
            {statusLabel(row.original.status)}
          </span>
        ),
      },
    ],
    []
  );

  const sel = selected ? rows.find((p) => p.id === selected.id) : null;

  return (
    <>
      <TopBar title="Imóveis" subtitle={isLoading ? 'Carregando anúncios…' : `${propertyPage?.page?.total ?? rows.length} anúncios · Tabela de inteligência`} />
      <div className="flex-1 flex min-h-0">
        <div className="flex-1 overflow-y-auto p-5">
          <Panel className="overflow-hidden">
            <div className="flex items-center gap-2 p-3 border-b border-border flex-wrap">
              <div className="flex items-center gap-1.5 h-8 px-3 rounded-full border border-border/70 bg-card/70 backdrop-blur-sm flex-1 min-w-[200px] focus-within:border-brand/40 transition-colors">
                <Search className="w-3.5 h-3.5 text-text-muted" />
                <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Buscar imóveis, bairros, endereços…" className="bg-transparent outline-none text-xs font-mono tracking-wide text-text-secondary w-full" />
              </div>
              <Select value={type || 'all'} onValueChange={(v) => setType(v === 'all' ? '' : v)}>
                <SelectTrigger className="h-8 w-auto min-w-[120px]"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Todos os tipos</SelectItem>
                  {PROPERTY_KIND_OPTIONS.map((t) => <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>)}
                </SelectContent>
              </Select>
              <Select value="unavailable" disabled>
                <SelectTrigger className="h-8 w-auto min-w-[120px]"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="unavailable">Status indisponível</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="overflow-x-auto">
              {isLoading && <div className="py-10 text-center text-xs text-text-muted">Carregando imóveis…</div>}
              {isError && <div role="alert" className="m-3 rounded border border-negative/30 bg-negative/10 p-3 text-xs text-negative">{apiErrorMessage(error)}</div>}
              {!isLoading && !isError && <>
                <TableProvider columns={columns} data={rows} className="w-full text-xs">
                  <TableHeader>
                    {({ headerGroup }) => (
                      <TableHeaderGroup headerGroup={headerGroup} key={headerGroup.id}>
                        {({ header }) => <TableHead header={header} key={header.id} className="text-text-muted" />}
                      </TableHeaderGroup>
                    )}
                  </TableHeader>
                  <TableBody>
                    {({ row }) => (
                      <TableRow
                        key={row.id}
                        row={row}
                        onClick={() => setSelected(row.original)}
                        className={cn('cursor-pointer hover:bg-elevated/50 transition-colors', selected?.id === row.original.id && 'bg-brand/5')}
                      >
                        {({ cell }) => <TableCell cell={cell} key={cell.id} className="whitespace-nowrap" />}
                      </TableRow>
                    )}
                  </TableBody>
                </TableProvider>
                {rows.length === 0 && <div className="py-10 text-center text-xs text-text-muted">Nenhum imóvel corresponde aos seus filtros.</div>}
              </>}
            </div>
          </Panel>
        </div>

        {sel && (
          <div className="w-[340px] shrink-0 border-l border-border bg-surface flex flex-col overflow-y-auto">
            <div className="flex items-center justify-between px-4 h-11 border-b border-border sticky top-0 bg-surface z-10">
              <span className="text-sm font-semibold text-foreground truncate">{sel.title}</span>
              <button onClick={() => setSelected(null)} className="text-text-muted hover:text-foreground"><X className="w-4 h-4" /></button>
            </div>
            <div className="p-4 space-y-4">
              <div className="flex items-center gap-1.5 text-xs text-text-muted"><MapPin className="w-3 h-3" />{sel.neighborhood}, {sel.city}</div>
              <div className="grid grid-cols-2 gap-2">
                <div className="rounded border border-border bg-elevated/50 p-2.5">
                  <div className="text-[10px] uppercase text-text-muted">Preço de pedido</div>
                  <div className="text-base font-semibold tnum text-foreground">{formatBRL(sel.price)}</div>
                  <div className="text-[10px] text-text-muted">{formatM2(sel.price_per_m2)}/m²</div>
                </div>
                <div className="rounded border border-border bg-elevated/50 p-2.5">
                  <div className="text-[10px] uppercase text-text-muted">AVM sugerido</div>
                  <div className="text-base font-semibold tnum text-brand">{formatBRL(sel.suggested_price)}</div>
                  <div className={cn('text-[10px] font-medium', sel.price_deviation > 5 ? 'text-negative' : sel.price_deviation < -5 ? 'text-positive' : 'text-text-secondary')}>{formatPct(sel.price_deviation)} desvio</div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={cn('text-[10px] px-2 py-0.5 rounded border', classBadge(sel.valuation_class))}>{valuationLabel(sel.valuation_class)}</span>
                <span className="text-[10px] text-text-muted">Confiança indisponível</span>
                <span className="text-[10px] text-text-muted">· comparáveis indisponíveis</span>
              </div>
              <Panel className="p-3">
                <div className="text-[10px] uppercase tracking-wide text-text-muted mb-2">Mercado</div>
                <MetricRow label="Aquecimento de mercado" value="—" />
                <MetricRow label="DOM do imóvel" value={sel.days_on_market == null ? '—' : `${sel.days_on_market}d`} />
                <MetricRow label="Crescimento esperado" value={sel.expected_growth_pct == null ? '—' : <span className="text-positive">{formatPct(sel.expected_growth_pct)}</span>} />
                <MetricRow label="Liquidez" value="—" />
              </Panel>
              <div className="space-y-2">
                <button onClick={() => navigate(`/properties/${sel.id}`)} className="w-full h-9 rounded border border-border bg-elevated text-xs text-text-secondary hover:text-foreground flex items-center justify-center gap-1.5">
                  <ExternalLink className="w-3.5 h-3.5" /> Ver inteligência completa
                </button>
                <button onClick={() => navigate(`/compare?a=${sel.id}`)} className="w-full h-9 rounded border border-border bg-elevated text-xs text-text-secondary hover:text-foreground flex items-center justify-center gap-1.5">
                  <ArrowLeftRight className="w-3.5 h-3.5" /> Comparar com outro imóvel
                </button>
                <button onClick={() => sendToAgent([{ id: `prop-${sel.id}`, type: 'Property', label: sel.title, data: sel }], `Analise ${sel.title} em ${sel.neighborhood}.`)} className="w-full h-9 rounded bg-brand text-brand-foreground text-xs font-medium hover:bg-brand/90 flex items-center justify-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5" /> Analisar com Ceres
                </button>
                <button onClick={() => sendToAgent([{ id: `prop-${sel.id}`, type: 'Property', label: sel.title, data: sel }], `Explique a avaliação de ${sel.title}.`)} className="w-full h-9 rounded border border-border bg-elevated text-xs text-text-secondary hover:text-foreground flex items-center justify-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-brand" /> Explicar avaliação
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
