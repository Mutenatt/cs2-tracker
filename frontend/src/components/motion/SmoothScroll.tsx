import type { ReactNode } from "react";
import { ReactLenis } from "lenis/react";
import "lenis/dist/lenis.css";

const LENIS_OPTIONS = {
  duration: 1.1,
  smoothWheel: true,
  wheelMultiplier: 1,
  touchMultiplier: 1.2,
};

// Scroll con inercia (rueda del ratón) solo para las vistas públicas tipo
// landing -- se monta/desmonta junto con la vista que lo envuelve, así que
// no toca el scroll nativo del dashboard ni de las rutas con Canvas 3D a
// pantalla completa (LineUps, PrefireView, RegisterView).
export function SmoothScroll({ children }: { children: ReactNode }) {
  return (
    <ReactLenis root options={LENIS_OPTIONS}>
      {children}
    </ReactLenis>
  );
}
