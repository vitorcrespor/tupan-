import AiEvidence from './AiEvidence';
import React, { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Sparkles, RefreshCw } from 'lucide-react';
import { sendAgentMessage } from '@/api/agent';
import { AsyncError, AsyncLoading } from './AsyncState';

export default function AiBrief({ prompt, title = 'Resumo de mercado com IA', className, portfolioId = null }) {
  const [response, setResponse] = useState(null);
  const [text, setText] = useState('');
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState(null);

  const run = async (signal) => {
    if (!portfolioId) { setStatus('unavailable'); setText('Selecione um portfólio com dados autorizados para obter uma interpretação.'); return; }
    setStatus('loading');
    setError(null);
    try {
      const res = await sendAgentMessage({ message: `Escreva um resumo de mercado conciso, baseado apenas nos dados a seguir. Não invente números; termine com uma recomendação acionável.\n\n${prompt}`, signal, contextItems: [{type: 'Portfolio', data: {id: portfolioId}}] });
      if (signal?.aborted) return;
      setText(res.message.content);
      setResponse(res);
      setStatus('success');
    } catch (e) {
      if (signal?.aborted) return;
      setError(e);
      setStatus('error');
    }
  };

  useEffect(() => {
    const controller = new AbortController();
    run(controller.signal);
    return () => {
      controller.abort();
    };
  }, [prompt, portfolioId]);

  return (
    <div className={className}>
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <div className="flex min-w-0 items-center gap-2">
          <Sparkles className="w-3.5 h-3.5 text-positive" />
          <h3 className="text-sm font-semibold text-foreground">{title}</h3>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-text-secondary">Interpretação IA</span>
          <button type="button" onClick={() => run()} aria-label="Atualizar comentário da Ceres" title="Atualizar comentário" className="icon-control h-8 w-8 text-text-muted hover:text-foreground" disabled={status === 'loading'}>
            <RefreshCw className={`w-3 h-3 ${status === 'loading' ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>
      {status === 'idle' || status === 'loading' ? <AsyncLoading className="min-h-12" label="Gerando resumo…" /> : null}
      {status === 'error' ? <AsyncError error={error} onRetry={() => run()} /> : null}
      {status === 'unavailable' && <p className="text-xs text-text-muted">{text}</p>}
      {status === 'success' ? (
        <div className="prose prose-sm max-w-none text-text-secondary [&_p]:my-1.5 [&_li]:my-0.5 [&_strong]:text-foreground [&_h4]:text-foreground [&_h4]:text-xs [&_h4]:mt-2">
          <ReactMarkdown>{text}</ReactMarkdown>
          <AiEvidence response={response} />
        </div>
      ) : null}
    </div>
  );
}

