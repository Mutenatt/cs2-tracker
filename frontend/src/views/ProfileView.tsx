import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { motion } from "motion/react";
import { getProfile } from "../api";
import { AccuracyPanel } from "../components/AccuracyPanel";
import { AutoFetchSettings } from "../components/AutoFetchSettings";
import { ClipsPanel } from "../components/ClipsPanel";
import { MatchTypeFilter, type MatchTypeFilterValue } from "../components/MatchTypeFilter";
import { ProfileTagChips } from "../components/ProfileTagChips";
import { SquadCard } from "../components/SquadCard";
import { CoachCorner } from "../components/CoachCorner";
import { tierClass } from "../components/RankBadge";
import { RankHistoryCard } from "../components/RankHistoryCard";
import { TopMapsPanel } from "../components/TopMapsPanel";
import { TopWeaponsPanel } from "../components/TopWeaponsPanel";
import { useUser } from "../context/UserContext";
import { cardRise, staggerList } from "../components/motion/presets";
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
  const [visibleCount, setVisibleCount] = useState(10);
  const [typeFilter, setTypeFilter] = useState<MatchTypeFilterValue>({
    premier: true,
    competitivo: true,
  });

  useEffect(() => {
    setVisibleCount(10);
  }, [typeFilter]);

  useEffect(() => {
    if (!steamid) return;
    setData(null);
    setError(null);
    setVisibleCount(10);
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
    steamid: profileSteamid,
    lifetime,
    match_history,
    map_pool,
    milestones,
    coach_insights,
    rank_history,
    tactical_snapshot,
    accuracy,
    top_weapons,
  } = data;
  // Rating Premier vigente: último punto válido de la historia de rank
  // (mismo filtro que RankHistoryCard: >0 y tipo Premier o desconocido).
  const rated = rank_history.filter(
    (p) => p.rank !== null && p.rank > 0 && (p.rank_type === null || p.rank_type === 11)
  );
  const entryRank = rated.length ? rated[rated.length - 1].rank : null;
  // Rating vivo del GC (Capa 2) si está; si no, el de entrada a la última
  // partida derivado del demo (Capa 1).
  const liveRating = data.current_premier_rating;
  const currentRank = liveRating ?? entryRank;
  // Delta a mostrar: con rating vivo cerramos el gap y mostramos el cambio de
  // la ÚLTIMA partida (vivo − entrada de esa partida). Sin vivo, lo más nuevo
  // que podemos afirmar es el delta de la penúltima (última resuelta).
  const lastResolvedDelta =
    [...rated].reverse().find((p) => p.rating_delta !== null)?.rating_delta ?? null;
  const heroDelta =
    liveRating !== null && entryRank !== null ? liveRating - entryRank : lastResolvedDelta;

  // rank_type === null: demo vieja sin re-ingerir, no se puede clasificar ->
  // se muestra siempre para no ocultar historial existente.
  const filteredHistory = match_history.filter((m) => {
    if (m.rank_type === null) return true;
    return m.rank_type === 11 ? typeFilter.premier : typeFilter.competitivo;
  });

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
            <b>{lifetime.win_rate.toFixed(0)}%</b> win rate
          </div>
          {currentRank !== null && (
            <div className="premier-hero">
              <span className="ph-label">Premier Rating</span>
              <span className={`ph-num mono ${tierClass(currentRank)}`}>
                {currentRank.toLocaleString("en-US")}
              </span>
              {heroDelta !== null && heroDelta !== 0 && (
                <span
                  className={`ph-delta mono ${heroDelta > 0 ? "up" : "down"}`}
                  title={
                    liveRating !== null
                      ? "Cambio en tu última partida (rating vivo del Game Coordinator)"
                      : "Cambio en tu última partida con resultado ya calculado"
                  }
                >
                  {heroDelta > 0 ? "▲" : "▼"} {Math.abs(heroDelta).toLocaleString("en-US")}
                </span>
              )}
            </div>
          )}
          {steamid && <ProfileTagChips steamid={steamid} />}
        </div>
      </div>

      <div className="section-note" style={{ marginTop: -8 }}>
        {lifetime.matches_played <= 5 ? (
          <>
            Solo <b>{lifetime.matches_played} partidas reales</b> ingeridas hasta ahora — las
            estadísticas de abajo son reales sobre esa base chica, no proyecciones. Con más demos,
            esto gana solidez estadística solo.
          </>
        ) : (
          <>
            Estadísticas calculadas sobre tus <b>{lifetime.matches_played} partidas</b> reales
            ingeridas.
          </>
        )}
      </div>

      <div className="profile-grid">
        <div>
          <div className="section-head">
            <span className="display">Historial de partidas</span>
            <span className="rule" />
            <MatchTypeFilter value={typeFilter} onChange={setTypeFilter} />
          </div>
          <motion.div className="mh-list" variants={staggerList} initial="hidden" animate="show">
            {filteredHistory.slice(0, visibleCount).map((m) => (
              <MatchHistoryCard key={m.match_id} m={m} />
            ))}
          </motion.div>
          {visibleCount < filteredHistory.length && (
            <button className="panel-cta" onClick={() => setVisibleCount((v) => v + 10)}>
              Cargar más partidas
            </button>
          )}
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

          <AccuracyPanel data={accuracy} />

          {steamid && <SquadCard steamid={steamid} />}

          <CoachCorner insights={coach_insights} />
        </div>

        <div>
          <div className="section-head">
            <span className="display">Lifetime</span>
            <span className="rule" />
          </div>
          {milestones.length === 0 ? (
            <p className="muted">Todavía no hay suficientes partidas para milestones.</p>
          ) : (
            <motion.div
              className="lifetime-grid"
              variants={staggerList}
              initial="hidden"
              animate="show"
            >
              {milestones.map((ms) => (
                <motion.div className="lt-card" variants={cardRise} key={ms.key}>
                  <div className="label">{ms.label}</div>
                  <div className="v mono">{ms.value}</div>
                </motion.div>
              ))}
            </motion.div>
          )}

          <TopWeaponsPanel weapons={top_weapons} steamid={profileSteamid} />

          <TopMapsPanel mapPool={map_pool} />

          {user.steamid === steamid && steamid && <ClipsPanel steamid={steamid} />}

          {user.steamid === steamid && <AutoFetchSettings />}
        </div>
      </div>
    </>
  );
}
