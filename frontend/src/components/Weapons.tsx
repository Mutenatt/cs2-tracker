import { useEffect, useState } from "react";
import { getWeapons } from "../api";
import type { PlayerWeapons } from "../types";

const NICE: Record<string, string> = {
  ak47: "AK-47",
  m4a1: "M4A4",
  m4a1_silencer: "M4A1-S",
  awp: "AWP",
  hkp2000: "USP/P2000",
  glock: "Glock",
  deagle: "Desert Eagle",
  usp_silencer: "USP-S",
  galilar: "Galil",
  famas: "FAMAS",
  mp9: "MP9",
};
const nice = (w: string) => NICE[w] ?? w;

function hsPct(hg: Record<string, number>): number {
  const total = Object.values(hg).reduce((a, b) => a + b, 0);
  return total ? (100 * (hg["head"] ?? 0)) / total : 0;
}

export function Weapons({ matchId }: { matchId: string }) {
  const [players, setPlayers] = useState<PlayerWeapons[] | null>(null);

  useEffect(() => {
    getWeapons(matchId)
      .then((r) => setPlayers(r.players))
      .catch(() => setPlayers([]));
  }, [matchId]);

  if (!players) return null;

  return (
    <div className="card">
      <h3>Armas y precisión</h3>
      <table className="sb">
        <colgroup>
          <col className="c-name" />
          <col className="c-name" />
          <col className="c-num" />
        </colgroup>
        <thead>
          <tr>
            <th className="txt">Jugador</th>
            <th className="txt">Arma principal</th>
            <th className="num" title="% del daño dirigido a la cabeza">
              HS dmg%
            </th>
          </tr>
        </thead>
        <tbody>
          {players.map((p) => {
            const top = p.top_weapons[0];
            return (
              <tr key={p.steamid}>
                <td className="txt pname">{p.name ?? "?"}</td>
                <td className="txt dim">
                  {top ? `${nice(top.weapon)} · ${top.kills}K · ${top.damage} dmg` : "–"}
                </td>
                <td className="num">{hsPct(p.hitgroups).toFixed(0)}%</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
