import { motion } from "motion/react";
import { RankBadge } from "./RankBadge";
import type { LifetimeStats, RankPoint, TacticalSnapshot } from "../types";

const W = 320;
const H = 96;
const PAD = 14;

const ROLE_LABEL: Record<string, string> = {
  awper: "AWPer",
  entry: "Entry Fragger",
  support: "Support",
  rifler: "Rifler",
};

// Tarjeta "Rank Premier": sparkline SVG con la progresión real del CS Rating
// (extraído de los demos), markers min/max con glow, y chips tácticos.
// Estados honestos: sin re-ingesta -> aviso; calibrando -> progreso N/10.
export function RankHistoryCard({
  rankHistory,
  lifetime,
  snapshot,
}: {
  rankHistory: RankPoint[];
  lifetime: LifetimeStats;
  snapshot: TacticalSnapshot;
}) {
  // Solo puntos con rating real de Premier: los ranks por mapa (escala 1-18)
  // nunca deben contaminar una escala de 0-35000.
  const rated = rankHistory.filter(
    (p) => p.rank !== null && p.rank > 0 && (p.rank_type === null || p.rank_type === 11)
  );
  const missing = rankHistory.filter((p) => p.rank === null).length;
  const calibrating = rankHistory.filter((p) => p.rank === 0);
  const latestWins = calibrating.length ? calibrating[calibrating.length - 1].comp_wins : null;

  const chips = [
    snapshot.best_map && { label: "Mejor mapa", value: snapshot.best_map },
    snapshot.dominant_role && {
      label: "Rol dominante",
      value: ROLE_LABEL[snapshot.dominant_role] ?? snapshot.dominant_role,
    },
  ].filter(Boolean) as { label: string; value: string }[];

  return (
    <>
      <div className="section-head">
        <span className="display">Rank Premier</span>
        <span className="rule" />
      </div>
      <div className="rh-card">
        <div className="rh-meta mono">
          {lifetime.matches_played} partida{lifetime.matches_played === 1 ? "" : "s"} ·{" "}
          {lifetime.win_rate.toFixed(0)}% win rate
        </div>

        {rated.length >= 2 ? (
          <Sparkline points={rated} />
        ) : rated.length === 1 ? (
          <div className="rh-single">
            <RankBadge rank={rated[0].rank} rankType={rated[0].rank_type} />
            <span className="rh-note">
              Una sola partida con CS Rating — el gráfico aparece con la segunda.
            </span>
          </div>
        ) : calibrating.length > 0 ? (
          <p className="rh-note">
            Todavía sin CS Rating — estás calibrando
            {latestWins !== null ? `: ${Math.min(latestWins, 10)}/10 victorias` : ""}. El gráfico
            aparece cuando ingieras partidas posteriores a tu calibración.
          </p>
        ) : (
          <p className="rh-note">
            Tus partidas fueron ingeridas antes de esta función. Re-ingestá tus demos (
            <code>cs2-ingest --source folder --demos ./demos --once --force</code>) para recuperar
            tu CS Rating (ver <code>INGESTA_MANUAL.md</code>).
          </p>
        )}

        {rated.length >= 2 && missing > 0 && (
          <p className="rh-note">
            {missing} partida{missing === 1 ? "" : "s"} sin dato de rank — re-ingestá esas demos
            para completar la línea.
          </p>
        )}

        {chips.length > 0 && (
          <div className="rh-chips">
            {chips.map((c) => (
              <span className="rh-chip" key={c.label}>
                {c.label} · <b>{c.value}</b>
              </span>
            ))}
          </div>
        )}
      </div>
    </>
  );
}

function Sparkline({ points }: { points: RankPoint[] }) {
  const ranks = points.map((p) => p.rank as number);
  const min = Math.min(...ranks);
  const max = Math.max(...ranks);
  const span = max - min;

  const x = (i: number) => PAD + (i / (points.length - 1)) * (W - 2 * PAD);
  // max === min -> línea plana al medio
  const y = (r: number) => (span === 0 ? H / 2 : PAD + ((max - r) / span) * (H - 2 * PAD));

  const d = ranks
    .map((r, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(r).toFixed(1)}`)
    .join(" ");

  const iMin = ranks.indexOf(min);
  const iMax = ranks.indexOf(max);
  const minPt = points[iMin];
  const maxPt = points[iMax];

  // Label por encima o debajo del marker según dónde haya lugar.
  const label = (i: number, r: number, anchorUp: boolean) => ({
    lx: Math.min(Math.max(x(i), 26), W - 26),
    ly: anchorUp ? Math.max(y(r) - 8, 10) : Math.min(y(r) + 16, H - 4),
  });
  const maxLabel = label(iMax, max, true);
  const minLabel = label(iMin, min, false);

  return (
    <div className="rh-spark">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`Progresión de CS Rating: mínimo ${min}, máximo ${max}`}
      >
        <defs>
          <filter id="rh-glow" x="-80%" y="-80%" width="260%" height="260%">
            <feGaussianBlur stdDeviation="2.5" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <motion.path
          d={d}
          fill="none"
          stroke="var(--signal)"
          strokeWidth={2}
          strokeLinejoin="round"
          strokeLinecap="round"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
        />
        {[
          { i: iMax, r: max, cls: "max", ...maxLabel },
          { i: iMin, r: min, cls: "min", ...minLabel },
        ].map((m) => (
          <g key={m.cls}>
            <motion.circle
              cx={x(m.i)}
              cy={y(m.r)}
              r={3.5}
              className={`rh-node ${m.cls}`}
              filter="url(#rh-glow)"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.8, duration: 0.3 }}
            />
            <motion.text
              x={m.lx}
              y={m.ly}
              textAnchor="middle"
              className={`rh-label mono ${m.cls}`}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.9, duration: 0.3 }}
            >
              {m.r.toLocaleString("es")}
            </motion.text>
          </g>
        ))}
      </svg>
      <div className="rh-minmax">
        <span className="rh-mm">
          <span className="label">Mín</span>{" "}
          <RankBadge rank={minPt.rank} rankType={minPt.rank_type} />
        </span>
        <span className="rh-mm">
          <span className="label">Máx</span>{" "}
          <RankBadge rank={maxPt.rank} rankType={maxPt.rank_type} />
        </span>
      </div>
    </div>
  );
}
