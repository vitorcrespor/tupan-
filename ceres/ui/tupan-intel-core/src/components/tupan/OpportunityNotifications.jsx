import React, {useEffect, useRef, useState} from 'react';
import {Bell, Sparkles} from 'lucide-react';
import useOutsideDismiss from '@/lib/useOutsideDismiss';

// No notification producer/feed exists yet. A price-gap list is not an AI alert.
export default function OpportunityNotifications() {
  const [open, setOpen] = useState(false);
  const [rendered, setRendered] = useState(false);
  const containerRef = useRef(null);
  const closeTimerRef = useRef(null);
  const openPanel = () => {
    window.clearTimeout(closeTimerRef.current);
    setRendered(true);
    setOpen(true);
  };
  const closePanel = () => {
    if (!rendered) return;
    setOpen(false);
    window.clearTimeout(closeTimerRef.current);
    closeTimerRef.current = window.setTimeout(() => setRendered(false), 180);
  };

  useOutsideDismiss(containerRef, open, closePanel);

  useEffect(() => () => window.clearTimeout(closeTimerRef.current), []);


  return <div ref={containerRef} className="notification-anchor relative">
    <button type="button" onClick={() => open ? closePanel() : openPanel()} aria-label="Abrir oportunidades da Ceres" aria-expanded={open}
      className="icon-control relative flex h-8 w-8 items-center justify-center text-text-secondary hover:text-foreground"><Bell className="h-4 w-4" /></button>
    {rendered && <aside className={`surface-popover anchored-popover ${open ? 'anchored-popover--enter' : 'anchored-popover--exit'} absolute right-0 top-10 z-50 w-[360px] max-w-[calc(100vw-2rem)] overflow-hidden rounded-[22px]`}>
      <div className="border-b border-border/65 px-4 py-3.5 flex items-center gap-2"><Sparkles className="h-4 w-4 text-brand" /><h2 className="text-sm font-semibold">Notificações da Ceres</h2></div>
      <p role="status" className="p-5 text-xs leading-relaxed text-text-secondary">O monitor de oportunidades ainda não está disponível. Diferenças entre pedido e estimativa podem ser consultadas no portfólio; elas não são alertas gerados pela IA.</p>
    </aside>}
  </div>;
}

