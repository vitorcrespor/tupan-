import React, { useEffect, useRef } from 'react';

/**
 * Soft twinkling starfield + drifting aqua motes for the Ceres voice page.
 * Canvas-based, fixed full-bleed, pointer-events-none, behind all content.
 */
export default function Starfield({ density = 1 }) {
  const ref = useRef(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let raf;
    let w = 0, h = 0, dpr = Math.min(window.devicePixelRatio || 1, 2);

    const resize = () => {
      w = canvas.clientWidth;
      h = canvas.clientHeight;
      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      seed();
    };

    let stars = [];
    let motes = [];

    const seed = () => {
      const count = Math.floor((w * h) / 9000 * density);
      stars = Array.from({ length: count }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        r: Math.random() * 1.1 + 0.3,
        base: Math.random() * 0.5 + 0.25,
        twk: Math.random() * Math.PI * 2,
        spd: Math.random() * 0.9 + 0.3,
        hue: Math.random() < 0.7 ? 188 : 168,
      }));
      motes = Array.from({ length: 14 }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        r: Math.random() * 2.4 + 1.2,
        vx: (Math.random() - 0.5) * 0.12,
        vy: (Math.random() - 0.5) * 0.12,
        a: Math.random() * 0.25 + 0.08,
      }));
    };

    const draw = () => {
      ctx.clearRect(0, 0, w, h);
      const t = performance.now() / 1000;

      // drifting aqua motes (soft bokeh)
      for (const m of motes) {
        m.x += m.vx; m.y += m.vy;
        if (m.x < -10) m.x = w + 10; if (m.x > w + 10) m.x = -10;
        if (m.y < -10) m.y = h + 10; if (m.y > h + 10) m.y = -10;
        const g = ctx.createRadialGradient(m.x, m.y, 0, m.x, m.y, m.r * 6);
        g.addColorStop(0, `hsla(${188 + Math.sin(t * 0.3 + m.x) * 6}, 80%, 70%, ${m.a})`);
        g.addColorStop(1, 'hsla(188, 80%, 70%, 0)');
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(m.x, m.y, m.r * 6, 0, Math.PI * 2);
        ctx.fill();
      }

      // soft radial glow behind the orb so stars pop on the light bg
      const cx = w / 2, cy = h / 2;
      const vg = ctx.createRadialGradient(cx, cy, 0, cx, cy, Math.max(w, h) * 0.5);
      vg.addColorStop(0, 'hsla(196, 60%, 22%, 0.16)');
      vg.addColorStop(0.55, 'hsla(196, 50%, 26%, 0.05)');
      vg.addColorStop(1, 'hsla(196, 50%, 26%, 0)');
      ctx.fillStyle = vg;
      ctx.fillRect(0, 0, w, h);

      // twinkling stars
      for (const s of stars) {
        const tw = s.base + Math.sin(t * s.spd + s.twk) * 0.35;
        const a = Math.max(0.08, tw);
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
        ctx.fillStyle = `hsla(${s.hue}, 80%, 60%, ${a})`;
        ctx.fill();
        // glow halo
        const gg = ctx.createRadialGradient(s.x, s.y, 0, s.x, s.y, s.r * 4);
        gg.addColorStop(0, `hsla(${s.hue}, 85%, 70%, ${a * 0.5})`);
        gg.addColorStop(1, `hsla(${s.hue}, 85%, 70%, 0)`);
        ctx.fillStyle = gg;
        ctx.beginPath();
        ctx.arc(s.x, s.y, s.r * 4, 0, Math.PI * 2);
        ctx.fill();
        // occasional sparkle cross for the brighter ones
        if (s.r > 0.9 && tw > 0.55) {
          ctx.strokeStyle = `hsla(${s.hue}, 85%, 75%, ${a * 0.6})`;
          ctx.lineWidth = 0.6;
          const k = s.r * 3.4;
          ctx.beginPath();
          ctx.moveTo(s.x - k, s.y); ctx.lineTo(s.x + k, s.y);
          ctx.moveTo(s.x, s.y - k); ctx.lineTo(s.x, s.y + k);
          ctx.stroke();
        }
      }

      raf = requestAnimationFrame(draw);
    };

    resize();
    draw();
    window.addEventListener('resize', resize);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', resize);
    };
  }, [density]);

  return (
    <canvas
      ref={ref}
      className="absolute inset-0 w-full h-full pointer-events-none"
      style={{ zIndex: 0 }}
    />
  );
}