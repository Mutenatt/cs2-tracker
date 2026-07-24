import type { Variants } from "motion/react";

// Timings compartidos: mantiene coordinados F1 (stagger de tarjetas),
// F2 (fade de rutas) y F3 (contadores/barras) sin duplicar números mágicos.
export const ROUTE_FADE = 0.15;
export const CARD_DURATION = 0.25;
export const CARD_STAGGER = 0.05;
export const COUNT_DURATION = 0.8;

export const staggerList: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: CARD_STAGGER } },
};

export const cardRise: Variants = {
  hidden: { opacity: 0, y: 12 },
  show: { opacity: 1, y: 0, transition: { duration: CARD_DURATION, ease: "easeOut" } },
};

export const LIVE_PULSE_DURATION = 1.8;
export const livePulse: Variants = {
  pulse: {
    opacity: [1, 0.35, 1],
    transition: { duration: LIVE_PULSE_DURATION, repeat: Infinity, ease: "easeInOut" },
  },
};
