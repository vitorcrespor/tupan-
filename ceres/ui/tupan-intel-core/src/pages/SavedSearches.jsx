import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { appClient } from '@/demo/localAppClient';
import TopBar from '@/components/tupan/TopBar';
import { Panel, SectionTitle } from '@/components/tupan/primitives';
import { useTupanData } from '@/lib/useTupanData';
import { CITIES, PROPERTY_TYPES } from '@/lib/tupanData';
import { formatBRLCompact } from '@/lib/format';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import { Trash2, Plus, Loader2, ChevronDown, ChevronRight, Building2 } from 'lucide-react';
import { AsyncError, AsyncLoading } from '@/components/tupan/AsyncState';

const STATUSES = ['Active', 'Sold', 'Off Market'];
const NEIGHBORHOODS = CITIES[0].neighborhoods;

export default function SavedSearches() {
  const { properties, propertiesStatus, propertiesError } = useTupanData();
  const navigate = useNavigate();
  const [searches, setSearches] = useState([]);
  const [loadingSearches, setLoadingSearches] = useState(true);
  const [expanded, setExpanded] = useState(null);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ name: '', neighborhood: '', property_type: '', status: '', minPrice: '', maxPrice: '' });

  const load = async () => {
    try {
      const res = await appClient.entities.SavedSearch.list('-created_date', 100);
      setSearches(res || []);
    } catch (e) {
      setSearches([]);
    } finally {
      setLoadingSearches(false);
    }
  };

  useEffect(() => { load(); }, []);

  const matchFor = (filters) => {
    if (!filters) return [];
    return properties.filter((p) => {
      if (filters.neighborhood && p.neighborhood !== filters.neighborhood) return false;
      if (filters.property_type && p.property_type !== filters.property_type) return false;
      if (filters.status && p.status !== filters.status) return false;
      if (filters.minPrice != null && p.price < filters.minPrice) return false;
      if (filters.maxPrice != null && p.price > filters.maxPrice) return false;
      return true;
    });
  };

  const save = async (e) => {
    e.preventDefault();
    if (!form.name.trim() || saving) return;
    setSaving(true);
    try {
      const filters = {
        neighborhood: form.neighborhood || '',
        property_type: form.property_type || '',
        status: form.status || '',
        minPrice: form.minPrice ? Number(form.minPrice) : null,
        maxPrice: form.maxPrice ? Number(form.maxPrice) : null,
      };
      await appClient.entities.SavedSearch.create({ name: form.name.trim(), filters });
      setForm({ name: '', neighborhood: '', property_type: '', status: '', minPrice: '', maxPrice: '' });
      load();
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id) => {
    try { await appClient.entities.SavedSearch.delete(id); load(); } catch (e) {}
  };

  const chips = (f) => {
    if (!f) return [];
    const out = [];
    if (f.neighborhood) out.push(f.neighborhood);
    if (f.property_type) out.push(f.property_type);
    if (f.status) out.push(f.status);
    if (f.minPrice != null) out.push('≥ ' + formatBRLCompact(f.minPrice));
    if (f.maxPrice != null) out.push('≤ ' + formatBRLCompact(f.maxPrice));
    return out;
  };

  return (
    <>
      <TopBar title="Buscas Salvas" subtitle="Workspaces recorrentes para acesso rápido a tendências" />
      <div className="flex-1 overflow-y-auto p-5">
        <div className="grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-4">
          <Panel className="p-4 h-fit">
            <SectionTitle>Nova busca salva</SectionTitle>
            <form onSubmit={save} className="space-y-3">
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Nome (ex: Apartamentos Pinheiros)" className="w-full h-9 rounded-xl border border-border bg-surface px-3 text-sm text-foreground outline-none focus:border-brand/40" />
              <div className="grid grid-cols-2 gap-2">
                <Select value={form.neighborhood} onValueChange={(v) => setForm({ ...form, neighborhood: v })}>
                  <SelectTrigger className="h-9"><SelectValue placeholder="Bairro" /></SelectTrigger>
                  <SelectContent>{NEIGHBORHOODS.map((n) => <SelectItem key={n} value={n}>{n}</SelectItem>)}</SelectContent>
                </Select>
                <Select value={form.property_type} onValueChange={(v) => setForm({ ...form, property_type: v })}>
                  <SelectTrigger className="h-9"><SelectValue placeholder="Tipo" /></SelectTrigger>
                  <SelectContent>{PROPERTY_TYPES.map((t) => <SelectItem key={t} value={t}>{t}</SelectItem>)}</SelectContent>
                </Select>
                <Select value={form.status} onValueChange={(v) => setForm({ ...form, status: v })}>
                  <SelectTrigger className="h-9"><SelectValue placeholder="Status" /></SelectTrigger>
                  <SelectContent>{STATUSES.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
                </Select>
                <div />
                <input type="number" value={form.minPrice} onChange={(e) => setForm({ ...form, minPrice: e.target.value })} placeholder="Preço mín." className="h-9 rounded-xl border border-border bg-surface px-3 text-sm outline-none focus:border-brand/40" />
                <input type="number" value={form.maxPrice} onChange={(e) => setForm({ ...form, maxPrice: e.target.value })} placeholder="Preço máx." className="h-9 rounded-xl border border-border bg-surface px-3 text-sm outline-none focus:border-brand/40" />
              </div>
              <button type="submit" disabled={!form.name.trim() || saving} className="w-full h-9 rounded-full bg-brand text-brand-foreground text-sm font-medium flex items-center justify-center gap-1.5 disabled:opacity-50">
                {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                Salvar busca
              </button>
            </form>
          </Panel>

          <div className="space-y-3">
            {propertiesStatus === 'loading' && <AsyncLoading className="h-10" label="Atualizando imóveis das buscas salvas…" />}
            {propertiesStatus === 'error' && <AsyncError error={propertiesError} />}
            {loadingSearches ? (
              <div className="flex items-center justify-center py-10"><Loader2 className="w-6 h-6 animate-spin text-text-muted" /></div>
            ) : searches.length === 0 ? (
              <Panel className="p-8 text-center text-sm text-text-muted">Nenhuma busca salva ainda. Crie uma à esquerda para acesso rápido.</Panel>
            ) : (
              searches.map((s) => {
                const matched = matchFor(s.filters);
                const open = expanded === s.id;
                return (
                  <Panel key={s.id} className="p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <h3 className="text-sm font-semibold text-foreground truncate">{s.name}</h3>
                          <span className="shrink-0 inline-flex items-center rounded-full bg-brand/10 text-brand text-[10px] font-semibold px-2 py-0.5">{matched.length} imóveis</span>
                        </div>
                        <div className="flex flex-wrap gap-1.5 mt-2">
                          {chips(s.filters).map((c, i) => (
                            <span key={i} className="inline-flex items-center rounded-full bg-elevated border border-border text-[11px] text-text-secondary px-2 py-0.5">{c}</span>
                          ))}
                          {chips(s.filters).length === 0 && <span className="text-[11px] text-text-muted">Sem filtros — todas as regiões</span>}
                        </div>
                      </div>
                      <div className="flex items-center gap-1">
                        <button onClick={() => setExpanded(open ? null : s.id)} className="w-8 h-8 rounded-full flex items-center justify-center text-text-secondary hover:bg-foreground/5">
                          {open ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                        </button>
                        <button onClick={() => remove(s.id)} className="w-8 h-8 rounded-full flex items-center justify-center text-text-muted hover:text-negative hover:bg-negative/5">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                    {open && (
                      <div className="mt-3 pt-3 border-t border-border">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-[11px] uppercase text-text-muted">Imóveis correspondentes</span>
                          <button onClick={() => navigate('/properties')} className="text-[11px] text-brand font-medium hover:underline flex items-center gap-1"><Building2 className="w-3 h-3" /> Ver todos</button>
                        </div>
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                          {matched.slice(0, 6).map((p) => (
                            <div key={p.id} className="rounded-xl border border-border bg-elevated/40 p-2.5">
                              <div className="text-xs font-medium text-foreground truncate">{p.title}</div>
                              <div className="text-[11px] text-text-secondary">{p.neighborhood} · {formatBRLCompact(p.price)}</div>
                            </div>
                          ))}
                          {matched.length === 0 && <p className="text-xs text-text-muted col-span-2">Nenhum imóvel corresponde a estes critérios.</p>}
                        </div>
                      </div>
                    )}
                  </Panel>
                );
              })
            )}
          </div>
        </div>
      </div>
    </>
  );
}
