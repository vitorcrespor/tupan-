import React, { useEffect, useRef, useState } from 'react';
import { Orb } from 'orb-ui';
import { ChevronUp } from 'lucide-react';
import VoiceBeams from '@/components/tupan/VoiceBeams';
import VoiceToolbar from '@/components/tupan/VoiceToolbar';
import VoiceBackground from '@/components/tupan/VoiceBackground';
import VoiceChatHistory from '@/components/tupan/VoiceChatHistory';
import { useApp } from '@/lib/AppContext';
import MenuWindow from '@/components/tupan/MenuWindow';
import { loadPersona, buildVoicePrompt } from '@/lib/voicePersona';
import { useSpeech } from '@/lib/useSpeech';
import { sendAgentMessage } from '@/api/agent';

export default function VoiceAgent() {
  const persona = loadPersona();
  const { setNavOpen, agentContextItems, agentPrefill, setAgentPrefill, agentContextArrival } = useApp();
  const [turns, setTurns] = useState([]);
  const [input, setInput] = useState('');
  const [thinking, setThinking] = useState(false);
  const [requestError, setRequestError] = useState(null);
  const [responsePulse, setResponsePulse] = useState(false);
  const [contextPulse, setContextPulse] = useState(false);
  const [chatCollapsed, setChatCollapsed] = useState(false);
  const orbRef = useRef(null);
  const responsePulseTimerRef = useRef(null);
  const contextPulseTimerRef = useRef(null);
  const seenContextArrivalRef = useRef(null);

  const ask = async (question, viaVoice = false, contextItems = agentContextItems) => {
    const q = question.trim();
    if (!q || thinking) return;
    setInput('');
    setChatCollapsed(false);
    setRequestError(null);
    setTurns((turns) => [...turns, { role: 'user', text: q }]);
    setThinking(true);
    try {
      const reply = await sendAgentMessage({ message: buildVoicePrompt(persona, q), contextItems });
      const text = reply.message.content;
      setTurns((turns) => [...turns, { role: 'agent', text }]);
      setChatCollapsed(false);
      setResponsePulse(true);
      window.clearTimeout(responsePulseTimerRef.current);
      responsePulseTimerRef.current = window.setTimeout(() => setResponsePulse(false), 760);
      if (viaVoice && persona.speak) speech.speak(text);
    } catch (error) {
      setChatCollapsed(false);
      setRequestError(error);
    } finally {
      setThinking(false);
    }
  };

  const speech = useSpeech({ onResult: (text) => ask(text, true), rate: persona.rate });
  const chatActive = turns.length > 0 || thinking || Boolean(requestError);
  const chatVisible = chatActive && !chatCollapsed;

  useEffect(() => {
    const question = new URLSearchParams(window.location.search).get('q');
    if (question) ask(question);
  }, []);

  useEffect(() => {
    if (!agentPrefill) return;
    const prompt = agentPrefill;
    setAgentPrefill('');
    ask(prompt, false, agentContextItems);
  }, [agentPrefill]);

  useEffect(() => {
    if (!agentContextArrival || agentContextArrival.source !== 'insight-tray' || seenContextArrivalRef.current === agentContextArrival.id) return;
    seenContextArrivalRef.current = agentContextArrival.id;
    setContextPulse(true);
    window.clearTimeout(contextPulseTimerRef.current);
    contextPulseTimerRef.current = window.setTimeout(() => setContextPulse(false), 920);
  }, [agentContextArrival]);

  useEffect(() => () => {
    window.clearTimeout(responsePulseTimerRef.current);
    window.clearTimeout(contextPulseTimerRef.current);
  }, []);

  const orbState = speech.speaking ? 'speaking' : speech.listening ? 'listening' : thinking ? 'thinking' : 'idle';


  return (
    <div className="relative h-screen overflow-hidden bg-background">
      <VoiceBackground />
      <div className="fixed inset-0 z-10 pointer-events-none">
        <VoiceBeams
          orbRef={orbRef}
          dismissed={chatVisible}
          conversationActive={chatVisible}
          responding={thinking || speech.speaking || responsePulse}
          contextArrival={contextPulse}
          orb={<Orb state={orbState} data-state={orbState} theme="circle" size={320} disabled className="ceres-orb" aria-label="Ceres voice assistant" />}
        />
        <button type="button" onClick={() => setNavOpen(true)} aria-label="Abrir menu" className="voice-menu-toggle voice-menu-toggle--conversation absolute z-30 flex items-center gap-1.5 h-7 px-3 rounded-full border border-border/70 bg-card/25 text-text-secondary hover:text-foreground hover:border-brand/50 pointer-events-auto backdrop-blur-md">
          <span className="w-1.5 h-1.5 rounded-full" style={{ background: 'radial-gradient(circle at 34% 28%, hsl(188 88% 76%), hsl(188 78% 54%))', boxShadow: '0 0 6px -1px hsl(188 82% 52% / 0.6)' }} />
          <span className="text-[10px] font-mono tracking-[0.2em] uppercase">Menu</span>
        </button>
        <div className={`voice-chat-shell ${chatActive ? 'voice-chat-shell--active' : ''} ${chatCollapsed ? 'voice-chat-shell--collapsed' : ''}`}>
          <VoiceChatHistory turns={turns} thinking={thinking} error={requestError} visible={chatVisible} />
          {chatActive && !chatCollapsed && (
            <button
              type="button"
              aria-controls="voice-chat-history"
              aria-expanded="true"
              aria-label="Recolher conversa"
              onClick={() => setChatCollapsed(true)}
              className="voice-chat-collapse-toggle pointer-events-auto"
            >
              <ChevronUp className="h-3 w-3" strokeWidth={1.75} aria-hidden="true" />
            </button>
          )}
        </div>
      </div>
      <MenuWindow />
      <VoiceToolbar input={input} setInput={setInput} onAsk={() => ask(input)} speech={speech} thinking={thinking} />
    </div>
  );
}
