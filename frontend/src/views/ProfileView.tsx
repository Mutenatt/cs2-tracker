import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { motion } from "motion/react";
import { getProfile } from "../api";
import { AccuracyPanel } from "../components/AccuracyPanel";
import { ClipsPanel } from "../components/ClipsPanel";
import { MatchHistory } from "../components/match-history/MatchHistory";
import { MapStatsPopover } from "../components/MapStatsPopover";
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

export function ProfileView() {
  const { steamid } = useParams<{ steamid: string }>();
  const user = useUser();
  useSteamBackground(user.steam_background_url);
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
                {equivRank && (
                  <span
                    className={`csgo-equiv-chip ${tierClass(currentRank)}`}
                    title={`Equivalente CS:GO: ${equivRank.name}`}
                  >
                    <RankCrest rank={equivRank} />
                    <span className="equiv-name">{equivRank.name}</span>
                  </span>
                )}
              </div>
            )}
          </div>
          {steamid && <ProfileTagChips steamid={steamid} />}

          {/* Agrupados en un solo bloque centrado verticalmente contra el
              alto completo de la tarjeta (.profile-hero-info es
              align-self:stretch) -- antes CS RATING y phs-inline eran dos
              posicionamientos absolutos independientes con tops fijos, lo
              que los dejaba pegados abajo con un hueco vacío arriba. */}
          <div className="cs-rating-block">
            {currentRank !== null && (
              <span className="ph-unit mono cs-rating-label">CS RATING</span>
            )}

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
        </div>

        {topMap && (
          <div className="profile-hero-summary">
            <div className="phs-bg">
              <MapWallpaperCarousel map={topMap.map} />
            </div>
            <MapStatsPopover map={topMap.map} winRate={topMap.win_rate} />
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
          </div>
          <MatchHistory matches={match_history} />
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
        </div>
      </div>
    </>
  );
}
