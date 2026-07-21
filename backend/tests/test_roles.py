"""Test de inferencia del rol dominante (umbrales y orden de especificidad)."""

from cs2tracker.domain import dominant_role


def _role(**overrides):
    base = {
        "matches_played": 10,
        "total_kills": 100,
        "awp_kills": 0,
        "entry_kills": 0,
        "entry_deaths": 0,
        "effective_flashes": 0,
    }
    base.update(overrides)
    return dominant_role(**base)


def test_awper_por_share_de_awp():
    assert _role(awp_kills=35) == "awper"  # 35/100 = umbral exacto


def test_awper_tiene_prioridad_sobre_entry():
    assert _role(awp_kills=50, entry_kills=30, entry_deaths=20) == "awper"


def test_entry_por_duelos_de_apertura():
    # (20 + 10) / 10 partidas = 3.0 aperturas por partida
    assert _role(entry_kills=20, entry_deaths=10) == "entry"


def test_support_por_flashes_efectivas():
    assert _role(effective_flashes=30) == "support"


def test_rifler_por_defecto():
    assert _role(awp_kills=10, entry_kills=5, entry_deaths=4, effective_flashes=9) == "rifler"


def test_sin_partidas_devuelve_none():
    assert _role(matches_played=0) is None


def test_umbral_exacto_cuenta():
    assert _role(awp_kills=34) == "rifler"  # 0.34 < 0.35
    assert _role(entry_kills=29, entry_deaths=0) == "rifler"  # 2.9 < 3.0
    assert _role(effective_flashes=29) == "rifler"  # 2.9 < 3.0


def test_cero_kills_no_divide_por_cero():
    assert _role(total_kills=0, awp_kills=0) == "rifler"
