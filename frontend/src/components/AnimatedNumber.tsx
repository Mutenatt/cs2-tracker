import { useEffect, useRef } from "react";
import { animate, useReducedMotion } from "motion/react";
import { COUNT_DURATION } from "./motion/presets";

// Cuenta de 0 al valor final escribiendo textContent directo (sin re-render
// por frame). animate() imperativo no pasa por <MotionConfig reducedMotion>,
// por eso el bailout de useReducedMotion es explícito acá.
export function AnimatedNumber({
  value,
  decimals = 0,
  suffix = "",
  delay = 0,
  duration = COUNT_DURATION,
}: {
  value: number;
  decimals?: number;
  suffix?: string;
  delay?: number;
  duration?: number;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const reduced = useReducedMotion();
  const final = value.toFixed(decimals) + suffix;

  useEffect(() => {
    if (reduced || !ref.current) return;
    const el = ref.current;
    const controls = animate(0, value, {
      duration,
      delay,
      ease: "easeOut",
      onUpdate: (v) => {
        el.textContent = v.toFixed(decimals) + suffix;
      },
      onComplete: () => {
        el.textContent = final;
      },
    });
    return () => controls.stop();
  }, [value, decimals, suffix, delay, duration, reduced, final]);

  if (reduced) return <span>{final}</span>;

  return (
    // El sizer invisible reserva el ancho final; el overlay animado no
    // produce layout shift aunque cambie la cantidad de dígitos.
    <span style={{ position: "relative", display: "inline-block" }}>
      <span style={{ visibility: "hidden" }} aria-hidden="true">
        {final}
      </span>
      <span ref={ref} style={{ position: "absolute", inset: 0 }}>
        {(0).toFixed(decimals) + suffix}
      </span>
    </span>
  );
}
