import { motion } from "motion/react";
import { cardRise, staggerList } from "../motion/presets";
import { niceWeaponName } from "../../data/weaponNames";
import { WeaponSilhouette } from "../WeaponSilhouette";
import type { WeaponCategory, WeaponDetailEntry } from "../../types";

// Etiqueta corta para el badge de rango ("#1 RIFLE") -- WEAPON_CATEGORY_LABEL
// (weaponNames.ts) usa frases largas en plural pensadas para la barra de
// filtros, no para un badge de una tarjeta.
const CATEGORY_SHORT: Record<WeaponCategory, string> = {
  rifle: "Rifle",
  pistol: "Pistola",
  smg: "SMG",
  sniper: "Sniper",
  shotgun: "Escopeta",
  heavy: "Pesada",
  melee: "Cuchillo",
};

export function WeaponHeroGrid({ weapons }: { weapons: WeaponDetailEntry[] }) {
  const top3 = [...weapons].sort((a, b) => b.kills - a.kills).slice(0, 3);
  if (top3.length === 0) return null;

  return (
    <motion.div
      className="weapons-hero-grid"
      variants={staggerList}
      initial="hidden"
      animate="show"
    >
      {top3.map((w, i) => (
        <motion.div className="weapons-hero-card" variants={cardRise} key={w.name}>
          <span className={`weapon-rank-badge rank-${i + 1}`}>
            #{i + 1} {CATEGORY_SHORT[w.category]}
          </span>
          <div className="weapons-hero-glow" aria-hidden="true" />
          <WeaponSilhouette weapon={w.name} category={w.category} width={110} height={44} />
          <div className="weapons-hero-name">{niceWeaponName(w.name)}</div>
          <div className="weapons-hero-stats">
            <div>
              <b className="mono">{w.kills}</b>
              <span>Kills</span>
            </div>
            <div>
              <b className="mono">{w.hs_pct.toFixed(1)}%</b>
              <span>HS%</span>
            </div>
            <div>
              <b className="mono">{w.adr.toFixed(1)}</b>
              <span>ADR</span>
            </div>
          </div>
        </motion.div>
      ))}
    </motion.div>
  );
}
