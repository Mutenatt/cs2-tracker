"""Test de resolucion de equipos + marcador (con swap de bandos a la mitad)."""

from cs2tracker.domain import resolve_teams

TEAMS_AT_TICK = {
    100: {"a1": 2, "a2": 2, "b1": 3, "b2": 3},
    200: {"a1": 2, "a2": 2, "b1": 3, "b2": 3},
    300: {"a1": 3, "a2": 3, "b1": 2, "b2": 2},
}


def test_score_con_swap():
    events = [
        {"round_num": 0, "tick": 100, "winner_side": 2},
        {"round_num": 1, "tick": 200, "winner_side": 3},
        {"round_num": 2, "tick": 300, "winner_side": 3},
    ]
    r = resolve_teams(events, TEAMS_AT_TICK)
    assert r.player_roster == {"a1": 2, "a2": 2, "b1": 3, "b2": 3}
    assert r.score[2] == 2
    assert r.score[3] == 1
    assert [x["winner_roster"] for x in r.rounds] == [2, 3, 2]


def test_vacio():
    r = resolve_teams([], {})
    assert r.score == {} and r.rounds == []
