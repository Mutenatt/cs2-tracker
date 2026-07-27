import { useEffect, useRef } from "react";

// Escena portada de un proyecto de Claude Design ("Desert Background"):
// cielo con resolana + bruma de calor, tres capas de dunas con ruido
// procedural (grano de arena + estrías talladas por viento), velos de
// arena a la deriva y partículas de polvo flotando. Todo dibujado por
// frame con Canvas2D -- no hay imagen ni video de por medio.
//
// El diseño original estaba pensado para llenar toda la pantalla; acá se
// reescala (via REF_W/REF_H) para que el grano/las estrías/las partículas
// se vean proporcionalmente finas en una card chica en vez de gigantes.

interface Dune {
  baseY: number;
  amp: number;
  freqs: [number, number, number];
  seed: number;
  top: string;
  mid: string;
  bottom: string;
}

interface Particle {
  x: number;
  y: number;
  size: number;
  vx: number;
  vy: number;
  alpha: number;
  wob: number;
}

const REF_W = 1280;
const REF_H = 720;

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function rand(seed: number) {
  const x = Math.sin(seed * 12.9898) * 43758.5453;
  return x - Math.floor(x);
}

function duneHeights(segs: number, amp: number, freqs: [number, number, number], seedOffset: number) {
  const arr = new Float32Array(segs + 1);
  for (let i = 0; i <= segs; i++) {
    const x = i / segs;
    let v = 0;
    v += Math.sin(x * Math.PI * freqs[0] + seedOffset) * amp;
    v += Math.sin(x * Math.PI * freqs[1] + seedOffset * 1.7) * amp * 0.45;
    v += Math.abs(Math.sin(x * Math.PI * freqs[2] + seedOffset * 2.3)) * amp * 0.35;
    v += (rand(i * 0.13 + seedOffset) - 0.5) * amp * 0.15;
    arr[i] = v;
  }
  return arr;
}

function buildGrain(size: number): HTMLCanvasElement {
  const g = document.createElement("canvas");
  g.width = size;
  g.height = size;
  const gc = g.getContext("2d")!;
  const img = gc.createImageData(size, size);
  for (let i = 0; i < img.data.length; i += 4) {
    const v = 128 + (Math.random() - 0.5) * 90;
    img.data[i] = v;
    img.data[i + 1] = v * 0.9;
    img.data[i + 2] = v * 0.75;
    img.data[i + 3] = 40 + Math.random() * 40;
  }
  gc.putImageData(img, 0, 0);
  return g;
}

function buildVeil(w: number, h: number): HTMLCanvasElement {
  const v = document.createElement("canvas");
  v.width = w;
  v.height = h;
  const vc = v.getContext("2d")!;
  for (let i = 0; i < 220; i++) {
    const y = Math.random() * h;
    const len = (80 + Math.random() * 260) * (w / 1400);
    const x = Math.random() * w;
    const alpha = 0.02 + Math.random() * 0.05;
    const thick = (1 + Math.random() * 3) * (w / 1400);
    const grad = vc.createLinearGradient(x, y, x + len, y);
    grad.addColorStop(0, "rgba(230,200,150,0)");
    grad.addColorStop(0.5, `rgba(235,210,170,${alpha})`);
    grad.addColorStop(1, "rgba(230,200,150,0)");
    vc.strokeStyle = grad;
    vc.lineWidth = thick;
    vc.beginPath();
    vc.moveTo(x, y);
    vc.lineTo(x + len, y + (Math.random() - 0.5) * 12);
    vc.stroke();
  }
  return v;
}

function spawnParticle(x: number, h: number, dpr: number, scale: number): Particle {
  const depth = Math.random();
  return {
    x,
    y: h * (0.35 + Math.random() * 0.6),
    size: (0.55 + depth * 1.1) * dpr * scale,
    vx: (0.15 + depth * 0.5) * dpr,
    vy: (Math.random() - 0.5) * 0.06 * dpr,
    alpha: 0.22 + depth * 0.42,
    wob: Math.random() * Math.PI * 2,
  };
}

function drawSky(ctx: CanvasRenderingContext2D, w: number, h: number) {
  const grad = ctx.createLinearGradient(0, 0, 0, h * 0.55);
  grad.addColorStop(0, "#f2c98a");
  grad.addColorStop(0.5, "#eebd7c");
  grad.addColorStop(1, "#e7ab6a");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, w, h * 0.55);

  const sunX = w * 0.72;
  const sunY = h * 0.16;

  // Halo amplio, para que el aire alrededor del sol se vea recalentado.
  const glare = ctx.createRadialGradient(sunX, sunY, 0, sunX, sunY, w * 0.48);
  glare.addColorStop(0, "rgba(255,248,222,0.95)");
  glare.addColorStop(0.22, "rgba(255,228,175,0.5)");
  glare.addColorStop(0.55, "rgba(255,220,160,0.16)");
  glare.addColorStop(1, "rgba(255,220,160,0)");
  ctx.fillStyle = glare;
  ctx.fillRect(0, 0, w, h * 0.65);

  // Disco de sol propiamente dicho -- sin esto es solo un brillo ambiental,
  // no se lee como "el sol" (lo que pedía la referencia del desierto).
  const sunR = h * 0.075;
  const core = ctx.createRadialGradient(sunX, sunY, 0, sunX, sunY, sunR);
  core.addColorStop(0, "rgba(255,255,250,1)");
  core.addColorStop(0.55, "rgba(255,241,205,0.98)");
  core.addColorStop(0.85, "rgba(255,214,140,0.55)");
  core.addColorStop(1, "rgba(255,214,140,0)");
  ctx.fillStyle = core;
  ctx.beginPath();
  ctx.arc(sunX, sunY, sunR * 1.6, 0, Math.PI * 2);
  ctx.fill();

  const haze = ctx.createLinearGradient(0, h * 0.42, 0, h * 0.58);
  haze.addColorStop(0, "rgba(255,236,205,0)");
  haze.addColorStop(0.5, "rgba(255,236,205,0.5)");
  haze.addColorStop(1, "rgba(255,236,205,0)");
  ctx.fillStyle = haze;
  ctx.fillRect(0, h * 0.4, w, h * 0.2);
}

function drawDune(
  ctx: CanvasRenderingContext2D,
  w: number,
  h: number,
  dune: Dune,
  heights: Float32Array,
  time: number,
  idx: number,
  duneSegs: number,
  duneCount: number,
  grainPattern: HTMLCanvasElement,
  scale: number,
) {
  ctx.beginPath();
  ctx.moveTo(0, h);
  for (let i = 0; i <= duneSegs; i++) {
    const x = (i / duneSegs) * w;
    const wob = Math.sin(time * 0.00003 + i * 0.2 + idx) * dune.amp * 0.02;
    const y = dune.baseY - heights[i] + wob;
    ctx.lineTo(x, y);
  }
  ctx.lineTo(w, h);
  ctx.closePath();

  const grad = ctx.createLinearGradient(w * 0.85, dune.baseY - dune.amp * 1.3, w * 0.1, h);
  grad.addColorStop(0, dune.top);
  grad.addColorStop(0.5, dune.mid);
  grad.addColorStop(1, dune.bottom);
  ctx.fillStyle = grad;
  ctx.fill();

  ctx.save();
  ctx.clip();
  const top = dune.baseY - dune.amp * 2;
  ctx.globalAlpha = 0.55;
  ctx.globalCompositeOperation = "overlay";
  const gp = ctx.createPattern(grainPattern, "repeat")!;
  ctx.fillStyle = gp;
  ctx.fillRect(0, top, w, h - top);
  ctx.globalAlpha = 0.28;
  ctx.globalCompositeOperation = "multiply";
  ctx.fillRect(0, top, w, h - top);
  ctx.globalCompositeOperation = "source-over";
  ctx.globalAlpha = 1;

  const lines = idx === duneCount - 1 ? 60 : 34;
  const segLen = idx === duneCount - 1 ? 14 : 10;
  for (let l = 0; l < lines; l++) {
    const xf = l / lines;
    const x0 = xf * w + (rand(l * 3.1 + idx) - 0.5) * (w / lines) * 0.7;
    const startY = dune.baseY - dune.amp * 0.3;
    ctx.beginPath();
    ctx.moveTo(x0, startY);
    for (let s = 0; s <= segLen; s++) {
      const yy = startY + (s * (h - startY)) / segLen;
      const drift = Math.sin(s * 0.9 + l * 1.3) * (6 + idx * 3) * scale + Math.sin(time * 0.00006 + l) * 2.5 * scale;
      ctx.lineTo(x0 + drift, yy);
    }
    const dark = rand(l * 5.2 + idx * 9) > 0.5;
    ctx.strokeStyle = dark
      ? `rgba(70,42,18,${0.1 + rand(l) * 0.16})`
      : `rgba(255,230,190,${0.08 + rand(l * 2) * 0.12})`;
    ctx.lineWidth = Math.max(0.4, (0.8 + rand(l * 7) * 1.8) * scale);
    ctx.stroke();
  }

  ctx.beginPath();
  for (let i = 0; i <= duneSegs; i++) {
    const x = (i / duneSegs) * w;
    const y = dune.baseY - heights[i];
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.strokeStyle = "rgba(255,244,220,0.35)";
  ctx.lineWidth = Math.max(0.6, 2 * scale);
  ctx.stroke();
  ctx.restore();
}

function drawVeils(ctx: CanvasRenderingContext2D, h: number, time: number, veilCanvas: HTMLCanvasElement) {
  const speed = 0.02;
  const vw = veilCanvas.width;
  const bands = [
    { y: h * 0.55, scale: 1.4, alpha: 0.55, dir: 1 },
    { y: h * 0.7, scale: 1.9, alpha: 0.7, dir: -0.7 },
    { y: h * 0.86, scale: 2.3, alpha: 0.8, dir: 1.2 },
  ];
  for (const b of bands) {
    const dw = vw * b.scale;
    const offset = (((time * speed * b.dir) % dw) + dw) % dw;
    ctx.globalAlpha = b.alpha;
    const dh = veilCanvas.height * b.scale;
    ctx.drawImage(veilCanvas, -offset, b.y - dh / 2, dw, dh);
    ctx.drawImage(veilCanvas, dw - offset, b.y - dh / 2, dw, dh);
  }
  ctx.globalAlpha = 1;
}

function drawParticles(
  ctx: CanvasRenderingContext2D,
  w: number,
  h: number,
  dt: number,
  particles: Particle[],
  dpr: number,
  scale: number,
) {
  ctx.save();
  for (const p of particles) {
    p.x += p.vx * dt * 0.06;
    p.y += (p.vy + Math.sin(p.wob) * 0.03) * dt * 0.06;
    p.wob += 0.01;
    if (p.x > w + 20) {
      Object.assign(p, spawnParticle(-10, h, dpr, scale));
    }
    const grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.size * 1.4);
    grad.addColorStop(0, `rgba(214,178,132,${p.alpha})`);
    grad.addColorStop(0.6, `rgba(214,178,132,${p.alpha * 0.4})`);
    grad.addColorStop(1, "rgba(214,178,132,0)");
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.size * 1.4, 0, Math.PI * 2);
    ctx.fill();
  }
  ctx.restore();
}

export function DesertDuneBackground({ className }: { className?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
    let w = 0;
    let h = 0;
    let scale = 1;
    let dunes: Dune[] = [];
    let duneHeightArrs: Float32Array[] = [];
    let duneSegs = 160;
    let grainPattern: HTMLCanvasElement;
    let veilCanvas: HTMLCanvasElement;
    let particles: Particle[] = [];

    const setup = () => {
      const cssW = Math.max(1, canvas.clientWidth);
      const cssH = Math.max(1, canvas.clientHeight);
      canvas.width = Math.floor(cssW * dpr);
      canvas.height = Math.floor(cssH * dpr);
      w = canvas.width;
      h = canvas.height;
      // Escala de detalle: qué tan chica es esta card contra el tamaño de
      // página completa para el que se diseñó originalmente la escena.
      scale = clamp(Math.min(cssW / REF_W, cssH / REF_H), 0.16, 1.2);

      dunes = [
        { baseY: h * 0.5, amp: h * 0.035, freqs: [1.3, 2.7, 5.1], seed: 1.1, top: "#f0d4a4", mid: "#dcae72", bottom: "#b6864e" },
        { baseY: h * 0.62, amp: h * 0.06, freqs: [1.7, 3.1, 6.3], seed: 4.4, top: "#ecc890", mid: "#d29e5e", bottom: "#a06f3e" },
        { baseY: h * 0.82, amp: h * 0.11, freqs: [1.1, 2.3, 4.7], seed: 8.8, top: "#e6bd7e", mid: "#c68e4e", bottom: "#8a5c32" },
      ];
      duneHeightArrs = dunes.map((d) => duneHeights(duneSegs, d.amp, d.freqs, d.seed));

      grainPattern = buildGrain(Math.max(28, Math.round(160 * scale)));
      veilCanvas = buildVeil(Math.max(320, Math.round(1400 * scale)), Math.max(110, Math.round(500 * scale)));

      const particleCount = Math.round(clamp(140 * scale, 26, 140));
      particles = Array.from({ length: particleCount }, () => spawnParticle(Math.random() * w, h, dpr, scale));
    };

    setup();
    const resizeObserver = new ResizeObserver(setup);
    resizeObserver.observe(canvas);

    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const t0 = performance.now();
    const dt = 16.6;

    const drawFrame = (time: number) => {
      drawSky(ctx, w, h);
      dunes.forEach((d, i) => drawDune(ctx, w, h, d, duneHeightArrs[i], time, i, duneSegs, dunes.length, grainPattern, scale));
      drawVeils(ctx, h, time, veilCanvas);
      drawParticles(ctx, w, h, dt, particles, dpr, scale);
    };

    drawFrame(0);

    let raf = 0;
    if (!reduceMotion) {
      const loop = (now: number) => {
        drawFrame(now - t0);
        raf = requestAnimationFrame(loop);
      };
      raf = requestAnimationFrame(loop);
    }

    return () => {
      if (raf) cancelAnimationFrame(raf);
      resizeObserver.disconnect();
    };
  }, []);

  return <canvas ref={canvasRef} className={className} aria-hidden="true" />;
}
