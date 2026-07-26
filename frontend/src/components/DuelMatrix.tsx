import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { getMatchDuels } from "../api";
import { cardRise, staggerList } from "./motion/presets";
import { DuelClashRow } from "./DuelClashRow";
import type { DuelEvent, DuelRosterPlayer, DuelsResponse } from "../types";

const RADAR_SIZE = 256;

const FLAG_LABEL: [
  keyof Pick<DuelEvent, "headshot" | "thru_smoke" | "noscope" | "attacker_blind">,
  string,
][] = [
  ["headshot", "HS"],
  ["thru_smoke", "humo"],
  ["noscope", "noscope"],
  ["attacker_blind", "ciego"],
];

type Pair = { row: DuelRosterPlayer; col: DuelRosterPlayer };

// Mini-radar del drill-down: radar del mapa + un punto por duelo en la
// posición de la víctima (verde = ganó el jugador-fila, rojo = lo ganó el
// rival), con una línea tenue hacia la posición del atacante si existe.
function DuelRadar({
  map,
  events,
  rowSteamid,
}: {
  map: string;
  events: DuelEvent[];
  rowSteamid: string;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const ctx = canvasRef.current?.getContext("2d");
    if (!ctx) return;

    const img = new Image();
    img.onload = () => {
      if (cancelled) return;
      ctx.clearRect(0, 0, RADAR_SIZE, RADAR_SIZE);
      ctx.globalAlpha = 0.5;
      ctx.drawImage(img, 0, 0, RADAR_SIZE, RADAR_SIZE);
      ctx.globalAlpha = 1;

      let drawnAny = false;
      for (const e of events) {
        if (e.victim_u === null || e.victim_v === null) continue;
        drawnAny = true;
        const won = e.attacker === rowSteamid;
        const color = won ? "rgba(70,224,160,0.9)" : "rgba(255,84,112,0.9)";
        const vx = e.victim_u * RADAR_SIZE;
        const vy = e.victim_v * RADAR_SIZE;
        if (e.attacker_u !== null && e.attacker_v !== null) {
          ctx.strokeStyle = won ? "rgba(70,224,160,0.25)" : "rgba(255,84,112,0.25)";
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(e.attacker_u * RADAR_SIZE, e.attacker_v * RADAR_SIZE);
          ctx.lineTo(vx, vy);
          ctx.stroke();
        }
        ctx.fillStyle = color;
        ctx.beginPath();
        ctx.arc(vx, vy, 4, 0, Math.PI * 2);
        ctx.fill();
      }
      setMsg(drawnAny ? null : "Sin datos de posición");
    };
    img.onerror = () => {
      if (!cancelled) setMsg(`Sin radar para ${map}`);
    };
    img.src = `/radar/${map}_radar_psd.png`;

    return () => {
      cancelled = true;
    };
  }, [map, events, rowSteamid]);

  return (
    <div className="duel-radar">
      <div className="map-frame">
        <canvas ref={canvasRef} width={RADAR_SIZE} height={RADAR_SIZE} />
      </div>
      {msg && <div className="muted">{msg}</div>}
    </div>
  );
}

function DuelDrilldown({
  pair,
  events,
  map,
  hasRadar,
}: {
  pair: Pair;
  events: DuelEvent[];
  map: string | null;
  hasRadar: boolean;
}) {
  const { row, col } = pair;
  const shortName = (p: DuelRosterPlayer): string => p.name ?? "?";
  const pairEvents = events.filter(
    (e) =>
      (e.attacker === row.steamid && e.victim === col.steamid) ||
      (e.attacker === col.steamid && e.victim === row.steamid)
  );

  return (
    <div className="duel-drilldown">
      <div className="duel-dd-title mono">
        {shortName(row)} vs {shortName(col)}
      </div>
      {pairEvents.length === 0 ? (
        <div className="section-note" style={{ marginTop: 6 }}>
          Nunca se cruzaron en esta partida.
        </div>
      ) : (
        <div className="duel-dd-body">
          <div className="duel-events">
            {pairEvents.map((e, i) => {
              const rowWon = e.attacker === row.steamid;
              return (
                <div className={`duel-event${rowWon ? " won" : " lost"}`} key={i}>
                  <span className="de-round mono">
                    Ronda {e.round_num !== null ? e.round_num : "—"}
                  </span>
                  <span className="de-who">
                    {rowWon ? shortName(row) : shortName(col)} →{" "}
                    {rowWon ? shortName(col) : shortName(row)}
                  </span>
                  <span className="de-weapon mono">{e.weapon ?? "?"}</span>
                  <span className="de-flags">
                    {FLAG_LABEL.filter(([f]) => e[f]).map(([f, label]) => (
                      <span className="duel-flag" key={f}>
                        {label}
                      </span>
                    ))}
                    {e.distance !== null && (
                      <span className="de-dist mono">{e.distance.toFixed(0)}</span>
                    )}
                  </span>
                </div>
              );
            })}
          </div>
          {hasRadar && map ? (
            <DuelRadar map={map} events={pairEvents} rowSteamid={row.steamid} />
          ) : (
            <div className="section-note">Sin radar para este mapa.</div>
          )}
        </div>
      )}
      <div className="section-note" style={{ marginTop: 10 }}>
        Verde = duelo ganado por {shortName(row)}. Rojo = ganado por {shortName(col)}. El punto
        marca dónde murió la víctima; la línea tenue, desde dónde disparó el atacante.
      </div>
    </div>
  );
}

// Matriz de duelos por partida: kills vs deaths contra cada rival. Click en
// una celda abre el drill-down 1v1 (timeline por ronda + mini-radar).
export function DuelMatrix({ matchId, mySteamid }: { matchId: string; mySteamid?: string }) {
  const [data, setData] = useState<DuelsResponse | null>(null);
  const [selected, setSelected] = useState<Pair | null>(null);

  useEffect(() => {
    let cancelled = false;
    setData(null);
    setSelected(null);
    (async () => {
      try {
        const r = await getMatchDuels(matchId);
        if (!cancelled) setData(r);
      } catch {
        if (!cancelled) setData(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [matchId]);

  // Filas = los duelos del usuario actual vs enemigos (Simple View).
  // Se construye a partir de all cells, filtrados por mySteamid.
  const view = useMemo(() => {
    if (!data || data.teams.length < 2 || !mySteamid) return null;
    const [t2, t3] = data.teams;
    if (t2.players.length === 0 || t3.players.length === 0) return null;

    // Encontrar equipo del usuario
    const meInT3 = t3.players.some((p) => p.steamid === mySteamid);
    const myTeam = meInT3 ? t3 : t2;
    const enemyTeam = meInT3 ? t2 : t3;

    // Buscar el jugador actual
    const me = myTeam.players.find((p) => p.steamid === mySteamid);
    if (!me) return null;

    // Construir filas: yo vs cada enemigo
    const rows = enemyTeam.players.map((enemy) => {
      const cell = data.cells.find(
        (c) =>
          (c.steamid_a === me.steamid && c.steamid_b === enemy.steamid) ||
          (c.steamid_a === enemy.steamid && c.steamid_b === me.steamid)
      );

      const [myKills, enemyKills] =
        cell && cell.steamid_a === me.steamid
          ? [cell.kills_a, cell.kills_b]
          : cell && cell.steamid_b === me.steamid
            ? [cell.kills_b, cell.kills_a]
            : [0, 0];

      // Filtrar eventos de este duelo específico
      const duelEvents = data.events.filter(
        (e) =>
          (e.attacker === me.steamid && e.victim === enemy.steamid) ||
          (e.attacker === enemy.steamid && e.victim === me.steamid)
      );

      return { me, enemy, myKills, enemyKills, duelEvents };
    });

    return { rows };
  }, [data, mySteamid]);

  if (!data || !view) return null;
  const { rows } = view;

  return (
    <>
      <div className="section-head">
        <span className="display">Duelos</span>
        <span className="rule" />
      </div>
      <motion.div className="clash-list" variants={staggerList} initial="hidden" animate="show">
        {rows.map((row) => {
          const isSelected =
            selected?.row.steamid === row.me.steamid && selected?.col.steamid === row.enemy.steamid;
          return (
            <motion.div key={row.enemy.steamid} variants={cardRise}>
              <DuelClashRow
                rowPlayer={row.me}
                colPlayer={row.enemy}
                rowKills={row.myKills}
                colKills={row.enemyKills}
                events={row.duelEvents}
                selected={isSelected}
                onSelect={() => setSelected(isSelected ? null : { row: row.me, col: row.enemy })}
              />
            </motion.div>
          );
        })}
      </motion.div>
      <div className="section-note" style={{ marginTop: 8 }}>
        Tus duelos contra cada rival en esta partida. Click en una fila para ver el detalle del 1v1
        (timeline + mapa).
      </div>
      <AnimatePresence initial={false}>
        {selected && (
          <motion.div
            key={`${selected.row.steamid}-${selected.col.steamid}`}
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.25, ease: "easeOut" }}
            style={{ overflow: "hidden" }}
          >
            <DuelDrilldown
              pair={selected}
              events={data.events}
              map={data.map}
              hasRadar={data.has_radar}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
