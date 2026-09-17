import React, { useRef, useState } from 'react';
import { BarChart3, ChevronRight, GripVertical, Send, X } from 'lucide-react';
import { useApp } from '@/lib/AppContext';
import useOutsideDismiss from '@/lib/useOutsideDismiss';

export default function InsightTray() {
  const { savedInsights, removeSavedInsight, clearSavedInsights, sendToAgent } = useApp();
  const [open, setOpen] = useState(true);
  const trayRef = useRef(null);

  useOutsideDismiss(trayRef, open, () => setOpen(false));

  if (!savedInsights.length) return null;

  const handoff = () => {
    sendToAgent(
      savedInsights,
      'Use the selected dashboard indicators as authorized evidence. Explain the most relevant relationships, evidence, and recommended next actions.',
      'insight-tray'
    );
  };

  return (
    <aside
      ref={trayRef}
      className={`surface-popover absolute bottom-4 right-4 z-50 w-[290px] overflow-hidden rounded-2xl transition-[transform,border-color,box-shadow] duration-300 ${open ? 'translate-x-0' : 'translate-x-[262px]'}`}
      style={{ transitionTimingFunction: 'cubic-bezier(0.22, 1, 0.36, 1)' }}
    >
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className={`absolute top-2 z-10 grid h-7 w-7 place-items-center rounded-full text-text-muted transition-colors hover:bg-elevated hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/60 ${open ? 'right-2' : 'left-2'}`}
        aria-label={open ? 'Recolher seleção' : 'Abrir seleção'}
        aria-expanded={open}
      >
        <ChevronRight className={`h-4 w-4 transition-transform ${open ? 'rotate-0' : 'rotate-180'}`} />
      </button>
      <div className={`transition-opacity duration-200 ${open ? 'opacity-100' : 'pointer-events-none opacity-0'}`} aria-hidden={!open}>
        <div className="border-b border-border/75 px-4 py-3 pr-10">
          <div className="flex items-center gap-2">
            <span className="grid h-7 w-7 place-items-center rounded-full border border-brand/25 bg-brand/10 text-brand"><BarChart3 className="h-3.5 w-3.5" /></span>
            <div>
              <div className="text-xs font-semibold text-foreground">Painel de contexto</div>
              <p className="text-[10px] text-text-muted">Arraste para o chat da Ceres</p>
            </div>
          </div>
        </div>
        <div className="max-h-56 space-y-1.5 overflow-y-auto p-2">
          {savedInsights.map((item) => (
            <div
              key={item.id}
              draggable
              onDragStart={(event) => {
                event.dataTransfer.effectAllowed = 'copy';
                event.dataTransfer.setData('application/x-ceres-context', JSON.stringify(item));
              }}
              className="group flex cursor-grab items-center gap-2 rounded-xl border border-border/65 bg-elevated/45 px-2.5 py-2 active:cursor-grabbing"
            >
              <GripVertical className="h-3.5 w-3.5 shrink-0 text-text-muted" />
              <div className="min-w-0 flex-1">
                <div className="truncate text-[11px] font-medium text-foreground">{item.label}</div>
                <div className="text-[9px] uppercase tracking-wide text-text-muted">{item.type}</div>
              </div>
              <button onClick={() => removeSavedInsight(item.id)} className="grid h-5 w-5 place-items-center rounded text-text-muted opacity-0 transition-opacity hover:bg-negative/10 hover:text-negative group-hover:opacity-100" aria-label={`Remover ${item.label}`}><X className="h-3 w-3" /></button>
            </div>
          ))}
        </div>
        <div className="flex gap-2 border-t border-border/75 p-2.5">
          <button onClick={clearSavedInsights} className="h-8 rounded-lg px-2 text-[10px] font-medium text-text-muted hover:bg-elevated hover:text-negative">Limpar</button>
          <button onClick={handoff} className="flex h-8 flex-1 items-center justify-center gap-1.5 rounded-lg bg-brand text-[11px] font-medium text-brand-foreground transition-colors hover:bg-brand/90"><Send className="h-3.5 w-3.5" /> Usar na Ceres</button>
        </div>
      </div>
    </aside>
  );
}
