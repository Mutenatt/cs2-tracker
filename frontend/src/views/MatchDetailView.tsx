import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getMatch } from "../api";
import { useUser } from "../context/UserContext";
import { AnimatedNumber } from "../components/AnimatedNumber";
import { BadgeStrip } from "../components/BadgeStrip";
import { ClutchTimeline } from "../components/ClutchTimeline";
import { DuelMatrix } from "../components/DuelMatrix";
import { Heatmap } from "../components/Heatmap";
import { ROUTE_FADE } from "../components/motion/presets";
import { Weapons } from "../components/Weapons";
import { Scoreboard } from "../components/Scoreboard";
import type { MatchDetail, PlayerRow, TeamScore } from "../types";

// Debrief: hero de la partida + tus stats. Ambas mitades vienen de datos
// reales (scoreboard); las barras de rondas ganadas por mitad no se
// muestran todavía porque la API no expone el desglose por mitad de ronda.
function Debrief({
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
    <div className="debrief">
      <div className="db-map">
        <div className="label">Última partida analizada</div>
        <div className="map-title-row">
          <div className="display mapname">{(match.map ?? "—").toUpperCase()}</div>
          {won !== null && (
            <div className={`result-stamp${won ? " win" : ""}`}>{won ? "Victoria" : "Derrota"}</div>
          )}
        </div>
        <div className="scoreline">
          <span className="side-tag ct">CT</span>
          <span className="score-num">{ct?.score ?? "—"}</span>
          <span className="score-sep">–</span>
          <span className="score-num">{t?.score ?? "—"}</span>
          <span className="side-tag t">T</span>
        </div>
      </div>
      <div className="db-you">
        <div className="rating-block">
          <div className="rating-num mono">
            <AnimatedNumber value={me.rating} decimals={2} delay={ROUTE_FADE} />
          </div>
          <div
            className="label tip"
            data-tip="Aproximación al HLTV Rating 2.0: combina kills, muertes, asistencias, daño y KAST en un solo número. 1.00 = nivel promedio."
          >
            Rating
          </div>
        </div>
        <div className="stat-grid">
          <div className="stat-item">
            <div
              className="label tip"
              data-tip="Kills sobre Deaths: cuántas bajas conseguiste por cada muerte propia."
            >
              K/D
            </div>
            <div className="v mono">
              <AnimatedNumber value={me.kd} decimals={2} delay={ROUTE_FADE} />
            </div>
          </div>
          <div className="stat-item">
            <div
              className="label tip"
              data-tip="Average Damage per Round: daño promedio que hiciste por ronda, cuente o no la kill."
            >
              ADR
            </div>
            <div className="v mono">
              <AnimatedNumber value={me.adr} decimals={1} delay={ROUTE_FADE} />
            </div>
          </div>
          <div className="stat-item">
            <div
              className="label tip"
              data-tip="Porcentaje de tus kills que fueron impacto de cabeza."
            >
              HS%
            </div>
            <div className="v mono">
              <AnimatedNumber value={me.hs_pct} decimals={0} suffix="%" delay={ROUTE_FADE} />
            </div>
          </div>
          <div className="stat-item">
            <div
              className="label tip"
              data-tip="% de rondas donde tuviste Kill, Assist, Sobreviviste o fuiste vengado por un compañero."
            >
              KAST
            </div>
            <div className="v mono">
              <AnimatedNumber value={me.kast} decimals={0} suffix="%" delay={ROUTE_FADE} />
            </div>
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

      <BadgeStrip matchId={match.match_id} steamid={user.steamid} />

      {me && <Debrief match={match} teams={teams} me={me} />}

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

      <DuelMatrix matchId={match.match_id} mySteamid={user.steamid} />

      <ClutchTimeline matchId={match.match_id} steamid={user.steamid} />

      <Weapons matchId={match.match_id} />

      <Heatmap map={match.map} matchId={match.match_id} />

      <footer>cStats://SISTEMA</footer>
    </>
  );
}
