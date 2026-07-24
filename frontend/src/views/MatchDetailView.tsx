import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getMatch } from "../api";
import { useUser } from "../context/UserContext";
import { AnimatedNumber } from "../components/AnimatedNumber";
import { BadgeStrip } from "../components/BadgeStrip";
import { ClutchTimeline } from "../components/ClutchTimeline";
import { DuelMatrix } from "../components/DuelMatrix";
import { EconomyTimeline } from "../components/EconomyTimeline";
import { Heatmap } from "../components/Heatmap";
import { ROUTE_FADE } from "../components/motion/presets";
import { Weapons } from "../components/Weapons";
import { ratingColor, Scoreboard } from "../components/Scoreboard";
import type { MatchDetail, PlayerRow, TeamScore } from "../types";

// Card de contexto de la partida para la columna izquierda (sticky) del
// layout split: mapa, resultado, marcador y tus stats de la partida.
function MatchContextCard({
  match,
  teams,
  me,
}: {
  match: MatchDetail["match"];
  teams: TeamScore[];
  me: PlayerRow;
}) {
  const ct = teams.find((t) => t.team_num === 3);
  const t = teams.find((t) => t.team_num === 2);
  const myTeam = teams.find((tm) => tm.team_num === me.team_num);
  const otherTeam = teams.find((tm) => tm.team_num !== me.team_num);
  const won = myTeam && otherTeam ? myTeam.score > otherTeam.score : null;

  return (
    <div className="match-context-card">
      <div className="label">Última partida analizada</div>
      <div className="mc-map">{(match.map ?? "—").toUpperCase()}</div>
      {won !== null && (
        <div className={`result-stamp flat${won ? " win" : ""}`}>
          {won ? "Victoria" : "Derrota"}
        </div>
      )}
      <div className="mc-scoreline">
        <span className="side-tag ct">CT</span>
        <span className="score-num">{ct?.score ?? "—"}</span>
        <span className="score-sep">–</span>
        <span className="score-num">{t?.score ?? "—"}</span>
        <span className="side-tag t">T</span>
      </div>
      <div className="mc-rating" style={{ color: ratingColor(me.rating) }}>
        <AnimatedNumber value={me.rating} decimals={2} delay={ROUTE_FADE} />
      </div>
      <div
        className="mc-rating-label tip"
        data-tip="Aproximación al HLTV Rating 2.0: combina kills, muertes, asistencias, daño y KAST en un solo número. 1.00 = nivel promedio."
      >
        Rating
      </div>
      <div className="mc-stats">
        <div className="mc-stat">
          <div className="mc-stat-value">
            <AnimatedNumber value={me.kd} decimals={2} delay={ROUTE_FADE} />
          </div>
          <div
            className="mc-stat-label tip"
            data-tip="Kills sobre Deaths: cuántas bajas conseguiste por cada muerte propia."
          >
            K/D
          </div>
        </div>
        <div className="mc-stat">
          <div className="mc-stat-value">
            <AnimatedNumber value={me.adr} decimals={1} delay={ROUTE_FADE} />
          </div>
          <div
            className="mc-stat-label tip"
            data-tip="Average Damage per Round: daño promedio que hiciste por ronda, cuente o no la kill."
          >
            ADR
          </div>
        </div>
        <div className="mc-stat">
          <div className="mc-stat-value">
            <AnimatedNumber value={me.hs_pct} decimals={0} suffix="%" delay={ROUTE_FADE} />
          </div>
          <div
            className="mc-stat-label tip"
            data-tip="Porcentaje de tus kills que fueron impacto de cabeza."
          >
            HS%
          </div>
        </div>
        <div className="mc-stat">
          <div className="mc-stat-value">
            <AnimatedNumber value={me.kast} decimals={0} suffix="%" delay={ROUTE_FADE} />
          </div>
          <div
            className="mc-stat-label tip"
            data-tip="% de rondas donde tuviste Kill, Assist, Sobreviviste o fuiste vengado por un compañero."
          >
            KAST
          </div>
        </div>
      </div>
    </div>
  );
}

export function MatchDetailView() {
  const { matchId } = useParams<{ matchId: string }>();
  const user = useUser();
  const [data, setData] = useState<MatchDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!matchId) return;
    setData(null);
    setError(null);
    (async () => {
      try {
        setData(await getMatch(matchId));
      } catch {
        setError("No se pudo cargar la partida.");
      }
    })();
  }, [matchId]);

  if (error) return <div className="wrap center">{error}</div>;
  if (!data) return <div className="wrap center">Cargando…</div>;

  const { match, teams, scoreboard } = data;
  const me = scoreboard.find((p) => p.steamid === user.steamid);
  const byTeam = (tn: number): PlayerRow[] => scoreboard.filter((p) => p.team_num === tn);

  return (
    <>
      <Link className="back-link" to={`/profile/${user.steamid}`}>
        ← Volver a tu perfil
      </Link>

      <div className="match-split">
        <aside className="match-split-side">
          {me && <MatchContextCard match={match} teams={teams} me={me} />}
          <BadgeStrip matchId={match.match_id} steamid={user.steamid} />
        </aside>

        <div className="match-split-feed">
          <div>
            <div className="section-head">
              <span className="display">Roster</span>
              <span className="rule" />
            </div>
            <div className="roster">
              {teams.map((t) => (
                <Scoreboard
                  key={t.team_num}
                  teamNum={t.team_num}
                  score={t.score}
                  rows={byTeam(t.team_num)}
                  mySteamid={user.steamid}
                />
              ))}
            </div>
          </div>

          <div>
            <DuelMatrix matchId={match.match_id} mySteamid={user.steamid} />
          </div>

          <div>
            <ClutchTimeline matchId={match.match_id} steamid={user.steamid} />
          </div>

          <div>
            <EconomyTimeline matchId={match.match_id} steamid={user.steamid} />
          </div>

          <Weapons matchId={match.match_id} />

          <Heatmap map={match.map} matchId={match.match_id} />

          <footer>cStats://SISTEMA</footer>
        </div>
      </div>
    </>
  );
}
