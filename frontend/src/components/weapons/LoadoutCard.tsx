import { motion } from "motion/react";
import { cardRise } from "../motion/presets";
import type { LoadoutTier, LoadoutTierStats } from "../../types";

export const LOADOUT_ORDER: LoadoutTier[] = ["full_buy", "semi_buy", "pistol", "eco"];

const LOADOUT_META: Record<LoadoutTier, { label: string; sub: string; tone: string }> = {
  full_buy: { label: "Full Buy", sub: ">= $3900", tone: "go" },
  semi_buy: { label: "Semi", sub: "$1000-3900", tone: "recon" },
  pistol: { label: "Pistol", sub: "1ra ronda de cada mitad", tone: "gold" },
  eco: { label: "Eco", sub: "$0-1000", tone: "alert" },
};

// hasData=false (0 rondas en este tier) -> nunca pintar rojo/verde, para no
// leer "sin datos" como "mal rendimiento".
function tone(value: number, hotAt: number, coldAt: number, hasData: boolean): "hot" | "cold" | "" {
  if (!hasData) return "";
  if (value >= hotAt) return "hot";
  if (value < coldAt) return "cold";
  return "";
}

export function LoadoutCard({
  tier,
  stats,
}: {
  tier: LoadoutTier;
  stats: LoadoutTierStats | undefined;
}) {
  const meta = LOADOUT_META[tier];
  const hasData = (stats?.rounds ?? 0) > 0;
  const kdVal = stats?.kd ?? 0;
  const adr = stats?.adr ?? 0;
  const acs = stats?.acs ?? 0;
  const dd = stats?.dd ?? 0;
  const kastPct = stats?.kast_pct ?? 0;
  const esrPct = stats?.esr_pct ?? 0;
  const kills = stats?.kills ?? 0;
  const deaths = stats?.deaths ?? 0;
  const killShare = hasData && kills + deaths > 0 ? (kills / (kills + deaths)) * 100 : 0;
  const ddTone = !hasData ? "" : dd > 0 ? "hot" : dd < 0 ? "cold" : "";

  return (
    <motion.div className={`loadout-card${hasData ? "" : " empty"}`} variants={cardRise}>
      <div className="loadout-card-tier">
        <span className={`loadout-badge-wrap tone-${meta.tone}`}>
          <span className={`loadout-badge tone-${meta.tone}`}>{meta.label}</span>
          <span className="loadout-range mono" role="tooltip">
            {meta.sub}
          </span>
        </span>
      </div>

      <div className="loadout-metrics">
        <div className="loadout-metric">
          <span className="loadout-metric-label">K/D</span>
          <span className={`loadout-metric-value mono ${tone(kdVal, 1.1, 0.8, hasData)}`}>
            {kdVal.toFixed(2)}
          </span>
        </div>
        <div className="loadout-metric">
          <span className="loadout-metric-label">ADR</span>
          <span className={`loadout-metric-value mono ${tone(adr, 80, 60, hasData)}`}>
            {adr.toFixed(1)}
          </span>
        </div>
        <div className="loadout-metric">
          <span className="loadout-metric-label">ACS</span>
          <span className={`loadout-metric-value mono ${tone(acs, 70, 50, hasData)}`}>
            {acs.toFixed(1)}
          </span>
        </div>
        <div className="loadout-metric">
          <span className="loadout-metric-label">DDΔ</span>
          <span className={`loadout-metric-value mono ${ddTone}`}>
            {dd > 0 ? "+" : ""}
            {dd.toFixed(1)}
          </span>
        </div>
        <div className="loadout-metric">
          <span className="loadout-metric-label">KAST</span>
          <span className={`loadout-metric-value mono ${tone(kastPct, 75, 60, hasData)}`}>
            {kastPct.toFixed(1)}%
          </span>
        </div>
        <div className="loadout-metric">
          <span className="loadout-metric-label">ESR</span>
          <span className={`loadout-metric-value mono ${tone(esrPct, 60, 40, hasData)}`}>
            {esrPct.toFixed(1)}%
          </span>
        </div>
      </div>

      <div className="loadout-kd-col">
        <div className="loadout-kd-numbers mono">
          <span className="loadout-kd-kills">{kills}</span>
          <span className="loadout-kd-sep">/</span>
          <span className="loadout-kd-deaths">{deaths}</span>
        </div>
        <div className="loadout-kd-bar" aria-hidden="true">
          <span className="loadout-kd-bar-fill" style={{ width: `${killShare}%` }} />
        </div>
      </div>
    </motion.div>
  );
}
