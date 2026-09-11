import React, { useState } from 'react';
import { useAuth } from '@/lib/AuthContext';
import TopBar from '@/components/tupan/TopBar';
import { Panel, SectionTitle, MetricRow } from '@/components/tupan/primitives';
import { TIME_PERIODS } from '@/lib/tupanData';
import { cn } from '@/lib/utils';
import ThemePicker from '@/components/tupan/ThemePicker';

function Toggle({ on, onChange, label }) {
  return (
    <button type="button" role="switch" aria-checked={on} aria-label={label} onClick={() => onChange(!on)} className={cn('w-9 h-5 rounded-full transition-colors relative shrink-0 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-ring', on ? 'bg-brand' : 'bg-border')}>
      <span className="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-foreground transition-transform" style={{ transform: on ? 'translateX(16px)' : 'translateX(0)' }} />
    </button>
  );
}

export default function Settings() {
  const { user } = useAuth();
  const [defaultPeriod, setDefaultPeriod] = useState('90d');
  const [prefs, setPrefs] = useState({ briefs: true, alerts: true, push: false, sound: false, autoRefresh: true, compact: true });
  const setP = (k, v) => setPrefs((p) => ({ ...p, [k]: v }));

  const inputCls = 'field-control h-9 min-w-0 w-full text-sm';

  return (
    <>
      <TopBar title="Configurações" subtitle="Configuração do espaço de trabalho" />
      <div className="workspace-content flex-1 w-full max-w-4xl overflow-y-auto mx-auto">
        <Panel className="p-4">
          <SectionTitle>Tema do espaço</SectionTitle>
          <ThemePicker />
        </Panel>

        <section className="py-6 border-b border-border/60">
          <SectionTitle>Perfil</SectionTitle>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <label className="text-xs text-text-secondary">Nome completo<input className={inputCls + ' mt-1.5'} defaultValue={user?.full_name || ''} /></label>
            <label className="text-xs text-text-secondary">E-mail<input className={inputCls + ' mt-1.5'} defaultValue={user?.email || ''} disabled /></label>
            <label className="text-xs text-text-secondary">Função<input className={inputCls + ' mt-1.5'} defaultValue={user?.role || '—'} disabled /></label>
            <label className="text-xs text-text-secondary">Corretora<input className={inputCls + ' mt-1.5'} defaultValue="" /></label>
          </div>
        </section>

        <section className="py-6 border-b border-border/60">
          <SectionTitle>Preferências</SectionTitle>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-text-secondary">Período padrão</span>
              <select aria-label="Período padrão" value={defaultPeriod} onChange={(e) => setDefaultPeriod(e.target.value)} className="field-control h-9 text-xs">
                {TIME_PERIODS.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
              </select>
            </div>
            <div className="flex items-center justify-between gap-4"><span className="text-xs text-text-secondary">Densidade compacta</span><Toggle label="Densidade compacta" on={prefs.compact} onChange={(v) => setP('compact', v)} /></div>
            <div className="flex items-center justify-between gap-4"><span className="text-xs text-text-secondary">Atualizar dados automaticamente</span><Toggle label="Atualizar dados automaticamente" on={prefs.autoRefresh} onChange={(v) => setP('autoRefresh', v)} /></div>
          </div>
        </section>

        <section className="py-6 border-b border-border/60">
          <SectionTitle>Configuração do modelo</SectionTitle>
          <MetricRow label="Modelo do agente" value="Configurado pelo backend" />
          <MetricRow label="Motor AVM" value="Artefato carregado pelo backend" />
          <MetricRow label="Limiar de confiança" value="Não exposto pela API" />
          <MetricRow label="Janela de contexto" value="Não exposta pela API" />
          <MetricRow label="Fonte de dados" value="Configurada pelo ambiente" />
        </section>

        <section className="py-6">
          <SectionTitle>Alertas</SectionTitle>
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-4"><span className="text-xs text-text-secondary">Resumos de mercado com IA</span><Toggle label="Resumos de mercado com IA" on={prefs.briefs} onChange={(v) => setP('briefs', v)} /></div>
            <div className="flex items-center justify-between gap-4"><span className="text-xs text-text-secondary">Alertas do portfólio</span><Toggle label="Alertas do portfólio" on={prefs.alerts} onChange={(v) => setP('alerts', v)} /></div>
            <div className="flex items-center justify-between gap-4"><span className="text-xs text-text-secondary">Notificações push</span><Toggle label="Notificações push" on={prefs.push} onChange={(v) => setP('push', v)} /></div>
            <div className="flex items-center justify-between gap-4"><span className="text-xs text-text-secondary">Alertas sonoros</span><Toggle label="Alertas sonoros" on={prefs.sound} onChange={(v) => setP('sound', v)} /></div>
          </div>
        </section>
      </div>
    </>
  );
}
