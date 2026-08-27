import React, { useState, useEffect } from 'react';
import { appClient } from '@/demo/localAppClient';
import { Upload, Plus, Trash2, Search, Building2, MapPin, Database, FileSpreadsheet, CheckCircle2, XCircle, AlertCircle } from 'lucide-react';
import TopBar from '@/components/tupan/TopBar';
import { Panel, SectionTitle, ContextTag } from '@/components/tupan/primitives';
import { CITIES, PROPERTY_TYPES } from '@/lib/tupanData';
import { formatBRL, formatM2 } from '@/lib/format';
import { propertyTypeLabel } from '@/lib/labels';
import { cn } from '@/lib/utils';

const TABS = [
  { id: 'properties', label: 'Imóveis', icon: Building2 },
  { id: 'cities', label: 'Cidades', icon: Database },
  { id: 'areas', label: 'Áreas', icon: MapPin },
  { id: 'import', label: 'Importar', icon: FileSpreadsheet },
  { id: 'search', label: 'Buscar', icon: Search },
];

const emptyForm = {
  title: '', address: '', city: 'São Paulo', neighborhood: 'Pinheiros', latitude: '', longitude: '',
  property_type: 'Apartment', bedrooms: '', bathrooms: '', parking_spaces: '', area_m2: '', price: '',
  last_sale_price: '', last_sale_date: '', suggested_price: '', valuation_confidence: '',
  valuation_class: '', comparable_count: '', days_on_market: '', market_heat: '', liquidity_score: '',
  luxury_score: '', leisure_score: '', location_score: '', leverage_score: '', property_age: '', status: 'Active',
};

export default function DataManagement() {
  const [tab, setTab] = useState('properties');
  const [properties, setProperties] = useState([]);
  const [regions, setRegions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [importStatus, setImportStatus] = useState(null);
  const [searchQ, setSearchQ] = useState('');

  const load = async () => {
    setLoading(true);
    try {
      const [p, r] = await Promise.all([appClient.entities.Property.list('-created_date', 500), appClient.entities.MarketRegion.list('-created_date', 200)]);
      setProperties(p || []);
      setRegions(r || []);
    } catch (e) { console.error(e); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const submit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const numberOrUndefined = (value) => (value === '' || value == null ? undefined : Number(value));
      const price = numberOrUndefined(form.price);
      const areaM2 = numberOrUndefined(form.area_m2);
      const suggestedPrice = numberOrUndefined(form.suggested_price);
      const price_per_m2 = price && areaM2 ? Math.round(price / areaM2) : undefined;
      const price_deviation = price && suggestedPrice ? +(((price - suggestedPrice) / suggestedPrice) * 100).toFixed(1) : undefined;
      await appClient.entities.Property.create({
        ...form,
        price_per_m2,
        price_deviation,
        bedrooms: numberOrUndefined(form.bedrooms),
        bathrooms: numberOrUndefined(form.bathrooms),
        parking_spaces: numberOrUndefined(form.parking_spaces),
        area_m2: areaM2,
        price,
        latitude: numberOrUndefined(form.latitude),
        longitude: numberOrUndefined(form.longitude),
      });
      setForm(emptyForm);
      await load();
    } catch (e) { console.error(e); }
    finally { setSaving(false); }
  };

  const remove = async (id) => {
    try { await appClient.entities.Property.delete(id); setProperties((p) => p.filter((x) => x.id !== id)); } catch (e) { console.error(e); }
  };

  const onImport = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImportStatus({ loading: true });
    try {
      const { file_url } = await appClient.integrations.Core.UploadFile({ file });
      const res = await appClient.integrations.Core.ExtractDataFromUploadedFile({
        file_url,
        json_schema: { type: 'array', items: { type: 'object', properties: { title: { type: 'string' }, address: { type: 'string' }, neighborhood: { type: 'string' }, property_type: { type: 'string' }, bedrooms: { type: 'number' }, bathrooms: { type: 'number' }, parking_spaces: { type: 'number' }, area_m2: { type: 'number' }, price: { type: 'number' } } } },
      });
      const records = res.output || [];
      let success = 0, invalid = 0;
      const valid = records.filter((r) => r.title && r.price && r.area_m2);
      invalid = records.length - valid.length;
      if (valid.length) {
        const mapped = valid.map((r) => ({ ...emptyForm, ...r, city: 'São Paulo', price_per_m2: Math.round(r.price / r.area_m2) }));
        await appClient.entities.Property.bulkCreate(mapped);
        success = valid.length;
        await load();
      }
      setImportStatus({ loading: false, total: records.length, success, invalid, duplicates: 0, errors: invalid });
    } catch (e) {
      setImportStatus({ loading: false, total: 0, success: 0, invalid: 0, duplicates: 0, errors: 1, message: String(e) });
    }
  };

  const inputCls = 'h-8 rounded border border-border bg-elevated text-xs text-foreground px-2 outline-none focus:border-brand/50 w-full';
  const labelCls = 'text-[10px] uppercase tracking-wide text-text-muted';

  return (
    <>
      <TopBar title="Gestão de dados" subtitle="Banco de dados imobiliário · Administração" />
      <div className="flex-1 flex min-h-0">
        <div className="w-[200px] shrink-0 border-r border-border bg-surface py-3 px-2 space-y-0.5">
          {TABS.map((t) => {
            const Icon = t.icon;
            return <button key={t.id} onClick={() => setTab(t.id)} className={cn('w-full flex items-center gap-2.5 px-3 py-2 rounded text-[13px]', tab === t.id ? 'bg-brand/10 text-brand font-medium' : 'text-text-secondary hover:text-foreground hover:bg-elevated/60')}><Icon className="w-4 h-4" />{t.label}</button>;
          })}
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {tab === 'properties' && (
            <>
              <Panel className="p-4">
                <SectionTitle right={<ContextTag type="DATA">Cadastro manual</ContextTag>}>Cadastrar imóvel</SectionTitle>
                <form onSubmit={submit} className="space-y-3">
                  <div>
                    <div className={labelCls}>Localização</div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-1.5">
                      <input className={inputCls} placeholder="Título" value={form.title} onChange={(e) => set('title', e.target.value)} required />
                      <input className={inputCls} placeholder="Endereço" value={form.address} onChange={(e) => set('address', e.target.value)} />
                      <select className={inputCls} value={form.city} onChange={(e) => set('city', e.target.value)}>{CITIES.map((c) => <option key={c.name}>{c.name}</option>)}</select>
                      <select className={inputCls} value={form.neighborhood} onChange={(e) => set('neighborhood', e.target.value)}>{CITIES.find((c) => c.name === form.city)?.neighborhoods.map((n) => <option key={n}>{n}</option>)}</select>
                      <input className={inputCls} type="number" step="0.0001" placeholder="Latitude" value={form.latitude} onChange={(e) => set('latitude', e.target.value)} />
                      <input className={inputCls} type="number" step="0.0001" placeholder="Longitude" value={form.longitude} onChange={(e) => set('longitude', e.target.value)} />
                    </div>
                  </div>
                  <div>
                    <div className={labelCls}>Métricas do imóvel</div>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mt-1.5">
                      <input className={inputCls} type="number" placeholder="Quartos" value={form.bedrooms} onChange={(e) => set('bedrooms', e.target.value)} />
                      <input className={inputCls} type="number" placeholder="Banheiros" value={form.bathrooms} onChange={(e) => set('bathrooms', e.target.value)} />
                      <input className={inputCls} type="number" placeholder="Vagas" value={form.parking_spaces} onChange={(e) => set('parking_spaces', e.target.value)} />
                      <input className={inputCls} type="number" placeholder="Área m²" value={form.area_m2} onChange={(e) => set('area_m2', e.target.value)} />
                      <select className={inputCls} value={form.property_type} onChange={(e) => set('property_type', e.target.value)}>{PROPERTY_TYPES.map((t) => <option key={t} value={t}>{propertyTypeLabel(t)}</option>)}</select>
                    </div>
                  </div>
                  <div>
                    <div className={labelCls}>Preço</div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-1.5">
                      <input className={inputCls} type="number" placeholder="Preço atual" value={form.price} onChange={(e) => set('price', e.target.value)} />
                      <input className={inputCls} type="number" placeholder="Sugerido (AVM)" value={form.suggested_price} onChange={(e) => set('suggested_price', e.target.value)} />
                      <input className={inputCls} type="number" placeholder="Preço da última venda" value={form.last_sale_price} onChange={(e) => set('last_sale_price', e.target.value)} />
                      <input className={inputCls} type="date" value={form.last_sale_date} onChange={(e) => set('last_sale_date', e.target.value)} />
                    </div>
                  </div>
                  <div>
                    <div className={labelCls}>Inteligência do imóvel (0–100)</div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-1.5">
                      <input className={inputCls} type="number" placeholder="Luxo" value={form.luxury_score} onChange={(e) => set('luxury_score', e.target.value)} />
                      <input className={inputCls} type="number" placeholder="Lazer" value={form.leisure_score} onChange={(e) => set('leisure_score', e.target.value)} />
                      <input className={inputCls} type="number" placeholder="Localização" value={form.location_score} onChange={(e) => set('location_score', e.target.value)} />
                      <input className={inputCls} type="number" placeholder="Alavancagem" value={form.leverage_score} onChange={(e) => set('leverage_score', e.target.value)} />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                    <input className={inputCls} type="number" placeholder="Aquecimento de mercado" value={form.market_heat} onChange={(e) => set('market_heat', e.target.value)} />
                    <input className={inputCls} type="number" placeholder="DOM" value={form.days_on_market} onChange={(e) => set('days_on_market', e.target.value)} />
                    <input className={inputCls} type="number" placeholder="Idade do imóvel" value={form.property_age} onChange={(e) => set('property_age', e.target.value)} />
                    <select className={inputCls} value={form.status} onChange={(e) => set('status', e.target.value)}><option value="Active">Ativo</option><option value="Sold">Vendido</option><option value="Off Market">Fora do mercado</option></select>
                  </div>
                  <button disabled={saving} className="h-9 px-4 rounded bg-brand text-brand-foreground text-xs font-medium hover:bg-brand/90 disabled:opacity-40 flex items-center gap-1.5">
                    <Plus className="w-3.5 h-3.5" /> {saving ? 'Salvando…' : 'Cadastrar imóvel'}
                  </button>
                </form>
              </Panel>
              <Panel className="overflow-hidden">
                <div className="flex items-center justify-between px-4 py-2.5 border-b border-border">
                  <span className="text-[11px] font-semibold uppercase tracking-wider text-text-secondary">Banco de dados · {properties.length} registros</span>
                </div>
                <div className="overflow-x-auto max-h-96 overflow-y-auto">
                  <table className="w-full text-xs">
                    <thead className="sticky top-0 bg-surface"><tr className="border-b border-border text-text-muted"><th className="px-3 py-2 text-left font-medium">Imóvel</th><th className="px-3 py-2 text-left font-medium">Bairro</th><th className="px-3 py-2 text-left font-medium">Tipo</th><th className="px-3 py-2 text-right font-medium">Preço</th><th className="px-3 py-2 text-right font-medium">m²</th><th className="px-3 py-2"></th></tr></thead>
                    <tbody>
                      {properties.map((p) => (
                        <tr key={p.id} className="border-b border-border/50">
                          <td className="px-3 py-2 text-foreground">{p.title}</td>
                          <td className="px-3 py-2 text-text-secondary">{p.neighborhood}</td>
                          <td className="px-3 py-2 text-text-secondary">{propertyTypeLabel(p.property_type)}</td>
                          <td className="px-3 py-2 text-right tnum text-foreground">{formatBRL(p.price)}</td>
                          <td className="px-3 py-2 text-right tnum text-text-secondary">{formatM2(p.price_per_m2)}</td>
                          <td className="px-3 py-2 text-right"><button onClick={() => remove(p.id)} className="text-text-muted hover:text-negative"><Trash2 className="w-3.5 h-3.5" /></button></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Panel>
            </>
          )}

          {tab === 'cities' && (
            <Panel className="p-4">
              <SectionTitle right={<ContextTag type="DATA">Referência</ContextTag>}>Cidades</SectionTitle>
              <table className="w-full text-xs">
                <thead><tr className="text-text-muted border-b border-border"><th className="text-left py-2 font-medium">Cidade</th><th className="text-left py-2 font-medium">Estado</th><th className="text-right py-2 font-medium">Áreas</th></tr></thead>
                <tbody>{CITIES.map((c) => <tr key={c.name} className="border-b border-border/50"><td className="py-2 text-foreground">{c.name}</td><td className="py-2 text-text-secondary">{c.state}</td><td className="py-2 text-right tnum text-text-secondary">{c.neighborhoods.length}</td></tr>)}</tbody>
              </table>
            </Panel>
          )}

          {tab === 'areas' && (
            <Panel className="p-4">
              <SectionTitle right={<ContextTag type="DATA">{regions.length}</ContextTag>}>Áreas / Regiões de mercado</SectionTitle>
              <table className="w-full text-xs">
                <thead><tr className="text-text-muted border-b border-border"><th className="text-left py-2 font-medium">Região</th><th className="text-left py-2 font-medium">Cidade</th><th className="text-right py-2 font-medium">Aquecimento</th><th className="text-right py-2 font-medium">Preço/m²</th><th className="text-right py-2 font-medium">Inventário</th></tr></thead>
                <tbody>{regions.map((r) => <tr key={r.id} className="border-b border-border/50"><td className="py-2 text-foreground">{r.name}</td><td className="py-2 text-text-secondary">{r.city}</td><td className="py-2 text-right tnum text-text-secondary">{r.market_heat}</td><td className="py-2 text-right tnum text-text-secondary">{formatM2(r.avg_price_per_m2)}</td><td className="py-2 text-right tnum text-text-secondary">{r.inventory}</td></tr>)}</tbody>
              </table>
            </Panel>
          )}

          {tab === 'import' && (
            <Panel className="p-6">
              <SectionTitle right={<ContextTag type="DATA">Planilha</ContextTag>}>Importar imóveis</SectionTitle>
              <label className="flex flex-col items-center justify-center border-2 border-dashed border-border rounded-lg py-12 cursor-pointer hover:border-brand/50 transition-colors">
                <Upload className="w-8 h-8 text-text-muted mb-2" />
                <span className="text-sm text-text-secondary">Clique para enviar CSV / Excel / JSON</span>
                <span className="text-[10px] text-text-muted mt-1">Colunas: title, address, neighborhood, property_type, bedrooms, bathrooms, parking_spaces, area_m2, price</span>
                <input type="file" accept=".csv,.xlsx,.xls,.json" className="hidden" onChange={onImport} />
              </label>
              {importStatus?.loading && <div className="flex items-center gap-2 mt-4 text-xs text-text-muted"><div className="w-4 h-4 border-2 border-border border-t-brand rounded-full animate-spin" /> Processando arquivo…</div>}
              {importStatus && !importStatus.loading && (
                <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-3">
                  <div className="rounded border border-positive/20 bg-positive/5 p-3 flex items-center gap-2"><CheckCircle2 className="w-4 h-4 text-positive" /><div><div className="text-[10px] uppercase text-text-muted">Bem-sucedidos</div><div className="text-lg font-semibold tnum text-positive">{importStatus.success}</div></div></div>
                  <div className="rounded border border-negative/20 bg-negative/5 p-3 flex items-center gap-2"><XCircle className="w-4 h-4 text-negative" /><div><div className="text-[10px] uppercase text-text-muted">Inválidos</div><div className="text-lg font-semibold tnum text-negative">{importStatus.invalid}</div></div></div>
                  <div className="rounded border border-warning/20 bg-warning/5 p-3 flex items-center gap-2"><AlertCircle className="w-4 h-4 text-warning" /><div><div className="text-[10px] uppercase text-text-muted">Duplicados</div><div className="text-lg font-semibold tnum text-warning">{importStatus.duplicates}</div></div></div>
                  <div className="rounded border border-border bg-elevated/50 p-3 flex items-center gap-2"><XCircle className="w-4 h-4 text-text-muted" /><div><div className="text-[10px] uppercase text-text-muted">Erros</div><div className="text-lg font-semibold tnum text-foreground">{importStatus.errors}</div></div></div>
                </div>
              )}
            </Panel>
          )}

          {tab === 'search' && (
            <Panel className="p-4">
              <SectionTitle right={<ContextTag type="AI">Semântica</ContextTag>}>Busca semântica de imóveis</SectionTitle>
              <div className="flex items-center gap-1.5 h-10 px-3 rounded border border-border bg-elevated mb-3">
                <Search className="w-4 h-4 text-text-muted" />
                <input value={searchQ} onChange={(e) => setSearchQ(e.target.value)} placeholder="ex.: apartamentos de luxo em Pinheiros até 2M com alto aquecimento" className="bg-transparent outline-none text-sm text-foreground w-full" />
              </div>
              <div className="space-y-1">
                {properties.filter((p) => !searchQ || `${p.title} ${p.neighborhood} ${p.property_type}`.toLowerCase().includes(searchQ.toLowerCase())).map((p) => (
                  <div key={p.id} className="flex items-center justify-between py-2 border-b border-border/60 last:border-0 text-xs">
                    <div><span className="text-foreground">{p.title}</span><span className="text-text-muted ml-2">{p.neighborhood} · {propertyTypeLabel(p.property_type)}</span></div>
                    <span className="tnum text-text-secondary">{formatBRL(p.price)}</span>
                  </div>
                ))}
              </div>
            </Panel>
          )}
        </div>
      </div>
    </>
  );
}
