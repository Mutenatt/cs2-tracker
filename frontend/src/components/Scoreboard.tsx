import { Link } from "react-router-dom";
import { RankBadge } from "./RankBadge";
import type { PlayerRow } from "../types";

// Convención del proyecto: team_num 2 = T, 3 = CT (ver CLAUDE.md).
const SIDE: Record<number, "t" | "ct"> = { 2: "t", 3: "ct" };
const SIDE_LABEL: Record<number, string> = { 2: "Equipo T", 3: "Equipo CT" };

export function ratingColor(rating: number): string | undefined {
  if (rating >= 1.3) return "var(--signal)";
  if (rating < 1) return "var(--text-dim)";
  return undefined;
}

interface Props {
  rows: PlayerRow[];
  teamNum: number;
  score: number;
  mySteamid?: string;
}

export function Scoreboard({ rows, teamNum, score, mySteamid }: Props) {
  const side = SIDE[teamNum] ?? "t";
  return (
    <div className={`team-panel ${side}`}>
      <div className="team-head">
        <span className="display">{SIDE_LABEL[teamNum] ?? `Equipo ${teamNum}`}</span>
        <span className="mono">{score}</span>
      </div>
      {rows.map((p, i) => (
        <div className={`row${p.steamid === mySteamid ? " you" : ""}`} key={p.steamid}>
          <span className="rk">{String(i + 1).padStart(2, "0")}</span>
          <Link className="nm" to={`/profile/${p.steamid}`}>
            {p.name ?? "?"}
            <RankBadge rank={p.rank} rankType={p.rank_type} />
          </Link>
          <span className="kda">
            {p.kills}-{p.deaths}-{p.assists}
          </span>
          <span className="adr">{p.adr.toFixed(1)}</span>
          <span className="rt" style={{ color: ratingColor(p.rating) }}>
            {p.rating.toFixed(2)}
          </span>
        </div>
      ))}
    </div>
  );
}
