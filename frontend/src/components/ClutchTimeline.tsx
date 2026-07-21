import { useEffect, useState } from "react";
import { getMatchClutches } from "../api";
import type { ClutchEntry } from "../types";

export function ClutchTimeline({ matchId, steamid }: { matchId: string; steamid: string }) {
  const [clutches, setClutches] = useState<ClutchEntry[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await getMatchClutches(matchId, steamid);
        if (!cancelled) setClutches(r.clutches);
      } catch {
        if (!cancelled) setClutches([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [matchId, steamid]);

  if (!clutches || clutches.length === 0) return null;

  return (
    <>
      <div className="section-head">
        <span className="display">Clutch timeline</span>
        <span className="rule" />
      </div>
      <div className="clutch-list">
        {clutches.map((c, i) => (
          <div className={`clutch-row ${c.outcome}`} key={i}>
            <span className="cx">1v{c.enemies_at_start}</span>
            <span className="cr">Ronda {c.round_num}</span>
            <span className="co">{c.outcome === "won" ? "Ganado" : "Perdido"}</span>
          </div>
        ))}
      </div>
      <div className="section-note" style={{ marginTop: 8 }}>
        Situaciones reales de 1vX detectadas a partir de la secuencia de kills de la partida (mismo
        algoritmo que calcula los clutches ganados, ahora con el detalle de ronda y rivales vivos).
      </div>
    </>
  );
}
