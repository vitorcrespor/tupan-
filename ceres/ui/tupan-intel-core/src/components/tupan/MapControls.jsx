import React from 'react';
import { Box, Mountain } from 'lucide-react';

export default function MapControls({ tilt, setTilt, elevation, setElevation }) {
  return (
    <div className="aero-glass aero-gloss rounded-2xl px-4 py-3 space-y-3 w-56">
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-[10px] uppercase tracking-widest text-text-muted">
          <span className="flex items-center gap-1.5"><Box className="w-3 h-3" /> Inclinação</span>
          <span className="tnum text-text-secondary">{tilt}°</span>
        </div>
        <input
          type="range"
          min="0"
          max="67"
          value={tilt}
          onChange={(e) => setTilt(Number(e.target.value))}
          className="w-full accent-brand"
        />
      </div>
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-[10px] uppercase tracking-widest text-text-muted">
          <span className="flex items-center gap-1.5"><Mountain className="w-3 h-3" /> Extrução</span>
          <span className="tnum text-text-secondary">{elevation}m</span>
        </div>
        <input
          type="range"
          min="200"
          max="4000"
          step="100"
          value={elevation}
          onChange={(e) => setElevation(Number(e.target.value))}
          className="w-full accent-brand"
        />
      </div>
    </div>
  );
}