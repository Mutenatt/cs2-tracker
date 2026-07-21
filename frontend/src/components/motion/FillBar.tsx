import { motion } from "motion/react";
import { BAR_DURATION } from "./presets";

// scaleX (no width): barato en GPU y motion lo deshabilita solo bajo
// reduced-motion (a diferencia de animar `width`).
export function FillBar({ width, origin = "left" }: { width: string; origin?: "left" | "right" }) {
  return (
    <motion.i
      style={{ width, transformOrigin: origin }}
      initial={{ scaleX: 0 }}
      whileInView={{ scaleX: 1 }}
      viewport={{ once: true, amount: 0.6 }}
      transition={{ duration: BAR_DURATION, ease: "easeOut" }}
    />
  );
}
