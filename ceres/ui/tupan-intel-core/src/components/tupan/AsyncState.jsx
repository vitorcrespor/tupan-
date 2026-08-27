import React from 'react';
import { AlertCircle } from 'lucide-react';
import { apiErrorMessage } from '@/api/client';

export function AsyncLoading({ label = 'Carregando…', className = '' }) {
  return <div className={`flex items-center justify-center text-xs text-text-muted ${className}`}><span className="w-4 h-4 border-2 border-border border-t-brand rounded-full animate-spin mr-2" />{label}</div>;
}

export function AsyncEmpty({ children = 'Nenhum dado disponível para este recorte.', className = '' }) {
  return <div className={`flex items-center justify-center px-6 text-center text-xs text-text-muted ${className}`}>{children}</div>;
}

export function AsyncError({ error, onRetry, className = '' }) {
  return (
    <div role="alert" className={`rounded border border-negative/30 bg-negative/10 p-3 text-xs text-negative ${className}`}>
      <div className="flex items-start gap-2"><AlertCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" /><span>{apiErrorMessage(error)}</span></div>
      {onRetry && <button onClick={onRetry} className="mt-2 text-[10px] font-medium underline underline-offset-2 hover:text-foreground">Tentar novamente</button>}
    </div>
  );
}
