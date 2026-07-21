"""Test del rating aproximado."""

from cs2tracker.domain.rating import compute_rating


def test_rating_rangos():
    # Jugador dominante -> rating alto (>1.3)
    top = compute_rating(kills=25, deaths=10, assists=6, adr=110, kast=80, n_rounds=22)
    assert top > 1.3
    # Jugador flojo -> rating bajo (<0.9)
    weak = compute_rating(kills=8, deaths=19, assists=4, adr=55, kast=50, n_rounds=22)
    assert weak < 0.9
    # Promedio ~1.0
    avg = compute_rating(kills=15, deaths=15, assists=5, adr=80, kast=70, n_rounds=22)
    assert 0.85 <= avg <= 1.2


def test_rating_no_negativo():
    assert compute_rating(0, 25, 0, 0, 0, 22) >= 0.0
