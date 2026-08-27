import React from 'react';

const BUBBLES = [
  { left: '12%', size: 14, delay: 0, dur: 11 },
  { left: '24%', size: 8, delay: 2.5, dur: 9 },
  { left: '41%', size: 18, delay: 1.2, dur: 13 },
  { left: '58%', size: 10, delay: 4, dur: 10 },
  { left: '73%', size: 12, delay: 0.8, dur: 12 },
  { left: '86%', size: 7, delay: 3, dur: 8 },
];

export default function VoiceBackground() {
  return (
    <div className="absolute inset-0 z-0 overflow-hidden">
      {/* Theme-driven animated base wash. */}
      <div className="voice-theme-gradient absolute inset-0" />

      {/* drifting aurora blobs */}
      <div
        className="absolute -left-32 -top-10 w-[44vw] h-[44vw] rounded-full blur-3xl opacity-60 ab9-float"
        style={{ background: 'radial-gradient(circle, hsl(var(--aqua) / 0.30), transparent 70%)' }}
      />
      <div
        className="absolute -right-24 top-1/4 w-[38vw] h-[38vw] rounded-full blur-3xl opacity-50 ab9-float"
        style={{ background: 'radial-gradient(circle, hsl(var(--positive) / 0.26), transparent 70%)', animationDelay: '-7s' }}
      />
      <div
        className="absolute left-1/4 -bottom-32 w-[40vw] h-[40vw] rounded-full blur-3xl opacity-45 ab9-float"
        style={{ background: 'radial-gradient(circle, hsl(var(--lagoon) / 0.26), transparent 70%)', animationDelay: '-13s' }}
      />

      {/* retained structural layer; grid texture is disabled globally */}
      <div
        className="absolute inset-0 grid-bg opacity-40"
        style={{
          maskImage: 'radial-gradient(circle at 50% 45%, black, transparent 78%)',
          WebkitMaskImage: 'radial-gradient(circle at 50% 45%, black, transparent 78%)',
        }}
      />

      {/* rising bubbles */}
      {BUBBLES.map((b, i) => (
        <span
          key={i}
          className="vb-bubble absolute rounded-full border border-border/70 bg-card/20"
          style={{
            left: b.left,
            bottom: -24,
            width: b.size,
            height: b.size,
            animationDelay: `${b.delay}s`,
            animationDuration: `${b.dur}s`,
          }}
        />
      ))}

      {/* top sheen */}
      <div className="absolute inset-0 aero-sheen opacity-25" />
    </div>
  );
}

