"""Test de entry / multikills / clutch."""

from cs2tracker.domain.rounds import (
    compute_round_stats,
    find_clutch_situations,
    find_entry_events,
)

TEAMS = {"A": 2, "A2": 2, "B": 3, "B2": 3}


def test_entry_multikill_clutch():
    # Ronda 0: B mata a A2 (entry). Luego A mata a B y a B2 -> A gana 1v2, clutch.
    kills = [
        {"round_num": 0, "tick": 100, "attacker": "B", "victim": "A2"},
        {"round_num": 0, "tick": 150, "attacker": "A", "victim": "B"},
        {"round_num": 0, "tick": 200, "attacker": "A", "victim": "B2"},
    ]
    res = compute_round_stats(kills, TEAMS, {0: 2})  # gana roster 2

    assert res["B"]["entry_kills"] == 1
    assert res["A2"]["entry_deaths"] == 1
    assert res["A"]["k2"] == 1  # 2 kills en la ronda
    assert res["A"]["clutches"] == 1  # quedo 1v2 y gano
    assert res["B"]["clutches"] == 0


def test_clutch_no_cuenta_si_pierde():
    # A queda 1v2 pero su equipo pierde la ronda -> sin clutch
    kills = [
        {"round_num": 0, "tick": 100, "attacker": "B", "victim": "A2"},
        {"round_num": 0, "tick": 200, "attacker": "B", "victim": "A"},
    ]
    res = compute_round_stats(kills, TEAMS, {0: 3})  # gana roster 3
    assert res["A"]["clutches"] == 0


def test_find_entry_events():
    # Ronda 0: primera muerte es A2 (tick 100). Ronda 1: primera es B (tick 50).
    kills = [
        {"round_num": 0, "tick": 100, "attacker": "B", "victim": "A2"},
        {"round_num": 0, "tick": 150, "attacker": "A", "victim": "B"},
        {"round_num": 1, "tick": 200, "attacker": "A", "victim": "B2"},
        {"round_num": 1, "tick": 50, "attacker": "B", "victim": "A"},
    ]
    assert find_entry_events(kills) == {(0, "A2"), (1, "A")}


def test_find_clutch_situations_ganada_y_perdida():
    # Ronda 0: A queda 1v2 (mata a B y B2) y su equipo gana -> clutch ganado.
    # La misma secuencia también deja a B2 en un 1v1 justo antes de morir
    # (equipo B llega a su último vivo con A todavía en pie) -> se registra
    # como clutch PERDIDO para B2, aunque termine casi al instante: el
    # algoritmo marca la situación en cuanto un roster queda en 1vX, no solo
    # a los intentos que "duran" -- igual que un tracker real contaría un
    # 1v1 relámpago perdido.
    # Ronda 1: A vuelve a quedar 1vX pero esta vez pierde -> clutch perdido.
    kills = [
        {"round_num": 0, "tick": 100, "attacker": "B", "victim": "A2"},
        {"round_num": 0, "tick": 150, "attacker": "A", "victim": "B"},
        {"round_num": 0, "tick": 200, "attacker": "A", "victim": "B2"},
        {"round_num": 1, "tick": 100, "attacker": "B", "victim": "A2"},
        {"round_num": 1, "tick": 200, "attacker": "B", "victim": "A"},
    ]
    situations = find_clutch_situations(kills, TEAMS, {0: 2, 1: 3})
    assert situations == [
        {"round_num": 0, "steamid": "A", "enemies_at_start": 2, "outcome": "won"},
        {"round_num": 0, "steamid": "B2", "enemies_at_start": 1, "outcome": "lost"},
        {"round_num": 1, "steamid": "A", "enemies_at_start": 2, "outcome": "lost"},
    ]


def test_find_clutch_situations_sin_situaciones():
    # Equipos de 3: una sola muerte no deja a ningún roster en su último
    # vivo todavía -> ninguna situación de clutch detectada.
    teams3 = {"A": 2, "A2": 2, "A3": 2, "B": 3, "B2": 3, "B3": 3}
    kills = [{"round_num": 0, "tick": 100, "attacker": "A", "victim": "B"}]
    assert find_clutch_situations(kills, teams3, {0: 2}) == []
