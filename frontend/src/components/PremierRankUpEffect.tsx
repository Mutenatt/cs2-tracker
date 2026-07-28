import { useMemo } from "react";

// Efecto "lluvia de +" de la pantalla de Rank Up / Premier de CS2. Se monta
// dentro de .premier-hero (ver styles.css) y hereda su color de --tier-accent.

type Plus = {
  id: number;
  x: number; // % horizontal dentro del cartel
  size: number; // px
  duration: number; // s, tiempo en cruzar todo el cartel
  delay: number; // s, negativo para que ya estén "en vuelo" al montar
  peakOpacity: number;
  scaleStart: number;
  scaleEnd: number;
};

function PlusIcon() {
  return (
    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <line x1="12" y1="2.5" x2="12" y2="21.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <line x1="2.5" y1="12" x2="21.5" y2="12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

function makePluses(count: number): Plus[] {
  // Reparto por slots en vez de x puramente aleatorio: evita que el azar
  // agrupe varios "+" juntos y deje huecos grandes en otras zonas.
  const margin = 8;
  const usable = 100 - margin * 2;
  const slot = usable / count;

  return Array.from({ length: count }, (_, i) => {
    const duration = 1.6 + Math.random() * 1.8; // 1.6s - 3.4s: velocidades asíncronas
    return {
      id: i,
      x: margin + i * slot + slot * 0.2 + Math.random() * slot * 0.6,
      size: 7 + Math.random() * 8,
      duration,
      delay: -Math.random() * duration, // arranca a mitad de vuelo, evita el "todos nacen juntos"
      peakOpacity: 0.35 + Math.random() * 0.45,
      scaleStart: 0.6 + Math.random() * 0.3,
      scaleEnd: 0.9 + Math.random() * 0.5,
    };
  });
}

export function PremierRankUpEffect({ count = 9 }: { count?: number }) {
  const pluses = useMemo(() => makePluses(count), [count]);
  return (
    <div className="rankup-plus-layer" aria-hidden="true">
      {pluses.map((p) => (
        <span
          key={p.id}
          className="rankup-plus"
          style={
            {
              "--x": `${p.x}%`,
              "--size": `${p.size}px`,
              "--duration": `${p.duration}s`,
              "--delay": `${p.delay}s`,
              "--peak-opacity": p.peakOpacity,
              "--scale-start": p.scaleStart,
              "--scale-end": p.scaleEnd,
            } as React.CSSProperties
          }
        >
          <PlusIcon />
        </span>
      ))}
    </div>
  );
}
