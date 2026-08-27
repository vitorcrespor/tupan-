import React, { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronDown, ChevronRight, CheckCircle2, AlertCircle, Clock, Cpu, Database, Activity } from 'lucide-react';
import TopBar from '@/components/tupan/TopBar';
import { Panel, SectionTitle, ContextTag, StatusDot } from '@/components/tupan/primitives';
import { useApp } from '@/lib/AppContext';
import { cn } from '@/lib/utils';
import { getAgentTraces } from '@/api/agent';
import { apiErrorMessage } from '@/api/client';

const TABS = ['Rastros', 'Ferramentas', 'Fontes de dados', 'Desempenho', 'Erros'];

function formatTimestamp(value) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? String(value) : date.toLocaleTimeString('pt-BR');
}

function eventFailed(event) {
  return /error|fail|failed/i.test(event.status || '');
}

export default function AgentLog() {
  const { recentTrace } = useApp();
  const [tab, setTab] = useState('Rastros');
  const [expanded, setExpanded] = useState(null);
  const traceQuery = useQuery({
    queryKey: ['agent-traces', recentTrace?.sessionId],
    queryFn: ({ signal }) => getAgentTraces(recentTrace.sessionId, { signal }),
    enabled: Boolean(recentTrace?.sessionId),
    retry: false,
  });
  const events = Array.isArray(traceQuery.data?.events) ? traceQuery.data.events : [];
  const tools = useMemo(() => {
    const entries = new Map();
    events.forEach((event) => {
      const name = event.tool || event.event_type;
      const current = entries.get(name) || { name, calls: 0, ms: 0 };
      current.calls += 1;
      current.ms += Number(event.duration_ms) || 0;
      entries.set(name, current);
    });
    return [...entries.values()];
  }, [events]);
  const errors = events.filter(eventFailed).map((event) => event.summary).concat(recentTrace?.warnings || []);
  const totalMs = events.reduce((total, event) => total + (Number(event.duration_ms) || 0), 0);
  const hasTrace = Boolean(recentTrace?.sessionId);
  const status = traceQuery.isError ? 'Indisponível' : errors.length ? 'Com avisos' : hasTrace ? 'Operacional' : 'Sem sessão';

  return (
    <>
      <TopBar title="Registro do agente" subtitle="Observabilidade de IA · Centro de controle" />
      <div className="flex-1 flex min-h-0">
        <div className="w-[280px] shrink-0 border-r border-border bg-surface overflow-y-auto">
          <div className="px-4 py-3 border-b border-border">
            <div className="flex items-center gap-2">
              <StatusDot status={status === 'Operacional' ? 'Operational' : 'Unknown'} />
              <span className="text-sm font-semibold text-foreground">Centro de controle</span>
            </div>
            <div className="text-[10px] text-text-muted mt-0.5">Status: {status} · Dados de execução do backend</div>
          </div>
          <div className="p-2 space-y-1">
            {!hasTrace && <div className="px-3 py-6 text-center text-xs text-text-muted">Envie uma mensagem ao Ceres para iniciar uma sessão observável.</div>}
            {hasTrace && (
              <div className="w-full text-left px-3 py-2 rounded border border-brand/40 bg-brand/5 text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-foreground">{recentTrace.sessionId.slice(0, 8)}</span>
                  <StatusDot status={status === 'Operacional' ? 'Operational' : 'Unknown'} />
                </div>
                <div className="text-text-muted truncate mt-0.5">{recentTrace.query}</div>
                <div className="text-[10px] text-text-muted mt-0.5">{formatTimestamp(recentTrace.createdAt)}</div>
              </div>
            )}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-4">
          {!hasTrace && <div className="h-full flex items-center justify-center text-center text-xs text-text-muted">Nenhuma sessão do agente foi selecionada. Envie uma mensagem ao Ceres para ver os rastros deste atendimento.</div>}
          {hasTrace && (
            <>
              <Panel className="p-4">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-sm text-foreground">{recentTrace.sessionId.slice(0, 8)}</span>
                      <span className={cn('text-[10px] px-1.5 py-0.5 rounded border', status === 'Operacional' ? 'bg-positive/10 text-positive border-positive/20' : 'bg-warning/10 text-warning border-warning/20')}>{status}</span>
                    </div>
                    <div className="text-xs text-text-secondary mt-1">&quot;{recentTrace.query}&quot;</div>
                  </div>
                  <div className="grid grid-cols-3 gap-3 text-center">
                    <div><div className="text-[10px] uppercase text-text-muted">Tempo registrado</div><div className="text-sm font-semibold tnum text-foreground">{totalMs ? `${(totalMs / 1000).toFixed(2)}s` : '—'}</div></div>
                    <div><div className="text-[10px] uppercase text-text-muted">Ferramentas</div><div className="text-sm font-semibold tnum text-foreground">{tools.length || '—'}</div></div>
                    <div><div className="text-[10px] uppercase text-text-muted">Tokens</div><div className="text-sm font-semibold tnum text-foreground">—</div></div>
                  </div>
                </div>
              </Panel>

              <div className="flex items-center gap-1 border-b border-border">
                {TABS.map((item) => (
                  <button key={item} onClick={() => setTab(item)} className={cn('px-3 py-2 text-xs font-medium border-b-2 -mb-px', tab === item ? 'border-brand text-foreground' : 'border-transparent text-text-muted hover:text-text-secondary')}>{item}</button>
                ))}
              </div>

              {traceQuery.isLoading && <div className="py-8 text-center text-xs text-text-muted">Carregando rastros do backend…</div>}
              {traceQuery.isError && <div role="alert" className="py-8 text-center text-xs text-negative">{apiErrorMessage(traceQuery.error)}</div>}
              {!traceQuery.isLoading && !traceQuery.isError && tab === 'Rastros' && (
                <Panel className="p-4">
                  <SectionTitle right={<ContextTag type="DATA">Linha do tempo</ContextTag>}>Linha do tempo de execução</SectionTitle>
                  {events.length === 0 ? <div className="py-6 text-center text-xs text-text-muted">O backend ainda não registrou eventos para esta sessão.</div> : <div className="space-y-1">
                    {events.map((event, index) => (
                      <div key={`${event.created_at}-${index}`}>
                        <button onClick={() => setExpanded(expanded === index ? null : index)} className="w-full flex items-center gap-3 py-2 border-b border-border/60 last:border-0 text-left hover:bg-elevated/30 -mx-1 px-1 rounded">
                          <span className="text-[10px] font-mono text-text-muted w-16 shrink-0">{formatTimestamp(event.created_at)}</span>
                          {expanded === index ? <ChevronDown className="w-3.5 h-3.5 text-text-muted shrink-0" /> : <ChevronRight className="w-3.5 h-3.5 text-text-muted shrink-0" />}
                          <span className="text-xs font-medium text-foreground flex-1">{event.tool || event.event_type}</span>
                          <span className="text-[10px] text-text-secondary">{event.summary || 'Sem resumo'}</span>
                          <span className="text-[10px] tnum text-text-muted w-12 text-right">{event.duration_ms == null ? '—' : `${event.duration_ms}ms`}</span>
                          {eventFailed(event) ? <AlertCircle className="w-3.5 h-3.5 text-negative shrink-0" /> : <CheckCircle2 className="w-3.5 h-3.5 text-positive shrink-0" />}
                        </button>
                        {expanded === index && <div className="ml-16 pl-3 border-l border-border py-2 mb-1 space-y-1 text-xs"><div className="flex justify-between"><span className="text-text-muted">Tipo</span><span className="text-text-secondary">{event.event_type}</span></div><div className="flex justify-between"><span className="text-text-muted">Status</span><span className={eventFailed(event) ? 'text-negative' : 'text-positive'}>{event.status}</span></div>{event.tool && <div className="flex justify-between"><span className="text-text-muted">Ferramenta</span><span className="text-text-secondary">{event.tool}</span></div>}</div>}
                      </div>
                    ))}
                  </div>}
                </Panel>
              )}

              {!traceQuery.isLoading && !traceQuery.isError && tab === 'Ferramentas' && <Panel className="p-4"><SectionTitle right={<ContextTag type="DATA">{tools.length}</ContextTag>}>Ferramentas usadas</SectionTitle>{tools.length === 0 ? <div className="py-6 text-center text-xs text-text-muted">Nenhuma chamada de ferramenta foi registrada.</div> : <table className="w-full text-xs"><thead><tr className="text-text-muted border-b border-border"><th className="text-left py-2 font-medium">Ferramenta</th><th className="text-right py-2 font-medium">Chamadas</th><th className="text-right py-2 font-medium">Tempo</th></tr></thead><tbody>{tools.map((tool) => <tr key={tool.name} className="border-b border-border/50"><td className="py-2 text-foreground"><span className="flex items-center gap-2"><Cpu className="w-3.5 h-3.5 text-text-muted" />{tool.name}</span></td><td className="py-2 text-right tnum text-text-secondary">{tool.calls}</td><td className="py-2 text-right tnum text-text-secondary">{tool.ms || '—'}{tool.ms ? 'ms' : ''}</td></tr>)}</tbody></table>}</Panel>}

              {!traceQuery.isLoading && !traceQuery.isError && tab === 'Fontes de dados' && <Panel className="p-4"><SectionTitle right={<ContextTag type="DATA">Fontes</ContextTag>}>Fontes de dados</SectionTitle>{recentTrace.sources?.length ? <div className="space-y-2">{recentTrace.sources.map((source, index) => <div key={`${source.label}-${index}`} className="flex items-center gap-2 py-1.5 border-b border-border/60 last:border-0 text-xs"><Database className="w-3.5 h-3.5 text-brand" /><span className="text-text-secondary">{source.label}{source.detail ? ` · ${source.detail}` : ''}</span></div>)}</div> : <div className="py-6 text-center text-xs text-text-muted">A resposta do agente não reportou fontes.</div>}</Panel>}

              {!traceQuery.isLoading && !traceQuery.isError && tab === 'Desempenho' && <Panel className="p-4"><SectionTitle right={<ContextTag type="MODEL">Métricas</ContextTag>}>Desempenho</SectionTitle><div className="grid grid-cols-2 md:grid-cols-4 gap-3">{[{ l: 'Tempo registrado', v: totalMs ? `${(totalMs / 1000).toFixed(2)}s` : '—', i: Clock }, { l: 'Ferramentas usadas', v: tools.length || '—', i: Cpu }, { l: 'Eventos', v: events.length || '—', i: Activity }, { l: 'Tempo médio', v: tools.length && totalMs ? `${Math.round(totalMs / tools.length)}ms` : '—', i: Clock }].map((item) => { const Icon = item.i; return <div key={item.l} className="rounded border border-border bg-elevated/50 p-3"><div className="flex items-center gap-1.5 text-[10px] uppercase text-text-muted"><Icon className="w-3 h-3" />{item.l}</div><div className="text-lg font-semibold tnum text-foreground mt-1">{item.v}</div></div>; })}</div></Panel>}

              {!traceQuery.isLoading && !traceQuery.isError && tab === 'Erros' && <Panel className="p-4"><SectionTitle right={<ContextTag type="DATA">Erros</ContextTag>}>Erros e avisos</SectionTitle>{errors.length === 0 ? <div className="flex items-center gap-2 py-6 text-xs text-positive"><CheckCircle2 className="w-4 h-4" />Nenhum erro registrado nesta sessão.</div> : <div className="space-y-2">{errors.map((error, index) => <div key={index} className="flex items-center gap-2 text-xs text-negative"><AlertCircle className="w-3.5 h-3.5" />{error}</div>)}</div>}</Panel>}
            </>
          )}
        </div>
      </div>
    </>
  );
}
