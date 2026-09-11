import { useCallback, useEffect, useRef, useState } from 'react';

// Thin wrapper over the browser Speech APIs. Fully optional: when the browser
// has no support the page stays usable as a typed conversation.
export function useSpeech({ onResult, rate = 1 }) {
  const [listening, setListening] = useState(false);
  const [speaking, setSpeaking] = useState(false);
  const recRef = useRef(null);
  const cbRef = useRef(onResult);
  cbRef.current = onResult;

  // Browser vendors still expose these constructors outside the standard Window type.
  const speechWindow = typeof window === 'undefined' ? null : /** @type {any} */ (window);
  const SR = speechWindow?.SpeechRecognition || speechWindow?.webkitSpeechRecognition;
  const canListen = !!SR;
  const canSpeak = typeof window !== 'undefined' && 'speechSynthesis' in window;

  useEffect(() => {
    if (!SR) return;
    const rec = new SR();
    rec.lang = 'pt-BR';
    rec.interimResults = false;
    rec.continuous = false;
    rec.onresult = (e) => {
      const text = Array.from(e.results).map((r) => r[0].transcript).join(' ').trim();
      if (text) cbRef.current?.(text);
    };
    rec.onend = () => setListening(false);
    rec.onerror = () => setListening(false);
    recRef.current = rec;
    return () => {
      rec.onresult = null;
      rec.onend = null;
      try { rec.stop(); } catch { /* already stopped */ }
    };
  }, [SR]);

  const toggleListening = useCallback(() => {
    const rec = recRef.current;
    if (!rec) return;
    if (listening) {
      rec.stop();
      setListening(false);
    } else {
      rec.start();
      setListening(true);
    }
  }, [listening]);

  const speak = useCallback(
    (text) => {
      if (!canSpeak || !text) return;
      window.speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.rate = rate;
      u.pitch = 1.05;
      u.onstart = () => setSpeaking(true);
      u.onend = () => setSpeaking(false);
      window.speechSynthesis.speak(u);
    },
    [canSpeak, rate]
  );

  const stopSpeaking = useCallback(() => {
    if (canSpeak) window.speechSynthesis.cancel();
    setSpeaking(false);
  }, [canSpeak]);

  return { listening, speaking, canListen, canSpeak, toggleListening, speak, stopSpeaking };
}