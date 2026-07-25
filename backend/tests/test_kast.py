"""Test de KAST: kill, assist, survive y trade."""

from cs2tracker.domain import compute_kast, find_trade_kills, find_traded_deaths
from cs2tracker.domain.kast import kast_rounds_for_player

TEAMS = {"A": 2, "A2": 2, "B": 3, "B2": 3}


def test_kast_componentes():
    # Ronda 0: A mata a B (kill+survive). B muere (nada). A2 sobrevive sin nada.
    # Ronda 1: B mata a A; A2 (companero) trade-ea matando a B enseguida.
    #          -> A cuenta por TRADE aunque murio. A2 por kill. B por kill+muere?
    kills = [
        {"round_num": 0, "tick": 100, "attacker": "A", "victim": "B", "assister": None},
        {"round_num": 1, "tick": 200, "attacker": "B", "victim": "A", "assister": None},
        {"round_num": 1, "tick": 260, "attacker": "A2", "victim": "B", "assister": None},
    ]
    k = compute_kast(kills, TEAMS, n_rounds=2)
    # A: ronda0 kill+survive OK; ronda1 murio pero tradeado OK -> 2/2 = 100
    assert k["A"] == 100.0
    # A2: ronda0 sobrevivio OK; ronda1 kill OK -> 100
    assert k["A2"] == 100.0
    # B: ronda0 murio sin nada; ronda1 kill (mato a A) OK -> 1/2 = 50
    assert k["B"] == 50.0
    # B2: sobrevivio las 2 -> 100
    assert k["B2"] == 100.0


def test_kast_rounds_for_player_coincide_con_compute_kast():
    # Mismas rondas que test_kast_componentes: A cuenta las 2 rondas
    # (kill+survive en la 0, tradeado en la 1); B solo la 1 (kill).
    kills = [
        {"round_num": 0, "tick": 100, "attacker": "A", "victim": "B", "assister": None},
        {"round_num": 1, "tick": 200, "attacker": "B", "victim": "A", "assister": None},
        {"round_num": 1, "tick": 260, "attacker": "A2", "victim": "B", "assister": None},
    ]
    assert kast_rounds_for_player(kills, TEAMS, "A") == {0, 1}
    assert kast_rounds_for_player(kills, TEAMS, "B") == {1}
    # B2 no aparece en ningún kill de ninguna ronda -> sobrevivió las 2.
    assert kast_rounds_for_player(kills, TEAMS, "B2") == {0, 1}


def test_trade_fuera_de_ventana():
    # A muere; el companion mata al asesino pero MUY tarde -> no cuenta como trade
    kills = [
        {"round_num": 0, "tick": 100, "attacker": "B", "victim": "A", "assister": None},
        {"round_num": 0, "tick": 100 + 999, "attacker": "A2", "victim": "B", "assister": None},
    ]
    k = compute_kast(kills, TEAMS, n_rounds=1, trade_ticks=320)
    assert k["A"] == 0.0  # murio y no fue tradeado a tiempo
    assert k["A2"] == 100.0  # kill


def test_find_traded_deaths():
    # Ronda 0: B mata a A2; A vengó a A2 matando a B enseguida -> A2 tradeada.
    # Ronda 1: B mata a A; nadie vengó a tiempo -> no tradeada.
    kills = [
        {"round_num": 0, "tick": 100, "attacker": "B", "victim": "A2", "assister": None},
        {"round_num": 0, "tick": 150, "attacker": "A", "victim": "B", "assister": None},
        {"round_num": 1, "tick": 200, "attacker": "B", "victim": "A", "assister": None},
    ]
    assert find_traded_deaths(kills, TEAMS, trade_ticks=320) == {(0, "A2")}


def test_find_trade_kills():
    # Mismo escenario que test_find_traded_deaths, pero pidiendo QUIÉN vengó:
    # A vengó a A2 (ronda 0) matando a B. Ronda 1 no tiene trade kill.
    kills = [
        {"round_num": 0, "tick": 100, "attacker": "B", "victim": "A2", "assister": None},
        {"round_num": 0, "tick": 150, "attacker": "A", "victim": "B", "assister": None},
        {"round_num": 1, "tick": 200, "attacker": "B", "victim": "A", "assister": None},
    ]
    assert find_trade_kills(kills, TEAMS, trade_ticks=320) == {(0, "A"): "A2"}


def test_find_trade_kills_fuera_de_ventana_no_cuenta():
    kills = [
        {"round_num": 0, "tick": 100, "attacker": "B", "victim": "A", "assister": None},
        {"round_num": 0, "tick": 100 + 999, "attacker": "A2", "victim": "B", "assister": None},
    ]
    assert find_trade_kills(kills, TEAMS, trade_ticks=320) == {}
