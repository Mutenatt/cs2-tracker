"""
Stats por ronda: entry duels (FK/FD), multikills (2K-5K) y clutches (1vX ganados).
PURA. Reconstruye el estado de "vivos" solo a partir de las muertes.

- Entry kill/death: primera muerte de la ronda (por tick).
- Multikill: si un jugador hace N kills en una ronda (2<=N<=5) suma un kN.
  Una ronda de 3 kills cuenta como UN 3K (no tambien 2K).
- Clutch ganado: el jugador quedo ultimo vivo de su equipo con >=1 enemigo vivo
  (1vX) y su equipo GANO la ronda.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable


def find_entry_events(kills: Iterable[dict]) -> set[tuple[int, str]]:
    """(round_num, victim) de la primera muerte de cada ronda (por tick).

    Identifica la entry kill/death de forma única sin depender de un id de
    evento: un jugador muere a lo sumo una vez por ronda (sin respawn en
    competitivo), mismo supuesto que domain/kast.py. Usado para marcar
    `is_entry` en player_map_events sin reimplementar compute_round_stats.
    """
    by_round: dict[int, list[dict]] = defaultdict(list)
    for k in kills:
        by_round[k.get("round_num")].append(k)

    entries: set[tuple[int, str]] = set()
    for rnd, rk in by_round.items():
        first = sorted(rk, key=lambda k: k.get("tick") or 0)[0]
        vic = first.get("victim")
        if vic:
            entries.add((rnd, vic))
    return entries


def _clutch_starts(
    rk_sorted: list[dict],
    rosters: dict[int, set[str]],
) -> dict[int, tuple[str, int]]:
    """Por roster: (jugador que quedó último vivo, enemigos vivos en ese
    momento), la PRIMERA vez que ese roster llega a 1vX (>=1 enemigo vivo)
    en la ronda. Compartido por compute_round_stats (solo cuenta las
    ganadas) y find_clutch_situations (ganadas y perdidas, con detalle)."""
    alive = {r: set(s) for r, s in rosters.items()}
    clutch_start: dict[int, tuple[str, int]] = {}
    for k in rk_sorted:
        v = k.get("victim")
        if v:
            for r in alive:
                alive[r].discard(v)
        for r in alive:
            enemies = sum(len(alive[o]) for o in alive if o != r)
            if len(alive[r]) == 1 and enemies >= 1 and r not in clutch_start:
                clutch_start[r] = (next(iter(alive[r])), enemies)
    return clutch_start


def compute_round_stats(
    kills: Iterable[dict],
    teams: dict[str, int],
    round_winners: dict[int, int | None],
) -> dict[str, dict]:
    kills = list(kills)
    rosters: dict[int, set[str]] = defaultdict(set)
    for sid, r in teams.items():
        rosters[r].add(sid)

    def blank():
        return {
            "entry_kills": 0,
            "entry_deaths": 0,
            "k2": 0,
            "k3": 0,
            "k4": 0,
            "k5": 0,
            "clutches": 0,
        }

    res: dict[str, dict] = {p: blank() for p in teams}

    by_round: dict[int, list[dict]] = defaultdict(list)
    for k in kills:
        by_round[k.get("round_num")].append(k)

    for rnd, rk in by_round.items():
        rk_sorted = sorted(rk, key=lambda k: k.get("tick") or 0)

        # --- entry (primera muerte de la ronda) ---
        first = rk_sorted[0]
        atk, vic = first.get("attacker"), first.get("victim")
        if atk in res and atk != vic:
            res[atk]["entry_kills"] += 1
        if vic in res:
            res[vic]["entry_deaths"] += 1

        # --- multikills ---
        kills_by_atk: dict[str, int] = defaultdict(int)
        for k in rk:
            a, v = k.get("attacker"), k.get("victim")
            if a and a != v and a in res:
                kills_by_atk[a] += 1
        for a, n in kills_by_atk.items():
            if n >= 2:
                res[a]["k" + str(min(n, 5))] += 1

        # --- clutch (1vX -> gano la ronda) ---
        clutch_start = _clutch_starts(rk_sorted, rosters)
        winner = round_winners.get(rnd)
        if winner in clutch_start:
            res[clutch_start[winner][0]]["clutches"] += 1

    return res


def find_clutch_situations(
    kills: Iterable[dict],
    teams: dict[str, int],
    round_winners: dict[int, int | None],
) -> list[dict]:
    """Una entrada por CADA situación 1vX detectada -- ganada o perdida, a
    diferencia de compute_round_stats (que solo cuenta un conteo agregado de
    las ganadas). Insumo del Clutch Timeline y de la milestone "clutch más
    grande ganado" en el Perfil.

    Devuelve: [{round_num, steamid, enemies_at_start, outcome: 'won'|'lost'}]
    """
    rosters: dict[int, set[str]] = defaultdict(set)
    for sid, r in teams.items():
        rosters[r].add(sid)

    by_round: dict[int, list[dict]] = defaultdict(list)
    for k in kills:
        by_round[k.get("round_num")].append(k)

    situations: list[dict] = []
    for rnd, rk in by_round.items():
        rk_sorted = sorted(rk, key=lambda k: k.get("tick") or 0)
        clutch_start = _clutch_starts(rk_sorted, rosters)
        winner = round_winners.get(rnd)
        for roster, (player, enemies) in clutch_start.items():
            situations.append(
                {
                    "round_num": rnd,
                    "steamid": player,
                    "enemies_at_start": enemies,
                    "outcome": "won" if roster == winner else "lost",
                }
            )
    situations.sort(key=lambda s: s["round_num"])
    return situations
