import type { MapPoolEntry } from "../types";

interface MapRow {
  map: string;
  winPct: number;
  wins: number;
  losses: number;
}

// win% sobre partidas RESUELTAS (wins+losses), no sobre matches_played --
// las partidas con won=None (ronda sin resolver) no ensucian el %.
function toRows(mapPool: MapPoolEntry[]): MapRow[] {
  return mapPool
    .filter((mp) => mp.has_data && mp.wins + mp.losses > 0)
    .map((mp) => ({
      map: mp.map,
      winPct: (100 * mp.wins) / (mp.wins + mp.losses),
      wins: mp.wins,
      losses: mp.losses,
    }))
    .sort((a, b) => b.winPct - a.winPct);
}

export function TopMapsPanel({ mapPool }: { mapPool: MapPoolEntry[] }) {
  const rows = toRows(mapPool);
  return (
    <div className="panel-card">
      <div className="panel-title">Top mapas</div>
      {rows.length === 0 ? (
        <p className="muted">Todavía no hay partidas con resultado resuelto.</p>
      ) : (
        <>
          <div className="map-table-head">
            <span>Mapa</span>
            <span>Win %</span>
          </div>
          <div className="map-rows">
            {rows.map((r) => (
              <div className="map-row" key={r.map}>
                <span className="mr-name">{r.map}</span>
                <div className="mr-winpct">
                  <b className={r.winPct === 100 ? "gold" : r.winPct === 0 ? "alert" : undefined}>
                    {r.winPct.toFixed(1)}%
                  </b>
                  <div className="mr-record">
                    {r.wins}V - {r.losses}D
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
      <div className="panel-cta">Ver todos los mapas</div>
    </div>
  );
}
