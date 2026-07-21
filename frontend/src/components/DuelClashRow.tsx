import type { DuelEvent, DuelRosterPlayer } from "../types";

type Outcome = "win" | "loss" | "tie";

interface DuelClashRowProps {
  rowPlayer: DuelRosterPlayer;
  colPlayer: DuelRosterPlayer;
  rowKills: number;
  colKills: number;
  /** Eventos ya filtrados a este 1v1 (usuario vs rival). */
  events: DuelEvent[];
  selected?: boolean;
  onSelect?: () => void;
}

// Resultado global del duelo desde la perspectiva del usuario (fila).
function outcomeOf(rowKills: number, colKills: number): Outcome {
  if (rowKills > colKills) return "win";
  if (rowKills < colKills) return "loss";
  return "tie";
}

// Arma más usada por `steamid` dentro de este 1v1.
function dominantWeapon(events: DuelEvent[], steamid: string): string | null {
  const counts = new Map<string, number>();
  for (const e of events) {
    if (e.attacker === steamid && e.weapon) {
      counts.set(e.weapon, (counts.get(e.weapon) ?? 0) + 1);
    }
  }
  let best: string | null = null;
  let bestCount = 0;
  for (const [weapon, count] of counts) {
    if (count > bestCount) {
      best = weapon;
      bestCount = count;
    }
  }
  return best;
}

// Primer kill de cada ronda del 1v1: cuántas rondas abrió cada lado.
function entryDuels(events: DuelEvent[], rowSteamid: string): [number, number] {
  const firstByRound = new Map<number, DuelEvent>();
  for (const e of events) {
    const round = e.round_num ?? -1;
    const prev = firstByRound.get(round);
    if (!prev || (e.tick ?? 0) < (prev.tick ?? 0)) firstByRound.set(round, e);
  }
  let user = 0;
  let enemy = 0;
  for (const first of firstByRound.values()) {
    if (first.attacker === rowSteamid) user++;
    else enemy++;
  }
  return [user, enemy];
}

function initialOf(name: string): string {
  return name.trim().charAt(0).toUpperCase() || "?";
}

// Avatar de Steam si la API lo resolvió; si no, la inicial del nombre.
function Avatar({ player }: { player: DuelRosterPlayer }) {
  return (
    <span className="clash-avatar" aria-hidden="true">
      {player.avatar_url ? (
        <img src={player.avatar_url} alt="" loading="lazy" />
      ) : (
        initialOf(player.name ?? "?")
      )}
    </span>
  );
}

// Punto único de sustitución para los SVG de armas: cuando existan los
// componentes por arma (<Ak47Icon />, <AwpIcon />...), resolver aquí cuál
// renderizar según `weapon` en lugar del nombre en texto.
function WeaponIcon({ weapon }: { weapon: string | null }) {
  return (
    <span className={`clash-weapon${weapon ? "" : " empty"}`} title={weapon ?? undefined}>
      {weapon ?? "—"}
    </span>
  );
}

// Fila "Weapon Clash" del Head to Head (Simple View): usuario vs un rival,
// con las kills de cada lado y el arma dominante de cada uno al centro.
export function DuelClashRow({
  rowPlayer,
  colPlayer,
  rowKills,
  colKills,
  events,
  selected = false,
  onSelect,
}: DuelClashRowProps) {
  const outcome = outcomeOf(rowKills, colKills);
  const enemyOutcome: Outcome = outcome === "win" ? "loss" : outcome === "loss" ? "win" : "tie";
  const userName = rowPlayer.name ?? "?";
  const enemyName = colPlayer.name ?? "?";
  const userWeapon = dominantWeapon(events, rowPlayer.steamid);
  const enemyWeapon = dominantWeapon(events, colPlayer.steamid);
  const [userEntries, enemyEntries] = entryDuels(events, rowPlayer.steamid);

  return (
    <button
      type="button"
      className={`clash-row ${outcome}${selected ? " selected" : ""}`}
      onClick={onSelect}
      aria-label={`Duelo: ${userName} ${rowKills} – ${colKills} ${enemyName}`}
    >
      {/* Columna izquierda: usuario */}
      <span className="clash-side user">
        <span className="clash-id">
          <Avatar player={rowPlayer} />
          <span className="clash-name">{userName}</span>
        </span>
        <span className={`clash-kills mono ${outcome}`}>{rowKills}</span>
      </span>

      {/* Columna central: Weapon Clash Zone */}
      <span className="clash-center">
        <span className="clash-weapons">
          <WeaponIcon weapon={userWeapon} />
          <span className="clash-vs">vs</span>
          <WeaponIcon weapon={enemyWeapon} />
        </span>
        {(userEntries > 0 || enemyEntries > 0) && (
          <span className="clash-entries mono">
            First kills: {userEntries} – {enemyEntries}
          </span>
        )}
      </span>

      {/* Columna derecha: rival (espejo de la izquierda) */}
      <span className="clash-side enemy">
        <span className="clash-id">
          <Avatar player={colPlayer} />
          <span className="clash-name">{enemyName}</span>
        </span>
        <span className={`clash-kills mono ${enemyOutcome}`}>{colKills}</span>
      </span>
    </button>
  );
}
