"""
KAST: % de rondas donde el jugador tuvo Kill, Assist, Survived o fue Traded.
PURA y testeable. Recibe kills como dicts (round_num, tick, attacker, victim,
assister) + el equipo de cada jugador (para detectar el trade por compañero).

Trade: el jugador murió, y un COMPAÑERO mató a su asesino dentro de una ventana
de tiempo (trade_ticks) después de su muerte. Un jugador muere a lo sumo una vez
por ronda (sin respawn en competitivo), así que buscamos su muerte única.
"""

from __future__ import annotations

from collections.abc import Iterable

DEFAULT_TRADE_TICKS = 320  # ~5s a 64 tick


def _was_traded(
    killer: str | None,
    dtick: int,
    team: int | None,
    round_kills: list[dict],
    teams: dict[str, int],
    trade_ticks: int,
) -> bool:
    """Un compañero del mismo `team` mató a `killer` dentro de la ventana."""
    return any(
        k.get("victim") == killer
        and teams.get(k.get("attacker")) == team
        and team is not None
        and 0 <= (k.get("tick") or 0) - dtick <= trade_ticks
        for k in round_kills
    )


def find_traded_deaths(
    kills: Iterable[dict],
    teams: dict[str, int],
    trade_ticks: int = DEFAULT_TRADE_TICKS,
) -> set[tuple[int, str]]:
    """(round_num, victim) de las muertes vengadas por un compañero dentro de
    la ventana de trade.

    A diferencia de KAST (que cuenta "ok" si el jugador tuvo kill/assist/
    supervivencia O trade), esto identifica la muerte tradeada en sí, sin
    importar si esa ronda ya contaba para KAST por otro lado. Usado para
    marcar `is_traded` en player_map_events por evento, no solo el % agregado.
    """
    by_round: dict[int, list[dict]] = {}
    for k in kills:
        by_round.setdefault(k.get("round_num"), []).append(k)

    traded: set[tuple[int, str]] = set()
    for rnd, rk in by_round.items():
        killer_of: dict[str, dict] = {}
        for k in rk:
            if k.get("victim"):
                killer_of[k["victim"]] = k
        for victim, death in killer_of.items():
            killer = death.get("attacker")
            dtick = death.get("tick") or 0
            team = teams.get(victim)
            if _was_traded(killer, dtick, team, rk, teams, trade_ticks):
                traded.add((rnd, victim))
    return traded


def find_trade_kills(
    kills: Iterable[dict],
    teams: dict[str, int],
    trade_ticks: int = DEFAULT_TRADE_TICKS,
) -> dict[tuple[int, str], str]:
    """(round_num, avenger_steamid) -> avenged_steamid: quién vengó a quién.

    Mismo criterio/ventana que find_traded_deaths, pero desde la perspectiva
    del vengador -- esa función solo marca que una muerte fue vengada por
    ALGUIEN, esta identifica POR QUIÉN. Necesario para atribuirle la trade
    kill a un jugador puntual (milestone lifetime, `trade_efficiency`
    par-a-par de Squad & Rivals)."""
    by_round: dict[int, list[dict]] = {}
    for k in kills:
        by_round.setdefault(k.get("round_num"), []).append(k)

    result: dict[tuple[int, str], str] = {}
    for rnd, rk in by_round.items():
        rk_sorted = sorted(rk, key=lambda k: k.get("tick") or 0)
        killer_of: dict[str, dict] = {}
        for k in rk_sorted:
            if k.get("victim"):
                killer_of[k["victim"]] = k

        for victim, death in killer_of.items():
            killer = death.get("attacker")
            dtick = death.get("tick") or 0
            team = teams.get(victim)
            if killer is None or team is None:
                continue
            for k in rk_sorted:
                is_revenge = (
                    k.get("victim") == killer
                    and teams.get(k.get("attacker")) == team
                    and 0 <= (k.get("tick") or 0) - dtick <= trade_ticks
                )
                if is_revenge:
                    avenger = k.get("attacker")
                    if avenger:
                        result[(rnd, avenger)] = victim
                    break
    return result


def kast_rounds_for_player(
    kills: Iterable[dict],
    teams: dict[str, int],
    steamid: str,
    trade_ticks: int = DEFAULT_TRADE_TICKS,
) -> set[int]:
    """round_num de las rondas donde `steamid` tuvo Kill/Assist/Survived o
    fue Traded, de UNA partida. Misma lógica que compute_kast, pero para un
    solo jugador y devolviendo el set de rondas en vez del %agregado de
    todos -- lo usa domain/loadouts.py vía api/queries.py para bucketear
    KAST por tipo de compra (necesita saber EN QUÉ rondas, no solo cuántas)."""
    by_round: dict[int, list[dict]] = {}
    for k in kills:
        by_round.setdefault(k.get("round_num"), []).append(k)

    out: set[int] = set()
    for rnd, rk in by_round.items():
        if rnd is None:
            continue
        got_kill = any(k.get("attacker") == steamid for k in rk)
        got_assist = any(k.get("assister") == steamid for k in rk)
        died = any(k.get("victim") == steamid for k in rk)
        ok = got_kill or got_assist or not died
        if not ok:
            death = next(k for k in rk if k.get("victim") == steamid)
            killer = death.get("attacker")
            dtick = death.get("tick") or 0
            team = teams.get(steamid)
            ok = _was_traded(killer, dtick, team, rk, teams, trade_ticks)
        if ok:
            out.add(rnd)
    return out


def compute_kast(
    kills: Iterable[dict],
    teams: dict[str, int],
    n_rounds: int,
    trade_ticks: int = DEFAULT_TRADE_TICKS,
) -> dict[str, float]:
    """Devuelve steamid -> KAST% (0..100)."""
    kills = list(kills)
    players = (
        set(teams)
        | {k["attacker"] for k in kills if k.get("attacker")}
        | {k["victim"] for k in kills if k.get("victim")}
    )
    players.discard(None)

    # agrupar por ronda
    by_round: dict[int, list[dict]] = {}
    for k in kills:
        by_round.setdefault(k.get("round_num"), []).append(k)

    # contar rondas KAST por jugador
    kast_rounds: dict[str, int] = {p: 0 for p in players}
    for _rnd, rk in by_round.items():
        got_kill = {k["attacker"] for k in rk if k.get("attacker")}
        got_assist = {k["assister"] for k in rk if k.get("assister")}
        died = {k["victim"] for k in rk if k.get("victim")}
        # muerte y asesino de cada víctima (última si hubiese varias)
        killer_of: dict[str, dict] = {}
        for k in rk:
            if k.get("victim"):
                killer_of[k["victim"]] = k

        for p in players:
            ok = p in got_kill or p in got_assist or p not in died
            if not ok and p in killer_of:  # revisar trade
                death = killer_of[p]
                killer = death.get("attacker")
                dtick = death.get("tick") or 0
                team = teams.get(p)
                ok = _was_traded(killer, dtick, team, rk, teams, trade_ticks)
            if ok:
                kast_rounds[p] += 1

    rounds = max(n_rounds, 1)
    return {p: round(100.0 * n / rounds, 1) for p, n in kast_rounds.items()}
