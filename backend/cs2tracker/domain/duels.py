"""
Matriz de duelos 1v1 dentro de una partida. PURA y testeable.

Agrega kills vs deaths entre cada par de jugadores de equipos opuestos, y
expone los eventos crudos de cada duelo para el drill-down. El roster
(steamid -> team_num del bando de la primera ronda) define los pares: como el
roster es estable toda la partida (ver teams.py), los swaps de bando no
requieren lógica extra — el par se identifica por steamids.

Exclusiones: kills sin atacante (caídas/mundo), suicidios, team kills, y
jugadores fuera del roster o con team_num fuera de {2, 3} (espectadores,
bandos desconocidos).
"""

from __future__ import annotations

from dataclasses import dataclass

# team_num: 2 = T, 3 = CT (convención de CS2)

_EVENT_FIELDS = (
    "round_num",
    "tick",
    "attacker",
    "victim",
    "weapon",
    "headshot",
    "thru_smoke",
    "noscope",
    "attacker_blind",
    "distance",
    "attacker_x",
    "attacker_y",
    "victim_x",
    "victim_y",
)


@dataclass
class DuelData:
    pairs: list[dict]  # {steamid_a (team 2), steamid_b (team 3), kills_a, kills_b}
    events: list[dict]  # kills cross-team, ordenados por (round_num, tick)


def compute_duels(kills: list[dict], roster: dict[str, int]) -> DuelData:
    """
    kills: [{attacker, victim, round_num, tick, weapon, headshot, thru_smoke,
             noscope, attacker_blind, distance, attacker_x/y, victim_x/y}]
    roster: {steamid: team_num}  (bando de la primera ronda, 2/3)
    """
    team_t = sorted(sid for sid, tn in roster.items() if tn == 2)
    team_ct = sorted(sid for sid, tn in roster.items() if tn == 3)

    # kills_a[(a, b)] = veces que a (team 2) mató a b (team 3); kills_b al revés.
    counts: dict[tuple[str, str], list[int]] = {(a, b): [0, 0] for a in team_t for b in team_ct}
    events: list[dict] = []

    for k in kills:
        atk, vic = k.get("attacker"), k.get("victim")
        if atk is None or vic is None or atk == vic:
            continue
        atk_team, vic_team = roster.get(atk), roster.get(vic)
        if atk_team not in (2, 3) or vic_team not in (2, 3) or atk_team == vic_team:
            continue
        pair = (atk, vic) if atk_team == 2 else (vic, atk)
        counts[pair][0 if atk_team == 2 else 1] += 1
        events.append({f: k.get(f) for f in _EVENT_FIELDS})

    events.sort(
        key=lambda e: (
            e["round_num"] if e["round_num"] is not None else float("inf"),
            e["tick"] if e["tick"] is not None else 0,
        )
    )

    pairs = [
        {"steamid_a": a, "steamid_b": b, "kills_a": ka, "kills_b": kb}
        for (a, b), (ka, kb) in counts.items()
    ]
    return DuelData(pairs=pairs, events=events)
