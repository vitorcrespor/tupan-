import React, { useEffect, useRef, useState } from 'react';
import { Orb } from 'orb-ui';
import VoiceBeams from '@/components/tupan/VoiceBeams';
import VoiceToolbar from '@/components/tupan/VoiceToolbar';
import VoiceBackground from '@/components/tupan/VoiceBackground';
import { Ripple } from '@/registry/magicui/ripple';
import { useApp } from '@/lib/AppContext';
import MenuWindow from '@/components/tupan/MenuWindow';
import { loadPersona, buildVoicePrompt } from '@/lib/voicePersona';
import { useSpeech } from '@/lib/useSpeech';
import { sendAgentMessage } from '@/api/agent';
import { apiErrorMessage } from '@/api/client';

export default function VoiceAgent() {
  const persona = loadPersona();
  const { setNavOpen } = useApp();
  const [turns, setTurns] = useState([]);
  const [input, setInput] = useState('');
  const [thinking, setThinking] = useState(false);
  const [requestError, setRequestError] = useState(null);
  const scrollRef = useRef(null);
  const orbRef = useRef(null);

  const ask = async (question, viaVoice = false) => {
    const q = question.trim();
    if (!q || thinking) return;
    setInput('');
    setRequestError(null);
    setTurns((t) => [...t, { role: 'user', text: q }]);
    setThinking(true);
    try {
      const reply = await sendAgentMessage({ message: buildVoicePrompt(persona, q) });
      const text = reply.message.content;
      setTurns((t) => [...t, { role: 'agent', text }]);
      if (viaVoice && persona.speak) speech.speak(text);
    } catch (error) {
      setRequestError(error);
    } finally {
      setThinking(false);
    }
  };

  const speech = useSpeech({ onResult: (text) => ask(text, true), rate: persona.rate });

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [turns, thinking]);

  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get('q');
    if (q) ask(q);
  }, []);

  const orbState = speech.speaking ? 'speaking' : speech.listening ? 'listening' : thinking ? 'thinking' : 'idle';

  return (
    <div className="relative h-screen overflow-hidden bg-background">
      {/* soft aqua ambient filling the whole window */}
      <VoiceBackground />

      {/* central layer — sphere centered on the whole window */}
      <div className="fixed inset-0 z-10 pointer-events-none">
        <Ripple className="opacity-80" />
        <VoiceBeams
          orbRef={orbRef}
          orb={<Orb state={orbState} data-state={orbState} theme="circle" size={320} interactive={false} className="ceres-orb" aria-label="Ceres voice assistant" />}
        />

        {/* small transparent menu button below the sphere + corner options */}
        <button
          type="button"
          onClick={() => setNavOpen(true)}
          className="absolute left-1/2 -translate-x-1/2 z-30 flex items-center gap-1.5 h-7 px-3 rounded-full border border-border/70 bg-card/25 text-text-secondary hover:text-foreground transition-all duration-300 hover:border-brand/50 pointer-events-auto backdrop-blur-md"
          style={{ top: 'calc(50% + 176px)' }}
        >
          <span
            className="w-1.5 h-1.5 rounded-full"
            style={{ background: 'radial-gradient(circle at 34% 28%, hsl(188 88% 76%), hsl(188 78% 54%))', boxShadow: '0 0 6px -1px hsl(188 82% 52% / 0.6)' }}
          />
          <span className="text-[10px] font-mono tracking-[0.2em] uppercase">Menu</span>
        </button>

        {/* transcript kept near the sphere */}
        <div
          ref={scrollRef}
          className="absolute left-1/2 -translate-x-1/2 z-30 w-full max-w-2xl max-h-[16vh] overflow-y-auto px-6 space-y-3 text-center pointer-events-auto"
          style={{ top: 'calc(50% + 248px)' }}
        >
          {turns.map((t, i) => (
            <div key={i} className={t.role === 'user' ? 'text-right' : 'text-left'}>
              <p
                className={`text-sm leading-relaxed ${
                  t.role === 'user' ? 'text-text-secondary' : 'text-foreground'
                }`}
              >
                {t.role === 'agent' && (
                  <span className="mr-1.5 text-[10px] uppercase tracking-widest text-brand align-middle">
                    Ceres ·
                  </span>
                )}
                {t.text}
              </p>
            </div>
          ))}
          {thinking && (
            <div className="flex justify-center gap-1.5 pt-1">
              {[0, 1, 2].map((d) => (
                <span
                  key={d}
                  className="w-1.5 h-1.5 rounded-full bg-brand animate-bounce"
                  style={{ animationDelay: `${d * 120}ms` }}
                />
              ))}
            </div>
          )}
          {requestError && <div role="alert" className="text-xs text-negative">{apiErrorMessage(requestError)}</div>}
        </div>
      </div>

      <MenuWindow />

      {/* sleek transparent toolbar — expands on click */}
      <VoiceToolbar
        input={input}
        setInput={setInput}
        onAsk={() => ask(input)}
        speech={speech}
        thinking={thinking}
      />
    </div>
  );
}

