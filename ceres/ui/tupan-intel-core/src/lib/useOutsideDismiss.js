import { useEffect, useRef } from 'react';

/**
 * Closes a transient, button-anchored surface when focus moves outside it.
 * Capture-phase pointer handling keeps the dismissal reliable even when
 * interactive dashboard content stops bubbling events.
 */
/**
 * @param {React.RefObject<HTMLElement | null>} containerRef
 * @param {boolean} open
 * @param {() => void} onDismiss
 * @param {{ignoreSelector?: string}} [options]
 */
export default function useOutsideDismiss(containerRef, open, onDismiss, options = {}) {
  const { ignoreSelector } = options;
  const dismissRef = useRef(onDismiss);

  useEffect(() => {
    dismissRef.current = onDismiss;
  }, [onDismiss]);

  useEffect(() => {
    if (!open) return undefined;

    const shouldIgnore = (event) => Boolean(
      ignoreSelector && event.target?.closest?.(ignoreSelector),
    );
    const dismissIfOutside = (event) => {
      const container = containerRef.current;
      if (!shouldIgnore(event) && container && !container.contains(event.target)) dismissRef.current();
    };
    let pointerHandled = false;
    const handlePointerDown = (event) => {
      pointerHandled = true;
      dismissIfOutside(event);
    };
    const handleClick = (event) => {
      if (pointerHandled) {
        pointerHandled = false;
        return;
      }
      dismissIfOutside(event);
    };
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') dismissRef.current();
    };

    document.addEventListener('pointerdown', handlePointerDown, true);
    document.addEventListener('click', handleClick, true);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('pointerdown', handlePointerDown, true);
      document.removeEventListener('click', handleClick, true);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [containerRef, ignoreSelector, open]);
}
