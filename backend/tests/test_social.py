"""Test de winrate 'jugando juntos'. Puro, sin DB."""

from cs2tracker.domain.social import calcular_winrate_conjunto


def test_winrate_conjunto_mezcla_victorias_y_derrotas():
    r = calcular_winrate_conjunto([{"won": True}, {"won": True}, {"won": False}, {"won": True}])
    assert r == {"matches_together": 4, "wins": 3, "losses": 1, "win_rate": 75.0}


def test_winrate_conjunto_sin_partidas():
    assert calcular_winrate_conjunto([]) == {
        "matches_together": 0,
        "wins": 0,
        "losses": 0,
        "win_rate": 0.0,
    }
