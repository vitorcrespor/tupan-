import React, { useState } from 'react';
import { useAuth } from '@/lib/AuthContext';
import TopBar from '@/components/tupan/TopBar';
import { Panel, SectionTitle, ContextTag, MetricRow } from '@/components/tupan/primitives';
import { TIME_PERIODS } from '@/lib/tupanData';
import { cn } from '@/lib/utils';
import ThemePicker from '@/components/tupan/ThemePicker';

function Toggle({ on, onChange }) {
  return (
    <button onClick={() => onChange(!on)} className={cn('w-9 h-5 rounded-full transition-colors relative shrink-0', on ? 'bg-brand' : 'bg-border')}>
      <span className="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-foreground transition-transform" style={{ transform: on ? 'translateX(16px)' : 'translateX(0)' }} />
    </button>
  );
}

export default function Settings() {
  const { user } = useAuth();
  const [defaultPeriod, setDefaultPeriod] = useState('90d');
  const [prefs, setPrefs] = useState({ briefs: true, alerts: true, push: false, sound: false, autoRefresh: true, compact: true });
  const setP = (k, v) => setPrefs((p) => ({ ...p, [k]: v }));

  const inputCls = 'h-8 rounded border border-border bg-elevated text-xs text-foreground px-2 outline-none focus:border-brand/50 w-full';

  return (
    <>
      <TopBar title="Configurações" subtitle="Configuração do espaço de trabalho" />
      <div className="flex-1 overflow-y-auto p-5 max-w-4xl space-y-4">
        <Panel className="p-4">
          <SectionTitle right={<ContextTag type="AI">Aparência</ContextTag>}>Tema do espaço</SectionTitle>
          <ThemePicker />
        </Panel>

        <Panel className="p-4">
          <SectionTitle right={<ContextTag type="DATA">Conta</ContextTag>}>Perfil</SectionTitle>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div><label className="text-[10px] uppercase tracking-wide text-text-muted">Nome completo</label><input className={inputCls + ' mt-1'} defaultValue={user?.full_name || ''} /></div>
            <div><label className="text-[10px] uppercase tracking-wide text-text-muted">E-mail</label><input className={inputCls + ' mt-1'} defaultValue={user?.email || ''} disabled /></div>
            <div><label className="text-[10px] uppercase tracking-wide text-text-muted">Função</label><input className={inputCls + ' mt-1'} defaultValue={user?.role || '—'} disabled /></div>
            <div><label className="text-[10px] uppercase tracking-wide text-text-muted">Corretora</label><input className={inputCls + ' mt-1'} defaultValue="" /></div>
          </div>
        </Panel>

        <Panel className="p-4">
          <SectionTitle right={<ContextTag type="DATA">Padrões</ContextTag>}>Preferências</SectionTitle>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-text-secondary">Período padrão</span>
              <select value={defaultPeriod} onChange={(e) => setDefaultPeriod(e.target.value)} className="h-8 rounded border border-border bg-elevated text-xs text-text-secondary px-2 outline-none">
                {TIME_PERIODS.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
              </select>
            </div>
            <div className="flex items-center justify-between"><span className="text-xs text-text-secondary">Densidade compacta</span><Toggle on={prefs.compact} onChange={(v) => setP('compact', v)} /></div>
            <div className="flex items-center justify-between"><span className="text-xs text-text-secondary">Atualizar dados automaticamente</span><Toggle on={prefs.autoRefresh} onChange={(v) => setP('autoRefresh', v)} /></div>
          </div>
        </Panel>

        <Panel className="p-4">
          <SectionTitle right={<ContextTag type="MODEL">Inteligência</ContextTag>}>Configuração do modelo</SectionTitle>
          <MetricRow label="Modelo do agente" value="Configurado pelo backend" />
          <MetricRow label="Motor AVM" value="Artefato carregado pelo backend" />
          <MetricRow label="Limiar de confiança" value="Não exposto pela API" />
          <MetricRow label="Janela de contexto" value="Não exposta pela API" />
          <MetricRow label="Fonte de dados" value="Configurada pelo ambiente" />
        </Panel>

        <Panel className="p-4">
          <SectionTitle right={<ContextTag type="AI">Notificações</ContextTag>}>Alertas</SectionTitle>
          <div className="space-y-3">
            <div className="flex items-center justify-between"><span className="text-xs text-text-secondary">Resumos de mercado com IA</span><Toggle on={prefs.briefs} onChange={(v) => setP('briefs', v)} /></div>
            <div className="flex items-center justify-between"><span className="text-xs text-text-secondary">Alertas do portfólio</span><Toggle on={prefs.alerts} onChange={(v) => setP('alerts', v)} /></div>
            <div className="flex items-center justify-between"><span className="text-xs text-text-secondary">Notificações push</span><Toggle on={prefs.push} onChange={(v) => setP('push', v)} /></div>
            <div className="flex items-center justify-between"><span className="text-xs text-text-secondary">Alertas sonoros</span><Toggle on={prefs.sound} onChange={(v) => setP('sound', v)} /></div>
          </div>
        </Panel>
      </div>
    </>
  );
}
