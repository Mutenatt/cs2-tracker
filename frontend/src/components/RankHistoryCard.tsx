import { Crosshair, Map as MapIcon, TrendingUp } from "lucide-react";
import { motion } from "motion/react";
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

// Tarjeta "Rank Premier": area chart SVG con la progresión real del CS
// Rating (extraído de los demos), markers min/max con glow + tooltip
// flotante, y badges tácticos. Estados honestos: sin re-ingesta -> aviso;
// calibrando -> progreso N/10.
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
  const currentElo = rated.length > 0 ? rated[rated.length - 1].rank : null;

  const badges = [
    snapshot.best_map && {
      key: "map",
      icon: <MapIcon size={13} />,
      value: snapshot.best_map.replace(/^de_/i, "").toUpperCase(),
    },
    snapshot.dominant_role && {
      key: "role",
      icon: <Crosshair size={13} className="rh-badge-icon-role" />,
      value: (ROLE_LABEL[snapshot.dominant_role] ?? snapshot.dominant_role).toUpperCase(),
    },
  ].filter(Boolean) as { key: string; icon: JSX.Element; value: string }[];

  return (
    <>
      <div className="section-head">
        <span className="display">Rank Premier</span>
        <span className="rule" />
      </div>
      <div className="rh-card">
        <div className="rh-header">
          <div className="rh-meta mono">
            {lifetime.matches_played} partida{lifetime.matches_played === 1 ? "" : "s"}
            <span className="rh-winrate-badge">{lifetime.win_rate.toFixed(0)}% WR</span>
          </div>
          {currentElo !== null && (
            <div className="rh-elo-now mono">{currentElo.toLocaleString("es")}</div>
          )}
        </div>

        {rated.length >= 2 ? (
          <AreaSparkline points={rated} />
        ) : rated.length === 1 ? (
          <div className="rh-single">
            <span className="rh-elo-now mono">{rated[0].rank!.toLocaleString("es")}</span>
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

        {badges.length > 0 && (
          <div className="rh-badges">
            {badges.map((b) => (
              <span className="rh-badge" key={b.key}>
                {b.icon}
                <span className="rh-badge-value">{b.value}</span>
              </span>
            ))}
          </div>
        )}
      </div>
    </>
  );
}

function AreaSparkline({ points }: { points: RankPoint[] }) {
  const ranks = points.map((p) => p.rank as number);
  const min = Math.min(...ranks);
  const max = Math.max(...ranks);
  const span = max - min;
  const eloGain = max - min;

  const x = (i: number) => PAD + (i / (points.length - 1)) * (W - 2 * PAD);
  // max === min -> línea plana al medio
  const y = (r: number) => (span === 0 ? H / 2 : PAD + ((max - r) / span) * (H - 2 * PAD));

  const line = ranks
    .map((r, i) => `${i === 0 ? "M" : "L"} ${x(i).toFixed(1)} ${y(r).toFixed(1)}`)
    .join(" ");
  const baseline = H - PAD;
  const area = `${line} L ${x(points.length - 1).toFixed(1)} ${baseline} L ${x(0)} ${baseline} Z`;

  const iMin = ranks.indexOf(min);
  const iMax = ranks.indexOf(max);
  const minPt = points[iMin];
  const maxPt = points[iMax];

  // Tooltip flotante por encima o debajo del marker según dónde haya lugar.
  const tagY = (r: number, anchorUp: boolean) =>
    anchorUp ? Math.max(y(r) - 22, 2) : Math.min(y(r) + 8, H - 18);

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
          <linearGradient id="rh-area-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--recon)" stopOpacity={0.28} />
            <stop offset="100%" stopColor="var(--recon)" stopOpacity={0} />
          </linearGradient>
        </defs>

        {[0.25, 0.5, 0.75].map((f) => (
          <line
            key={f}
            x1={0}
            y1={PAD + f * (H - 2 * PAD)}
            x2={W}
            y2={PAD + f * (H - 2 * PAD)}
            className="rh-grid-line"
          />
        ))}

        <motion.path
          d={area}
          fill="url(#rh-area-fill)"
          stroke="none"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        />
        <motion.path
          d={line}
          fill="none"
          stroke="var(--recon)"
          strokeWidth={3}
          strokeLinejoin="round"
          strokeLinecap="round"
          filter="url(#rh-glow)"
          initial={{ pathLength: 0 }}
          animate={{ pathLength: 1 }}
          transition={{ duration: 0.8, ease: "easeOut" }}
        />

        {[
          { i: iMax, r: max, cls: "max", tagY: tagY(max, true) },
          { i: iMin, r: min, cls: "min", tagY: tagY(min, false) },
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
            <ChartTag
              cx={Math.min(Math.max(x(m.i), 24), W - 24)}
              y={m.tagY}
              text={m.r.toLocaleString("es")}
              tone={m.cls as "max" | "min"}
            />
          </g>
        ))}
      </svg>
      <div className="rh-stats-row">
        <div className="rh-stat">
          <span className="rh-stat-label">Mín</span>
          <b className="rh-stat-value mono min">{minPt.rank!.toLocaleString("es")}</b>
        </div>
        <div className="rh-stat">
          <span className="rh-stat-label">Máx</span>
          <b className="rh-stat-value mono max">{maxPt.rank!.toLocaleString("es")}</b>
        </div>
        <div className="rh-stat">
          <span className="rh-stat-label">Elo gain</span>
          <b className="rh-stat-value mono gain">
            <TrendingUp size={13} /> +{eloGain.toLocaleString("es")}
          </b>
        </div>
      </div>
    </div>
  );
}

function ChartTag({
  cx,
  y,
  text,
  tone,
}: {
  cx: number;
  y: number;
  text: string;
  tone: "max" | "min";
}) {
  const w = text.length * 6.2 + 14;
  return (
    <motion.g
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.9, duration: 0.3 }}
    >
      <rect x={cx - w / 2} y={y} width={w} height={16} rx={4} className={`rh-tag-bg ${tone}`} />
      <text x={cx} y={y + 11} textAnchor="middle" className={`rh-tag-text mono ${tone}`}>
        {text}
      </text>
    </motion.g>
  );
}
