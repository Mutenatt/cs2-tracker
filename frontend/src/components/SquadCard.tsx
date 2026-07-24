import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getCompare, getRivals } from "../api";
import type { WinrateTogetherSummary } from "../types";

interface SquadRow {
  steamid: string;
  name: string | null;
  winrate: WinrateTogetherSummary | null;
}

const TOP_N = 3;

// Compañeros frecuentes + winrate jugando juntos (solo partidas en el
// mismo equipo -- el backend excluye enfrentamientos y resultados sin
// resolver del %).
export function SquadCard({ steamid }: { steamid: string }) {
  const [rows, setRows] = useState<SquadRow[] | null>(null);

  useEffect(() => {
    setRows(null);
    (async () => {
      try {
        const { rivals } = await getRivals(steamid);
        const companeros = rivals.filter((r) => r.matches_together > 0).slice(0, TOP_N);
        const withWinrate = await Promise.all(
          companeros.map(async (c) => {
            const cmp = await getCompare(steamid, c.steamid).catch(() => null);
            return { steamid: c.steamid, name: c.name, winrate: cmp?.winrate_together ?? null };
          })
        );
        setRows(withWinrate);
      } catch {
        setRows([]);
      }
    })();
  }, [steamid]);

  if (!rows || rows.length === 0) return null;

  return (
    <div className="panel-card">
      <div className="panel-title">Squad</div>
      <div className="panel-subtitle">Compañeros frecuentes · winrate jugando juntos</div>
      <div className="squad-rows">
        {rows.map((r) => (
          <div className="squad-row" key={r.steamid}>
            <Link className="sq-name" to={`/profile/${r.steamid}`}>
              {r.name ?? r.steamid}
            </Link>
            {r.winrate ? (
              <div className="sq-winrate">
                <b>{r.winrate.win_rate.toFixed(0)}%</b>
                <div className="sq-record">
                  {r.winrate.matches_together} juntos · {r.winrate.wins}V - {r.winrate.losses}D
                </div>
              </div>
            ) : (
              <span className="sq-record">sin partidas juntos</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
