import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { motion } from "motion/react";
import { getProfile } from "../api";
import { AccuracyPanel } from "../components/AccuracyPanel";
import { AutoFetchSettings } from "../components/AutoFetchSettings";
import { BackgroundSettings } from "../components/BackgroundSettings";
import { ClipsPanel } from "../components/ClipsPanel";
import { FlyingCrowWatermark } from "../components/FlyingCrowWatermark";
import { MatchTypeFilter, type MatchTypeFilterValue } from "../components/MatchTypeFilter";
import { MapWallpaperCarousel } from "../components/MapWallpaperCarousel";
import { PremierRankUpEffect } from "../components/PremierRankUpEffect";
import { ProfileTagChips } from "../components/ProfileTagChips";
import { SquadCard } from "../components/SquadCard";
import { CoachCorner } from "../components/CoachCorner";
import { tierClass } from "../components/RankBadge";
import { RankHistoryCard } from "../components/RankHistoryCard";
import { csgoRankFor, RankCrest } from "../lib/csgoRankEquivalent";
import { isPromotionalMatch } from "../lib/premierRating";
import { TopMapsPanel } from "../components/TopMapsPanel";
import { TopWeaponsPanel } from "../components/TopWeaponsPanel";
import { useUser } from "../context/UserContext";
import { useSteamBackground } from "../hooks/useSteamBackground";
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
            if (!img.src.endsWith(`/radar/${m.map}_radar_psd.png`)) {
              img.src = `/radar/${m.map}_radar_psd.png`;
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
  useSteamBackground(user.custom_background_url ?? user.steam_background_url);
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
  const equivRank = currentRank !== null ? csgoRankFor(currentRank) : null;
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

  // "Mejor mapa" ya viene resuelto por el backend (win rate + desempate por
  // muestra, ver profile_domain.best_map) -- se busca la fila de map_pool
  // que corresponde en vez de reordenar acá.
  const topMap = tactical_snapshot.best_map
    ? map_pool.find((m) => m.map === tactical_snapshot.best_map)
    : undefined;
  const topWeapon = top_weapons[0];

  return (
    <>
      <div className={`profile-hero ${currentRank !== null ? tierClass(currentRank) : ""}`}>
        {equivRank?.name === "Legendary Eagle" && <FlyingCrowWatermark />}
        <div className="profile-hero-avatar-col">
          {data.display_name && (
            <span className="display pname pname-above-avatar">{data.display_name}</span>
          )}
          {data.avatar_url ? (
            <img className="pav" src={data.avatar_url} alt="" style={{ objectFit: "cover" }} />
          ) : (
            <div className="pav">🎯</div>
          )}
        </div>
        <div className="profile-hero-info">
          <div className="pname-row">
            {currentRank !== null && (
              <div className="premier-hero-row">
                <div className="premier-hero">
                  {isPromotionalMatch(currentRank) && <PremierRankUpEffect />}
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
              </div>
            )}
          </div>
          {equivRank && currentRank !== null && (
            <span
              className={`csgo-equiv-chip expanded equiv-chip-bottom ${tierClass(currentRank)}`}
              title={`Equivalente CS:GO: ${equivRank.name}`}
            >
              <RankCrest rank={equivRank} />
              <span className="equiv-name">{equivRank.name}</span>
            </span>
          )}
          {steamid && <ProfileTagChips steamid={steamid} />}

          {currentRank !== null && <span className="ph-unit mono cs-rating-label">CS RATING</span>}

          {/* Cerca del chip de rango equivalente (misma columna), no en el
              panel del carrusel de mapa -- fondo propio en degradé de tier
              (ver .phs-inline .phs-stat) en vez de depender del wallpaper. */}
          <div className="phs-inline">
            <div className="phs-stat phs-stat-adr">
              <span className="label">ADR</span>
              <b>{lifetime.avg_adr.toFixed(1)}</b>
            </div>
            <div className="phs-stat phs-stat-hs">
              <span className="label">HS%</span>
              <b>{accuracy.head_pct.toFixed(0)}%</b>
            </div>
            {topWeapon && (
              <div className="phs-stat phs-stat-weapon">
                <span className="label">Mejor arma</span>
                <b>{topWeapon.name}</b>
              </div>
            )}
          </div>
        </div>

        {topMap && (
          <div className="profile-hero-summary">
            <div className="phs-bg">
              <MapWallpaperCarousel map={topMap.map} />
            </div>
            <div className="phs-grid-single">
              <div className="phs-stat phs-stat-map">
                <span className="label">Mejor mapa</span>
                <span className="phs-sub">·</span>
                <span>
                  <b>{topMap.map.replace(/^de_/, "")}</b>
                  {topMap.win_rate !== null && (
                    <span className="phs-sub"> · {topMap.win_rate.toFixed(0)}% WR</span>
                  )}
                </span>
              </div>
            </div>
          </div>
        )}
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
          {user.steamid === steamid && <BackgroundSettings />}
        </div>
      </div>
    </>
  );
}
