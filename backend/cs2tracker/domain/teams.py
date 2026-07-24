"""
Resolución de equipos (rosters) y marcador. PURA y testeable.

Los rosters son estables toda la partida; solo cambian de bando (CT<->T) a la
mitad (y en overtime). Por eso identificamos el roster por su bando en la
PRIMERA ronda, y para cada ronda ganada miramos qué roster estaba en el bando
ganador en ese momento. Así el marcador queda bien aunque haya swaps.
"""

from __future__ import annotations

from dataclasses import dataclass

# team_num: 2 = T, 3 = CT (convención de CS2)


@dataclass
class TeamResolution:
    player_roster: dict[str, int]  # steamid -> roster_id (bando 1a ronda: 2/3)
    rounds: list[dict]  # {round_num, tick, winner_roster, attacker_roster}
    score: dict[int, int]  # roster_id -> rondas ganadas


def resolve_teams(
    round_events: list[dict],
    teams_at_tick: dict[int, dict[str, int]],
) -> TeamResolution:
    """
    round_events: [{round_num, tick, winner_side}]  winner_side in {2,3}
    teams_at_tick: {tick: {steamid: team_num}}  (team_num de cada jugador en ese tick)
    """
    if not round_events:
        return TeamResolution({}, [], {})

    first_tick = min(e["tick"] for e in round_events)
    # roster de cada jugador = su bando en la primera ronda (estable)
    player_roster = dict(teams_at_tick.get(first_tick, {}))

    rounds: list[dict] = []
    score: dict[int, int] = {}
    for e in sorted(round_events, key=lambda x: x["round_num"]):
        side = e["winner_side"]
        at = teams_at_tick.get(e["tick"], {})
        # cualquier jugador que esté en el bando ganador en ese tick -> su roster
        winner_roster = next(
            (player_roster.get(sid) for sid, t in at.items() if t == side and sid in player_roster),
            None,
        )
        # Mismo lookup pero fijo al bando T (2, convención de arriba) -- qué
        # roster atacaba esa ronda. Insumo de domain/lurker.py: el rol solo
        # se evalúa en rondas de ataque.
        attacker_roster = next(
            (player_roster.get(sid) for sid, t in at.items() if t == 2 and sid in player_roster),
            None,
        )
        rounds.append(
            {
                "round_num": e["round_num"],
                "tick": e["tick"],
                "winner_roster": winner_roster,
                "attacker_roster": attacker_roster,
            }
        )
        if winner_roster is not None:
            score[winner_roster] = score.get(winner_roster, 0) + 1

    return TeamResolution(player_roster, rounds, score)
