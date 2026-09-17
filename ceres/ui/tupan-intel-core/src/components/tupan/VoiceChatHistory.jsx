import AiEvidence from './AiEvidence';
import React, { useEffect, useLayoutEffect, useRef } from 'react';
import { ScrollShadow } from '@/components/ui/heroui-scroll-shadow';
import { apiErrorMessage } from '@/api/client';

/**
 * The scroll viewport stays in normal block flow. Bottom alignment belongs to
 * its inner content so overflowing messages remain reachable by native scroll.
 *
 * @param {{
 *   turns: Array<{role: string, text: string, response?: object}>,
 *   thinking: boolean,
 *   error: unknown,
 *   visible: boolean,
 * }} props
 */
export default function VoiceChatHistory({ turns, thinking, error, visible }) {
  const viewportRef = useRef(null);
  const contentRef = useRef(null);
  const followingLatest = useRef(true);
  const readingPosition = useRef(0);

  useEffect(() => {
    if (!visible) return;
    const viewport = viewportRef.current;
    const content = contentRef.current;
    if (!viewport || !content) return;

    const showLatest = () => {
      if (followingLatest.current) viewport.scrollTop = viewport.scrollHeight;
    };
    const resizeObserver = new ResizeObserver(showLatest);
    resizeObserver.observe(viewport);
    resizeObserver.observe(content);
    showLatest();
    return () => resizeObserver.disconnect();
  }, [visible]);

  useLayoutEffect(() => {
    if (!visible) return;
    // A question sent by this user intentionally returns to the conversation end.
    if (turns.at(-1)?.role === 'user') followingLatest.current = true;
    const viewport = viewportRef.current;
    if (!viewport) return;
    if (followingLatest.current) viewport.scrollTo({ top: viewport.scrollHeight });
    else viewport.scrollTop = readingPosition.current;
  }, [turns, error, visible]);

  return (
    <div className="voice-chat-frame">
      <ScrollShadow
        ref={viewportRef}
        id="voice-chat-history"
        role="region"
        aria-label="Conversa com a Ceres"
        aria-hidden={!visible || undefined}
        tabIndex={visible ? 0 : -1}
        orientation="vertical"
        visibility="top"
        size={112}
        className="voice-chat-stage"
        onScroll={(event) => {
          const viewport = event.currentTarget;
          readingPosition.current = viewport.scrollTop;
          followingLatest.current = viewport.scrollHeight - viewport.clientHeight - viewport.scrollTop < 32;
        }}
      >
        <div ref={contentRef} className="voice-chat-content">
          {turns.map((turn, index) => (
            <div key={index} className={`voice-chat-message ${turn.role === 'user' ? 'text-right' : 'text-left'}`}>
              <p className={`text-sm leading-relaxed ${turn.role === 'user' ? 'text-text-secondary' : 'text-foreground'}`}>
                {turn.role === 'agent' && <span className="mr-1.5 text-[10px] uppercase tracking-widest text-brand align-middle">Ceres ·</span>}
                {turn.text}
              </p>
              {turn.response && <AiEvidence response={turn.response} />}
            </div>
          ))}
          {error && <div role="alert" className="voice-chat-message text-xs text-negative">{apiErrorMessage(error)}</div>}
          {thinking && <span role="status" aria-live="polite" className="sr-only">Ceres está processando sua mensagem.</span>}
        </div>
      </ScrollShadow>
      <div className="voice-chat-edge-blur" aria-hidden="true" />
    </div>
  );
}
