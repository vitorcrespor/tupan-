import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import useOutsideDismiss from '@/lib/useOutsideDismiss';
import './MetricKnob.css';

const PANEL_HEIGHT = 318;
const MIN_PANEL_HEIGHT = 96;
const VIEWPORT_GUTTER = 16;

export default function MetricKnob({ value, onChange, metrics = [], className }) {
  const [open, setOpen] = useState(false);
  const [rendered, setRendered] = useState(false);
  const [placement, setPlacement] = useState({ direction: 'up', maxHeight: PANEL_HEIGHT });
  const ref = useRef(null);
  const closeTimerRef = useRef(null);

  const openSelector = () => {
    window.clearTimeout(closeTimerRef.current);
    setRendered(true);
    setOpen(true);
  };
  const closeSelector = () => {
    if (!rendered) return;
    setOpen(false);
    window.clearTimeout(closeTimerRef.current);
    closeTimerRef.current = window.setTimeout(() => setRendered(false), 240);
  };

  useOutsideDismiss(ref, open, closeSelector);

  useEffect(() => () => window.clearTimeout(closeTimerRef.current), []);

  useLayoutEffect(() => {
    if (!open) return undefined;

    const updatePlacement = () => {
      const host = ref.current?.parentElement;
      if (!host) return;

      const bounds = host.getBoundingClientRect();
      const spaceAbove = Math.max(0, bounds.bottom - VIEWPORT_GUTTER);
      const spaceBelow = Math.max(0, window.innerHeight - bounds.bottom - VIEWPORT_GUTTER);
      const direction = spaceAbove >= PANEL_HEIGHT || spaceAbove >= spaceBelow ? 'up' : 'down';
      const availableSpace = direction === 'up' ? spaceAbove : spaceBelow;

      setPlacement({
        direction,
        maxHeight: Math.min(PANEL_HEIGHT, availableSpace >= MIN_PANEL_HEIGHT ? Math.floor(availableSpace) : Math.max(64, Math.floor(availableSpace))),
      });
    };

    updatePlacement();
    window.addEventListener('resize', updatePlacement);
    window.addEventListener('scroll', updatePlacement, true);
    return () => {
      window.removeEventListener('resize', updatePlacement);
      window.removeEventListener('scroll', updatePlacement, true);
    };
  }, [open]);

  if (!metrics.length) return null;

  const placementClass = placement.direction === 'down' ? 'metric-knob--opens-down' : '';

  return (
    <div
      ref={ref}
      onClick={(event) => event.stopPropagation()}
      className={`metric-knob ${rendered ? 'metric-knob--active' : ''} ${open ? 'metric-knob--open' : rendered ? 'metric-knob--closing' : ''} ${placementClass} ${className || ''}`}
      style={rendered ? {
        '--metric-knob-open-height': `${placement.maxHeight}px`,
        '--metric-knob-closed-scale-y': `${Math.min(1, 12 / placement.maxHeight)}`,
      } : undefined}
    >
      <button
        className="metric-knob__handle"
        type="button"
        onClick={() => (open ? closeSelector() : openSelector())}
        aria-label={open ? 'Fechar seletor de métricas' : 'Abrir seletor de métricas'}
        aria-expanded={open}
      />
      <div className="metric-knob__content">
        <div className="metric-knob__title">Selecionar métrica</div>
        <div className="metric-knob__options">
          {metrics.map((metric) => {
            const id = typeof metric === 'string' ? metric : metric.id;
            const label = typeof metric === 'string' ? metric : metric.label;
            const active = id === value;
            return (
              <button key={id} type="button" className={`metric-knob__option ${active ? 'metric-knob__option--active' : ''}`} onClick={() => { onChange?.(metric); closeSelector(); }}>
                <span>{label}</span>{active && <span className="metric-knob__dot" />}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
