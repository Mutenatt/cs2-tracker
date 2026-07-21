import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { motion } from "motion/react";
import { getProfile } from "../api";
import { AnimatedNumber } from "../components/AnimatedNumber";
import { AutoFetchSettings } from "../components/AutoFetchSettings";
import { CoachCorner } from "../components/CoachCorner";
import { tierClass } from "../components/RankBadge";
import { RankHistoryCard } from "../components/RankHistoryCard";
import { useUser } from "../context/UserContext";
import { FillBar } from "../components/motion/FillBar";
import { cardRise, numberDelay, staggerList } from "../components/motion/presets";
import type { ProfileResponse } from "../types";

const SIDE_LABEL: Record<number, string> = { 2: "T", 3: "CT" };
const MotionLink = motion.create(Link);

function MatchHistoryCard({ m }: { m: ProfileResponse["match_history"][number] }) {
  const resultLabel = m.won === null ? "" : m.won ? "Victoria" : "Derrota";
  const resultClass = m.won === null ? "" : m.won ? "w" : "l";
  const side = m.team_num !== null ? SIDE_LABEL[m.team_num] : null;
  // Fecha REAL de juego (matchtime del GC); sin ella no se muestra fecha
  // (ingested_at sería engañoso: es cuándo se cargó el demo, no cuándo se jugó).
  const playedDate = m.played_at
    ? new Date(m.played_at).toLocaleDateString(undefined, { day: "numeric", month: "short" })
    : null;
  return (
    <MotionLink className="mh-card" to={`/match/${m.match_id}`} variants={cardRise}>
      <span className={`stripe ${resultClass}`} />
      {m.map && (
        <img
          className="mh-emblem"
          src={`/map-icons/${m.map}.png`}
          alt={m.map}
          onError={(e) => {
            // Mapa sin emblema -> cae al radar; sin radar tampoco -> se oculta.
            const img = e.currentTarget as HTMLImageElement;
            if (!img.src.endsWith(`/maps/${m.map}.png`)) {
              img.src = `/maps/${m.map}.png`;
              img.className = "mh-thumb";
            } else {
              img.style.visibility = "hidden";
            }
          }}
        />
      )}
      <span className="mh-mid">
        <span className="mh-top">
          <span className="mh-map">{(m.map ?? "—").toUpperCase()}</span>
          {resultLabel && <span className={`mh-result ${resultClass}`}>{resultLabel}</span>}
        </span>
        <span className="mh-sub">
          {playedDate ? `${playedDate} · ` : ""}
          {m.my_score ?? "—"} – {m.opponent_score ?? "—"}
          {side ? ` · empezaste ${side}` : ""} · {m.n_rounds ?? "—"} rondas
        </span>
      </span>
      <span className="mh-stats">
        <span>
          <b>{m.kd.toFixed(2)}</b>
          <span>K/D</span>
        </span>
        <span>
          <b>{m.adr.toFixed(1)}</b>
          <span>ADR</span>
        </span>
        <span>
          <b>{m.rating.toFixed(2)}</b>
          <span>Rating</span>
        </span>
      </span>
    </MotionLink>
  );
}

export function ProfileView() {
  const { steamid } = useParams<{ steamid: string }>();
  const user = useUser();
  const [data, setData] = useState<ProfileResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!steamid) return;
    setData(null);
    setError(null);
    (async () => {
      try {
        setData(await getProfile(steamid));
      } catch {
        setError("No se pudo cargar el perfil (¿compartís alguna partida con este jugador?).");
      }
    })();
  }, [steamid]);

  if (error) return <p className="section-note">{error}</p>;
  if (!data) return <p className="muted">Cargando…</p>;

  const {
    lifetime,
    match_history,
    map_pool,
    milestones,
    coach_insights,
    rank_history,
    tactical_snapshot,
  } = data;
  const mapsWithData = map_pool.filter((m) => m.has_data).length;
  // Rating Premier vigente: último punto válido de la historia de rank
  // (mismo filtro que RankHistoryCard: >0 y tipo Premier o desconocido).
  const rated = rank_history.filter(
    (p) => p.rank !== null && p.rank > 0 && (p.rank_type === null || p.rank_type === 11)
  );
  const currentRank = rated.length ? rated[rated.length - 1].rank : null;

  return (
    <>
      <div className="profile-hero">
        {data.avatar_url ? (
          <img className="pav" src={data.avatar_url} alt="" style={{ objectFit: "cover" }} />
        ) : (
          <div className="pav">🎯</div>
        )}
        <div>
          <div className="pname-row">
            <span className="display pname">{data.display_name ?? steamid}</span>
            <span className="prank">STEAMID {steamid}</span>
          </div>
          <div className="pmeta">
            <b>{lifetime.matches_played}</b> partidas jugadas ·{" "}
            <b>{lifetime.win_rate.toFixed(0)}%</b> win rate ·{" "}
            <b>
              {mapsWithData} mapa{mapsWithData === 1 ? "" : "s"}
            </b>{" "}
            con datos
          </div>
          {currentRank !== null && (
            <div className="premier-hero">
              <span className="ph-label">Premier Rating</span>
              <span className={`ph-num mono ${tierClass(currentRank)}`}>
                {currentRank.toLocaleString("en-US")}
              </span>
            </div>
          )}
        </div>
      </div>

      <div className="section-note" style={{ marginTop: -8 }}>
        {lifetime.matches_played <= 5 ? (
          <>
            Solo <b>{lifetime.matches_played} partidas reales</b> ingeridas hasta ahora — los
            promedios y el rendimiento por mapa de abajo son reales sobre esa base chica, no
            proyecciones. Con más demos, esto gana solidez estadística solo.
          </>
        ) : (
          <>
            Promedios y rendimiento por mapa calculados sobre tus{" "}
            <b>{lifetime.matches_played} partidas</b> reales ingeridas.
          </>
        )}
      </div>

      <div className="profile-grid">
        <div>
          <div className="section-head">
            <span className="display">Historial de partidas</span>
            <span className="rule" />
          </div>
          <motion.div className="mh-list" variants={staggerList} initial="hidden" animate="show">
            {match_history.map((m) => (
              <MatchHistoryCard key={m.match_id} m={m} />
            ))}
          </motion.div>
          <div className="mh-note">
            El historial crece con cada demo que ingerís (ver <code>INGESTA_MANUAL.md</code>) —
            click en una tarjeta para ver su Match Detail.
          </div>
        </div>

        <div>
          <RankHistoryCard
            rankHistory={rank_history}
            lifetime={lifetime}
            snapshot={tactical_snapshot}
          />

          <div className="section-head">
            <span className="display">Lifetime</span>
            <span className="rule" />
          </div>
          <motion.div
            className="lifetime-grid"
            variants={staggerList}
            initial="hidden"
            animate="show"
          >
            <motion.div className="lt-card" variants={cardRise}>
              <div
                className="label tip"
                data-tip={`Promedio de Rating en tus ${lifetime.matches_played} partidas ingeridas.`}
              >
                Rating promedio
              </div>
              <div className="v mono">
                <AnimatedNumber value={lifetime.avg_rating} decimals={2} delay={numberDelay(0)} />
              </div>
            </motion.div>
            <motion.div className="lt-card" variants={cardRise}>
              <div className="label">ADR promedio</div>
              <div className="v mono">
                <AnimatedNumber value={lifetime.avg_adr} decimals={1} delay={numberDelay(1)} />
              </div>
            </motion.div>
            <motion.div className="lt-card" variants={cardRise}>
              <div className="label">K/D promedio</div>
              <div className="v mono">
                <AnimatedNumber value={lifetime.avg_kd} decimals={2} delay={numberDelay(2)} />
              </div>
            </motion.div>
            <motion.div className="lt-card" variants={cardRise}>
              <div className="label">KAST promedio</div>
              <div className="v mono">
                <AnimatedNumber
                  value={lifetime.avg_kast}
                  decimals={1}
                  suffix="%"
                  delay={numberDelay(3)}
                />
              </div>
            </motion.div>
          </motion.div>

          <div className="section-head">
            <span className="display">Rendimiento por mapa</span>
            <span className="rule" />
          </div>
          {mapsWithData === 0 ? (
            <p className="muted">Todavía no hay mapas con partidas cargadas.</p>
          ) : (
            <div className="legend-card">
              <div className="mp-list">
                {map_pool
                  .filter((mp) => mp.has_data)
                  .map((mp) => {
                    const winRate = (100 * mp.wins) / mp.matches_played;
                    return (
                      <div className="mp-row" key={mp.map}>
                        <div className="mp-top">
                          <span className="mp-name">{mp.map}</span>
                          <span className="mp-kd">
                            K/D {mp.avg_kd?.toFixed(2)} · {mp.matches_played} partida
                            {mp.matches_played === 1 ? "" : "s"}
                          </span>
                        </div>
                        <div className="mp-bar">
                          <FillBar width={`${winRate}%`} />
                        </div>
                      </div>
                    );
                  })}
              </div>
            </div>
          )}

          {milestones.length > 0 && (
            <>
              <div className="section-head">
                <span className="display">Milestones</span>
                <span className="rule" />
              </div>
              <div className="milestones-card">
                {milestones.map((ms) => (
                  <div className="ms-row" key={ms.key}>
                    <span className="k">{ms.label}</span>
                    <span className="v mono">
                      {ms.value}
                      {ms.context && <span className="ctx">{ms.context}</span>}
                    </span>
                  </div>
                ))}
              </div>
            </>
          )}

          <CoachCorner insights={coach_insights} />

          {user.steamid === steamid && <AutoFetchSettings />}
        </div>
      </div>
    </>
  );
}
