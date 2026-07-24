import { useEffect, useState } from "react";
import { getMatchEconomy } from "../api";
import type { RoundEconomyEntry, TipoCompra } from "../types";

const TIPO_LABEL: Record<TipoCompra, string> = {
  full_buy: "Full buy",
  force_buy: "Force",
  semi_eco: "Semi-eco",
  eco: "Eco",
};

// Tu economía ronda a ronda (equip value post-compra clasificado por tipo).
// Vacío (null-render) en partidas ingeridas antes de round_economy.
export function EconomyTimeline({ matchId, steamid }: { matchId: string; steamid: string }) {
  const [rounds, setRounds] = useState<RoundEconomyEntry[] | null>(null);

  useEffect(() => {
    getMatchEconomy(matchId)
      .then((r) => setRounds(r.rounds.filter((e) => e.steamid === steamid)))
      .catch(() => setRounds([]));
  }, [matchId, steamid]);

  if (!rounds || rounds.length === 0) return null;

  return (
    <div>
      <div className="section-head">
        <span className="display">Economía</span>
        <span className="rule" />
      </div>
      <div className="eco-card">
        <div className="eco-timeline">
          {rounds.map((r) => (
            <span
              key={r.round_num}
              className={`eco-cell ${r.tipo_compra}`}
              title={`Ronda ${r.round_num + 1}: ${TIPO_LABEL[r.tipo_compra]} ($${r.equip_value})`}
            />
          ))}
        </div>
        <div className="eco-legend">
          {(Object.keys(TIPO_LABEL) as TipoCompra[]).map((t) => (
            <span key={t} className="eco-legend-item">
              <span className={`eco-cell ${t}`} /> {TIPO_LABEL[t]}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
