import { useEffect, useRef, useState } from "react";
import TacticalBadge3D from "./TacticalBadge3D";

export const LOGO_TRANSITION_DURATION_MS = 2000;
const FADE_OUT_MS = 260;
// El badge original gira a 0.15 rad/s pensado para quedarse fijo en un hero
// -- acá necesita notarse en una ventana de 2s, así que gira bastante más rápido.
const SPIN_SPEED = 6;

export function LogoIntroTransition({ onFinished }: { onFinished: () => void }) {
  const [fadingOut, setFadingOut] = useState(false);

  // App.tsx pasa un onFinished inline, así que su identidad cambia en cada
  // render del padre -- si entrara en el array de deps de abajo, cada
  // re-render de App reiniciaría los timers desde cero y la cortina nunca
  // terminaría a los 2s reales. El ref la mantiene al día sin reabrir el
  // efecto (que corre una única vez, al montar).
  const onFinishedRef = useRef(onFinished);
  onFinishedRef.current = onFinished;

  useEffect(() => {
    const fadeTimer = setTimeout(() => setFadingOut(true), LOGO_TRANSITION_DURATION_MS - FADE_OUT_MS);
    const doneTimer = setTimeout(() => onFinishedRef.current(), LOGO_TRANSITION_DURATION_MS);
    return () => {
      clearTimeout(fadeTimer);
      clearTimeout(doneTimer);
    };
  }, []);

  return (
    <div className={`logo-intro-transition${fadingOut ? " logo-intro-transition-out" : ""}`}>
      <div className="logo-intro-transition-stage">
        <TacticalBadge3D accent="ice" spinSpeed={SPIN_SPEED} background="transparent" />
      </div>
      <div className="logo-intro-transition-word">
        <span className="logo-intro-transition-word-c">c</span>
        <span className="logo-intro-transition-word-stats">Stats</span>
      </div>
    </div>
  );
}
