import React, { useEffect, useRef } from 'react';

/**
 * Orb2D — a soft aqua sphere rendered on a 2D canvas that *simulates* 3D:
 * radial shading, specular highlight, and noise-driven surface blobs that
 * wander like organic undulations. The whole sphere also drifts on smooth
 * pseudo-random noise motion. Lighter than the WebGL OrbModel.
 */
export default function Orb2D({ size = 180, drift = 36, noise = true, className = '' }) {
  const ref = useRef(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const ph = Array.from({ length: 8 }, () => Math.random() * 6.28);
    let raf;
    const R = size * 0.30;
    const glow = size * 0.50;

    const draw = () => {
      const t = performance.now() / 1000;
      ctx.clearRect(0, 0, size, size);

      const nx = Math.sin(t * 0.21 + ph[0]) * 0.58 + Math.sin(t * 0.43 + ph[1]) * 0.42;
      const ny = Math.cos(t * 0.19 + ph[2]) * 0.58 + Math.cos(t * 0.37 + ph[3]) * 0.42;
      const cx = size / 2 + nx * drift;
      const cy = size / 2 + ny * drift;

      // outer glow
      const g0 = ctx.createRadialGradient(cx, cy, R * 0.6, cx, cy, glow);
      g0.addColorStop(0, 'hsla(178, 72%, 55%, 0.30)');
      g0.addColorStop(1, 'hsla(178, 72%, 55%, 0)');
      ctx.fillStyle = g0;
      ctx.beginPath();
      ctx.arc(cx, cy, glow, 0, Math.PI * 2);
      ctx.fill();

      // sphere body
      const g1 = ctx.createRadialGradient(cx - R * 0.3, cy - R * 0.35, R * 0.1, cx, cy, R);
      g1.addColorStop(0, '#e8fbff');
      g1.addColorStop(0.35, '#7fe9ef');
      g1.addColorStop(0.75, '#2fb6c8');
      g1.addColorStop(1, '#1c8a9c');
      ctx.fillStyle = g1;
      ctx.beginPath();
      ctx.arc(cx, cy, R, 0, Math.PI * 2);
      ctx.fill();

      // noise-driven surface blobs (simulated 3D undulations), clipped to sphere
      if (noise) {
        ctx.save();
        ctx.beginPath();
        ctx.arc(cx, cy, R, 0, Math.PI * 2);
        ctx.clip();
        for (let i = 0; i < 4; i++) {
          const a = t * (0.10 + i * 0.04) + ph[i];
          const bx = cx + Math.cos(a) * R * (0.35 + 0.2 * Math.sin(t * 0.13 + ph[i + 1]));
          const by = cy + Math.sin(a * 1.3 + ph[i + 2]) * R * 0.45;
          const br = R * (0.28 + 0.12 * Math.sin(t * 0.2 + ph[i]));
          const bg = ctx.createRadialGradient(bx, by, 0, bx, by, br);
          bg.addColorStop(0, 'rgba(220, 250, 255, 0.55)');
          bg.addColorStop(1, 'rgba(220, 250, 255, 0)');
          ctx.fillStyle = bg;
          ctx.beginPath();
          ctx.arc(bx, by, br, 0, Math.PI * 2);
          ctx.fill();
        }
        ctx.restore();
      }

      // specular highlight
      const g2 = ctx.createRadialGradient(cx - R * 0.34, cy - R * 0.4, 0, cx - R * 0.34, cy - R * 0.4, R * 0.5);
      g2.addColorStop(0, 'rgba(255,255,255,0.85)');
      g2.addColorStop(1, 'rgba(255,255,255,0)');
      ctx.fillStyle = g2;
      ctx.beginPath();
      ctx.arc(cx - R * 0.34, cy - R * 0.4, R * 0.5, 0, Math.PI * 2);
      ctx.fill();

      // soft rim
      ctx.strokeStyle = 'rgba(255,255,255,0.35)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.arc(cx, cy, R - 0.5, 0, Math.PI * 2);
      ctx.stroke();

      raf = requestAnimationFrame(draw);
    };
    draw();

    return () => cancelAnimationFrame(raf);
  }, [size, drift, noise]);

  return <canvas ref={ref} className={className} style={{ width: size, height: size }} />;
}