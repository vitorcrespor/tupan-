import React, { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { Sparkles, Send, X, Plus, Trash2, Database, MapPin, Building2, BarChart3, Filter, Clock, Calculator } from 'lucide-react';
import TopBar from '@/components/tupan/TopBar';
import { useApp } from '@/lib/AppContext';
import { useTupanData } from '@/lib/useTupanData';
import { SAMPLE_QUESTIONS } from '@/lib/tupanData';
import { cn } from '@/lib/utils';
import { sendAgentMessage } from '@/api/agent';
import { apiErrorMessage } from '@/api/client';

const TYPE_ICON = { Portfolio: Database, Property: Building2, Region: MapPin, Metric: BarChart3, Filters: Filter, Period: Clock, AVM: Calculator };

export default function IntelligenceAgent() {
  const { agentContextItems, addAgentContext, removeAgentContext, clearAgentContext, agentPrefill, setAgentPrefill, setRecentTrace } = useApp();
  const { properties, regions } = useTupanData();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const endRef = useRef(null);

  useEffect(() => {
    if (agentPrefill) { setInput(agentPrefill); setAgentPrefill(''); }
  }, [agentPrefill, setAgentPrefill]);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, loading]);

  const send = async (text) => {
    if (!text.trim() || loading) return;
    const userMsg = { role: 'user', content: text, context: agentContextItems };
    setMessages((m) => [...m, userMsg]);
    setInput('');
    setLoading(true);
    const t0 = performance.now();
    try {
      const res = await sendAgentMessage({
        message: text,
        sessionId,
        contextItems: agentContextItems,
      });
      const runtime = ((performance.now() - t0) / 1000).toFixed(2);
      setSessionId(res.session_id);
      setMessages((m) => [...m, { role: 'assistant', content: res.message.content, runtime, sources: res.sources, warnings: res.warnings }]);
      setRecentTrace({
        sessionId: res.session_id,
        query: text,
        createdAt: new Date().toISOString(),
        sources: res.sources || [],
        warnings: res.warnings || [],
      });
    } catch (e) {
      setMessages((m) => [...m, { role: 'assistant', content: apiErrorMessage(e), error: true }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <TopBar title="Agente Ceres" subtitle="Espaço de trabalho de IA · Contexto ativo" />
      <div className="flex-1 flex min-h-0 flex-col lg:flex-row">
        <div className="flex-1 flex flex-col min-w-0">
          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            {messages.length === 0 && (
              <div className="h-full flex flex-col items-center justify-center text-center gap-4">
                <div className="w-12 h-12 rounded-lg bg-brand/10 border border-brand/30 flex items-center justify-center">
                  <Sparkles className="w-6 h-6 text-brand" />
                </div>
                <div>
                  <h2 className="text-base font-semibold text-foreground">Pergunte à Ceres</h2>
                  <p className="text-xs text-text-muted mt-1 max-w-md">Sua assistente de inteligência imobiliária. Pergunte sobre risco do portfólio, preço, demanda ou tendências — a Ceres usa o contexto ativo para fundamentar cada resposta.</p>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-w-2xl w-full mt-2">
                  {SAMPLE_QUESTIONS.map((q) => (
                    <button key={q} onClick={() => send(q)} className="text-left text-xs text-text-secondary px-3 py-2.5 rounded border border-border bg-surface hover:bg-elevated/60 hover:text-foreground transition-colors">
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={cn('flex gap-3', m.role === 'user' ? 'justify-end' : '')}>
                {m.role === 'assistant' && <div className="w-7 h-7 rounded bg-brand/10 border border-brand/30 flex items-center justify-center shrink-0"><Sparkles className="w-3.5 h-3.5 text-brand" /></div>}
                <div className={cn('max-w-[80%] rounded-lg p-3.5', m.role === 'user' ? 'bg-brand/10 border border-brand/20' : 'bg-surface border border-border')}>
                  {m.context?.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-2 pb-2 border-b border-border/60">
                      {m.context.map((c) => <span key={c.id} className="text-[9px] px-1.5 py-0.5 rounded bg-elevated text-text-muted border border-border">{c.type}: {c.label}</span>)}
                    </div>
                  )}
                  <div className={cn('prose prose-sm max-w-none text-text-secondary [&_p]:my-1.5 [&_li]:my-0.5 [&_strong]:text-foreground [&_h1]:text-foreground [&_h1]:text-sm [&_h2]:text-foreground [&_h2]:text-sm [&_h3]:text-foreground [&_h3]:text-xs [&_table]:text-xs [&_th]:text-foreground [&_td]:py-1', m.error && 'text-negative')}>
                    <ReactMarkdown>{m.content}</ReactMarkdown>
                  </div>
                  {m.warnings?.length > 0 && <div className="mt-2 text-[10px] text-warning">{m.warnings.join(' ')}</div>}
                  {m.runtime && <div className="text-[10px] text-text-muted mt-2 pt-2 border-t border-border/40">Tempo de resposta {m.runtime}s · Ceres v2.4</div>}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex gap-3">
                <div className="w-7 h-7 rounded bg-brand/10 border border-brand/30 flex items-center justify-center shrink-0"><Sparkles className="w-3.5 h-3.5 text-brand animate-pulse" /></div>
                <div className="bg-surface border border-border rounded-lg p-3.5 flex items-center gap-2 text-xs text-text-muted">
                  <span className="ceres-pending-dot w-2 h-2 rounded-full bg-brand" style={{ animationDelay: '0ms' }} />
                  <span className="ceres-pending-dot w-2 h-2 rounded-full bg-brand" style={{ animationDelay: '150ms' }} />
                  <span className="ceres-pending-dot w-2 h-2 rounded-full bg-brand" style={{ animationDelay: '300ms' }} />
                  <span className="ml-1">Analisando o contexto…</span>
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>
          <div
            className="border-t border-border p-3 bg-surface"
            onDragOver={(event) => event.preventDefault()}
            onDrop={(event) => {
              event.preventDefault();
              try {
                const item = JSON.parse(event.dataTransfer.getData('application/x-ceres-context'));
                addAgentContext(item);
                setInput((current) => current || `Use ${item.label} como referência anexa do painel. Explique as evidências e as próximas ações recomendadas.`);
              } catch { /* Ignore non-Ceres drops. */ }
            }}
          >
            <div className="flex items-end gap-2">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(input); } }}
                aria-label="Mensagem para a Ceres" placeholder="Pergunte à Ceres sobre seu portfólio ou o mercado…"
                rows={1}
                className="flex-1 resize-none bg-elevated border border-border rounded-lg px-3 py-2.5 text-sm text-foreground outline-none focus:border-brand/50 max-h-32"
              />
              <button onClick={() => send(input)} disabled={loading || !input.trim()} className="h-10 px-4 rounded-lg bg-brand text-brand-foreground text-sm font-medium hover:bg-brand/90 disabled:opacity-40 flex items-center gap-1.5">
                <Send className="w-4 h-4" /> Enviar
              </button>
            </div>
          </div>
        </div>

        <div className="surface-panel w-full max-h-[36vh] shrink-0 border-x-0 border-b-0 border-t flex flex-col overflow-y-auto lg:max-h-none lg:w-[300px] lg:border-y-0 lg:border-l">
          <div className="flex items-center justify-between px-4 h-11 border-b border-border sticky top-0 bg-surface z-10">
            <span className="text-sm font-semibold text-foreground">Contexto ativo</span>
            {agentContextItems.length > 0 && <button type="button" onClick={clearAgentContext} aria-label="Limpar contexto ativo" className="icon-control h-8 w-8 text-text-muted hover:text-negative"><Trash2 className="w-3.5 h-3.5" /></button>}
          </div>
          <div className="p-3 space-y-2 flex-1">
            {agentContextItems.length === 0 && <div className="text-xs text-text-muted text-center py-8">Nenhum contexto ativo. Selecione uma região, um imóvel ou uma métrica em outra tela para fundamentar as respostas da Ceres.</div>}
            {agentContextItems.map((item) => {
              const Icon = TYPE_ICON[item.type] || Plus;
              return (
                <div key={item.id} className="rounded border border-border bg-elevated/50 p-2.5 group">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 min-w-0">
                      <Icon className="w-3.5 h-3.5 text-brand shrink-0" />
                      <span className="text-xs font-medium text-foreground truncate">{item.label}</span>
                    </div>
                    <button type="button" onClick={() => removeAgentContext(item.id)} aria-label={`Remover ${item.label} do contexto`} className="icon-control h-7 w-7 text-text-muted hover:text-negative opacity-100 lg:opacity-0 lg:group-hover:opacity-100"><X className="w-3 h-3" /></button>
                  </div>
                  <div className="text-[10px] text-text-muted mt-0.5">{item.type}</div>
                </div>
              );
            })}
          </div>
          <div className="p-3 border-t border-border space-y-1.5">
            <div className="text-[10px] uppercase tracking-wide text-text-muted mb-1">Adicionar rapidamente</div>
            <button onClick={() => { const r = regions[0]; if (r) addAgentContext({ id: `region-${r.id}`, type: 'Region', label: r.name, data: r }); }} className="w-full text-left text-xs text-text-secondary px-2 py-1.5 rounded hover:bg-elevated/60 flex items-center gap-2"><MapPin className="w-3.5 h-3.5" /> Adicionar principal região</button>
            <button onClick={() => { const p = properties[0]; if (p) addAgentContext({ id: `prop-${p.id}`, type: 'Property', label: p.title, data: p }); }} className="w-full text-left text-xs text-text-secondary px-2 py-1.5 rounded hover:bg-elevated/60 flex items-center gap-2"><Building2 className="w-3.5 h-3.5" /> Adicionar principal imóvel</button>
          </div>
        </div>
      </div>
    </>
  );
}

