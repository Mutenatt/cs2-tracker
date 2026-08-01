import { ChevronRight } from "lucide-react";
import { motion } from "motion/react";
import { Link } from "react-router-dom";
import { cardRise } from "../motion/presets";
import type { MatchHistoryEntry } from "../../types";

const SIDE_LABEL: Record<number, string> = { 2: "T", 3: "CT" };
// Mismos logos de lado que el toggle T/CT de LineUps.tsx.
const SIDE_LOGO: Record<number, string> = {
  2: "/fondo-lineups/logo-tt.jpg",
  3: "/fondo-lineups/logo-ct.jpg",
};
const MotionLink = motion.create(Link);

// >1.05 se resalta como "en racha"; el resto (incluido <0.90) queda con el
// color neutro de los otros stats -- no hay un segundo umbral visual, solo
// el highlight de rating alto.
function ratingClass(rating: number): string {
  return rating > 1.05 ? "hot" : "";
}

export function MatchCard({ match: m }: { match: MatchHistoryEntry }) {
  const resultClass = m.won === null ? "" : m.won ? "w" : "l";
  const side = m.team_num !== null ? SIDE_LABEL[m.team_num] : null;
  const sideLogo = m.team_num !== null ? SIDE_LOGO[m.team_num] : null;
  const mapName = m.map ? m.map.replace(/^de_/, "") : "—";
  // Fecha REAL de juego (matchtime del GC); sin ella no se muestra fecha
  // (ingested_at sería engañoso: es cuándo se cargó el demo, no cuándo se jugó).
  const playedDate = m.played_at
    ? new Date(m.played_at).toLocaleDateString(undefined, { day: "numeric", month: "short" })
    : null;

  return (
    <MotionLink className="mh-card" to={`/match/${m.match_id}`} variants={cardRise}>
      <span className={`mh-stripe ${resultClass}`} aria-hidden="true" />
      {m.map && (
        <img
          className="mh-emblem"
          src={`/map-icons/${m.map}.png`}
          alt={mapName}
          onError={(e) => {
            // Mapa sin emblema -> cae al radar; sin radar tampoco -> se oculta.
            const img = e.currentTarget as HTMLImageElement;
            if (!img.src.endsWith(`/radar/${m.map}_radar_psd.png`)) {
              img.src = `/radar/${m.map}_radar_psd.png`;
              img.className = "mh-thumb";
            } else {
              img.style.visibility = "hidden";
            }
          }}
        />
      )}
      <span className="mh-body">
        <span className="mh-heading">
          <span className="mh-map">{mapName}</span>
          {playedDate && <span className="mh-date">{playedDate}</span>}
        </span>
        <span className="mh-score-row">
          <span className={`mh-score mono ${resultClass}`}>
            {m.my_score ?? "—"} – {m.opponent_score ?? "—"}
          </span>
          {sideLogo && (
            <span className="mh-side-wrap">
              <img className="mh-side-logo" src={sideLogo} alt={`Empezaste ${side}`} />
              <span className="mh-side-tooltip" role="tooltip">
                Empezaste de {side}
              </span>
            </span>
          )}
        </span>
      </span>
      <span className="mh-stats">
        <span className="mh-stat">
          <span className="mh-stat-label">k/d</span>
          <span className="mh-stat-value mono">
            {m.kd.toFixed(2)}
            <span className={`mh-kd-dot ${m.kd >= 1 ? "up" : "down"}`} aria-hidden="true" />
          </span>
        </span>
        <span className="mh-stat">
          <span className="mh-stat-label">adr</span>
          <span className="mh-stat-value mono">{m.adr.toFixed(1)}</span>
        </span>
        <span className="mh-stat">
          <span className="mh-stat-label">rating</span>
          <span className={`mh-stat-value mono ${ratingClass(m.rating)}`}>
            {m.rating.toFixed(2)}
          </span>
        </span>
      </span>
      <ChevronRight className="mh-chevron" aria-hidden="true" />
    </MotionLink>
  );
}
