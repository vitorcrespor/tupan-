import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Mic, MicOff, ArrowUp } from 'lucide-react';

export default function VoiceToolbar({ input, setInput, onAsk, speech, thinking }) {
  const [open, setOpen] = useState(false);
  const canSend = input.trim().length > 0 && !thinking;
  const hasText = input.trim().length > 0;

  return (
    <div className="fixed bottom-7 left-1/2 -translate-x-1/2 z-30 flex flex-col items-center gap-2">
      <AnimatePresence>
        {speech.speaking && (
          <motion.button
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 6 }}
            transition={{ duration: 0.18 }}
            onClick={speech.stopSpeaking}
            className="flex items-center gap-1.5 h-8 px-3.5 rounded-full bg-negative/10 border border-negative/25 text-[11px] text-negative backdrop-blur-md"
          >
            <span className="w-2 h-2 rounded-sm bg-negative" /> Parar
          </motion.button>
        )}
      </AnimatePresence>

      <motion.div
        layout
        className="relative"
        animate={{ width: open ? 560 : 120, height: open ? 52 : 28 }}
        transition={{ type: 'spring', stiffness: 380, damping: 32 }}
      >
        <div
          onMouseEnter={() => setOpen(true)}
          onMouseLeave={() => { if (!hasText) setOpen(false); }}
          onClick={() => setOpen(true)}
          className={`flex items-center rounded-full cursor-text overflow-hidden transition-all duration-300 ${
            open ? 'border border-border/75 backdrop-blur-xl' : 'border border-foreground/15'
          }`}
          style={{
            height: open ? 52 : 28,
            background: open ? 'hsl(var(--card) / 0.82)' : 'transparent',
            boxShadow: open
              ? '0 18px 44px -14px hsl(var(--foreground) / 0.30), inset 0 1px 0 hsl(0 0% 100% / 0.16)'
              : 'none',
          }}
        >
          {/* mic — left, circular accent */}
          <button
            onClick={(e) => { e.stopPropagation(); speech.toggleListening(); }}
            disabled={!speech.canListen}
            title={speech.canListen ? 'Falar com Ceres' : 'Entrada por voz não suportada'}
            className={`w-10 h-10 ml-1.5 shrink-0 rounded-full flex items-center justify-center transition-all duration-200 ${
              open ? 'opacity-100' : 'opacity-0 pointer-events-none'
            } ${
              speech.listening
                ? 'bg-brand/15 text-brand shadow-glow'
                : 'text-brand hover:bg-brand/10 disabled:opacity-40'
            }`}
          >
            {speech.canListen ? <Mic className="w-4 h-4" strokeWidth={1.7} /> : <MicOff className="w-4 h-4" strokeWidth={1.7} />}
          </button>

          {/* input — expands */}
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && onAsk()}
            placeholder="Fale ou digite para o Ceres…"
            className={`flex-1 h-full bg-transparent px-3 text-sm text-foreground outline-none placeholder:text-text-muted transition-opacity duration-200 ${
              open ? 'opacity-100' : 'opacity-0 pointer-events-none'
            }`}
          />

          {/* send — right, circular */}
          <button
            onClick={(e) => { e.stopPropagation(); onAsk(); }}
            disabled={!canSend}
            title="Enviar"
            className={`w-10 h-10 mr-1.5 shrink-0 rounded-full flex items-center justify-center transition-all duration-200 ${
              open ? 'opacity-100' : 'opacity-0 pointer-events-none'
            } ${
              canSend
                ? 'bg-brand text-primary-foreground shadow-glow hover:brightness-105'
                : 'text-text-muted hover:text-text-secondary'
            }`}
          >
            <ArrowUp className="w-4 h-4" strokeWidth={2} />
          </button>
        </div>
      </motion.div>

      {open && !speech.canListen && (
        <p className="text-[10px] text-text-muted tracking-wide">O microfone precisa do Chrome ou Edge — digitar funciona em qualquer lugar.</p>
      )}
    </div>
  );
}
