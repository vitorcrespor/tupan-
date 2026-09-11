import React from 'react';
import { AlertCircle } from 'lucide-react';
import { apiErrorMessage } from '@/api/client';

export function AsyncLoading({ label = 'Carregando…', className = '' }) {
  return <div role="status" aria-live="polite" className={`flex items-center justify-center gap-2 text-xs leading-relaxed text-text-secondary ${className}`}><span aria-hidden="true" className="w-4 h-4 shrink-0 border-2 border-border border-t-brand rounded-full animate-spin motion-reduce:animate-none" />{label}</div>;
}

export function AsyncEmpty({ children = 'Nenhum dado disponível para este recorte.', className = '' }) {
  return <div className={`flex items-center justify-center px-4 text-center text-sm leading-relaxed text-text-secondary ${className}`}>{children}</div>;
}

export function AsyncError({ error, onRetry = undefined, className = '' }) {
  return (
    <div role="alert" className={`rounded-[var(--radius-control)] border border-negative/25 bg-negative/5 p-3 text-xs leading-relaxed text-negative ${className}`}>
      <div className="flex items-start gap-2"><AlertCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" /><span>{apiErrorMessage(error)}</span></div>
      {onRetry && <button type="button" onClick={onRetry} className="mt-2 min-h-8 text-xs font-medium underline underline-offset-4 hover:text-foreground focus-visible:outline focus-visible:outline-2 focus-visible:outline-ring">Tentar novamente</button>}
    </div>
  );
}
