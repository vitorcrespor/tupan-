import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import './MetricKnob.css';

const PANEL_HEIGHT = 318;
const MIN_PANEL_HEIGHT = 144;
const VIEWPORT_GUTTER = 16;

export default function MetricKnob({ value, onChange, metrics = [], className }) {
  const [open, setOpen] = useState(false);
  const [placement, setPlacement] = useState({ direction: 'up', maxHeight: PANEL_HEIGHT });
  const ref = useRef(null);

  useEffect(() => {
    const handleOutsideClick = (event) => {
      if (ref.current && !ref.current.contains(event.target)) setOpen(false);
    };
    document.addEventListener('pointerdown', handleOutsideClick);
    return () => document.removeEventListener('pointerdown', handleOutsideClick);
  }, []);

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
        maxHeight: Math.max(MIN_PANEL_HEIGHT, Math.min(PANEL_HEIGHT, Math.floor(availableSpace))),
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
      className={`metric-knob ${open ? 'metric-knob--open' : ''} ${placementClass} ${className || ''}`}
      style={open ? { '--metric-knob-open-height': `${placement.maxHeight}px` } : undefined}
    >
      <button
        className="metric-knob__handle"
        type="button"
        onClick={() => setOpen((current) => !current)}
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
              <button key={id} type="button" className={`metric-knob__option ${active ? 'metric-knob__option--active' : ''}`} onClick={() => { onChange?.(metric); setOpen(false); }}>
                <span>{label}</span>{active && <span className="metric-knob__dot" />}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}