import React, { useEffect, useRef } from 'react';

// Pseudo-random noise field (no deps): layered sines seeded per point.
const noise = (x, y, z, t, seed) =>
  Math.sin(x * 2.1 + t + seed) * 0.5 +
  Math.sin(y * 1.7 - t * 0.8 + seed * 1.3) * 0.3 +
  Math.sin(z * 2.9 + t * 0.6) * 0.2 +
  Math.sin((x + y + z) * 4.3 - t * 1.4) * 0.15;

// Fibonacci lattice → evenly scattered points on a unit sphere, each with its own seed.
const makePoints = (count) => {
  const golden = Math.PI * (3 - Math.sqrt(5));
  const pts = [];
  for (let i = 0; i < count; i++) {
    const y = 1 - (i / (count - 1)) * 2;
    const r = Math.sqrt(Math.max(0, 1 - y * y));
    const theta = golden * i;
    pts.push({
      x: Math.cos(theta) * r,
      y,
      z: Math.sin(theta) * r,
      seed: Math.random() * Math.PI * 2,
      jitter: 0.85 + Math.random() * 0.3,
    });
  }
  return pts;
};

/**
 * Flat 2D canvas render of a projected point sphere — the depth illusion comes
 * purely from perspective scaling, dot size and alpha. No WebGL, no 3D engine.
 */
export default function HologramSphere({ size = 420, points = 3400 }) {
  const canvasRef = useRef(null);
  const dataRef = useRef(makePoints(points));

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.scale(dpr, dpr);

    const cx = size / 2;
    const cy = size / 2;
    const base = size * 0.33;
    const focal = 3.2;
    let raf;
    let start = performance.now();

    const frame = (now) => {
      const t = (now - start) / 1000;
      ctx.clearRect(0, 0, size, size);

      const ry = t * 0.35;
      const rx = Math.sin(t * 0.25) * 0.45;
      const cosY = Math.cos(ry), sinY = Math.sin(ry);
      const cosX = Math.cos(rx), sinX = Math.sin(rx);

      const projected = [];
      for (const p of dataRef.current) {
        // Oscillating radius driven by the noise field.
        const n = noise(p.x, p.y, p.z, t * 1.1, p.seed);
        const rad = 1 + n * 0.14 * p.jitter;

        let x = p.x * rad, y = p.y * rad, z = p.z * rad;
        // rotate Y then X
        let x1 = x * cosY - z * sinY;
        let z1 = x * sinY + z * cosY;
        let y1 = y * cosX - z1 * sinX;
        let z2 = y * sinX + z1 * cosX;

        const scale = focal / (focal - z2);
        // Back hemisphere is hidden by the body — an opaque surface, not a cloud.
        if (z2 < -0.02) continue;
        projected.push({
          sx: cx + x1 * base * scale,
          sy: cy + y1 * base * scale,
          depth: (z2 + 1) / 2,
          nx: x1 / rad,
          ny: y1 / rad,
          nz: z2 / rad,
          n,
        });
      }

      // Opaque body, lit from the upper-left with a soft terminator toward the
      // lower-right — this is what reads as "solid".
      const R = base * 1.02;
      const body = ctx.createRadialGradient(cx - R * 0.34, cy - R * 0.4, R * 0.06, cx, cy, R);
      body.addColorStop(0, 'hsl(178, 72%, 62%)');
      body.addColorStop(0.45, 'hsl(180, 62%, 40%)');
      body.addColorStop(0.8, 'hsl(192, 62%, 22%)');
      body.addColorStop(1, 'hsl(198, 58%, 14%)');
      ctx.beginPath();
      ctx.arc(cx, cy, R, 0, Math.PI * 2);
      ctx.fillStyle = body;
      ctx.fill();

      projected.sort((a, b) => a.depth - b.depth);

      const Lx = -0.52, Ly = -0.6, Lz = 0.6;
      for (const q of projected) {
        const d = q.depth;
        const r = 0.7 + d * 1.9 + Math.max(0, q.n) * 0.8;
        const lambert = Math.max(0, q.nx * Lx + q.ny * Ly + q.nz * Lz);
        const lit = 0.12 + lambert * 0.95;

        // Each bump casts a short shadow away from the light, toward the dark side.
        ctx.beginPath();
        ctx.arc(q.sx - Lx * r * 1.6, q.sy - Ly * r * 1.6, r * 1.2, 0, Math.PI * 2);
        ctx.fillStyle = `hsla(198, 60%, 12%, ${0.14 + (1 - lambert) * 0.22})`;
        ctx.fill();

        const hue = 168 + d * 26 + q.n * 12;
        ctx.beginPath();
        ctx.arc(q.sx, q.sy, r, 0, Math.PI * 2);
        ctx.fillStyle = `hsla(${hue}, ${70 + lambert * 22}%, ${20 + lit * 58}%, ${0.55 + lambert * 0.45})`;
        ctx.fill();
      }

      // Rim light + specular highlight to close the volume.
      const rim = ctx.createRadialGradient(cx, cy, R * 0.82, cx, cy, R);
      rim.addColorStop(0, 'hsla(190, 90%, 80%, 0)');
      rim.addColorStop(1, 'hsla(186, 95%, 82%, 0.55)');
      ctx.beginPath();
      ctx.arc(cx, cy, R, 0, Math.PI * 2);
      ctx.fillStyle = rim;
      ctx.fill();

      const spec = ctx.createRadialGradient(cx - R * 0.36, cy - R * 0.42, 0, cx - R * 0.36, cy - R * 0.42, R * 0.55);
      spec.addColorStop(0, 'hsla(0, 0%, 100%, 0.4)');
      spec.addColorStop(1, 'hsla(0, 0%, 100%, 0)');
      ctx.save();
      ctx.beginPath();
      ctx.arc(cx, cy, R, 0, Math.PI * 2);
      ctx.clip();
      ctx.fillStyle = spec;
      ctx.fillRect(0, 0, size, size);
      ctx.restore();

      // Soft scanline shimmer for the hologram feel.
      ctx.save();
      ctx.beginPath();
      ctx.arc(cx, cy, R, 0, Math.PI * 2);
      ctx.clip();
      ctx.globalAlpha = 0.07;
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 1;
      const off = (t * 40) % 8;
      for (let y = -off; y < size; y += 8) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(size, y);
        ctx.stroke();
      }
      ctx.globalAlpha = 1;
      ctx.restore();

      raf = requestAnimationFrame(frame);
    };
    raf = requestAnimationFrame(frame);
    return () => cancelAnimationFrame(raf);
  }, [size]);

  return (
    <div className="relative flex items-center justify-center" style={{ width: size, height: size }}>
      <div
        className="absolute rounded-full blur-3xl"
        style={{
          width: size * 0.8,
          height: size * 0.8,
          background: 'radial-gradient(circle, hsla(174,80%,55%,0.35), hsla(196,80%,60%,0.12) 60%, transparent 70%)',
        }}
      />
      <canvas ref={canvasRef} style={{ width: size, height: size }} className="relative" />
    </div>
  );
}