"""Test de detección de rondas 'lurker' (aislamiento + timing tardío). Puro, sin DB."""

from cs2tracker.domain.lurker import aislamiento_ronda, es_ronda_lurker, tasa_lurker

EQUIPO_JUNTO = [
    {"steamid": "b1", "u": 0.5, "v": 0.5, "seconds_into_round": 5.0},
    {"steamid": "b2", "u": 0.52, "v": 0.48, "seconds_into_round": 6.0},
]


def test_aislamiento_ronda_distancia_al_centroide():
    mi_evento = {"u": 0.9, "v": 0.9}
    d = aislamiento_ronda(mi_evento, EQUIPO_JUNTO)
    assert d == ((0.9 - 0.51) ** 2 + (0.9 - 0.49) ** 2) ** 0.5


def test_aislamiento_ronda_none_sin_coords_propias():
    assert aislamiento_ronda({"u": None, "v": None}, EQUIPO_JUNTO) is None


def test_aislamiento_ronda_none_sin_eventos_de_equipo():
    assert aislamiento_ronda({"u": 0.1, "v": 0.1}, []) is None


def test_es_ronda_lurker_requiere_tardio_y_aislado():
    tardio_y_aislado = {"u": 0.95, "v": 0.95, "seconds_into_round": 30.0}
    assert es_ronda_lurker(tardio_y_aislado, EQUIPO_JUNTO) is True

    tardio_pero_junto = {"u": 0.51, "v": 0.49, "seconds_into_round": 30.0}
    assert es_ronda_lurker(tardio_pero_junto, EQUIPO_JUNTO) is False

    aislado_pero_temprano = {"u": 0.95, "v": 0.95, "seconds_into_round": 5.0}
    assert es_ronda_lurker(aislado_pero_temprano, EQUIPO_JUNTO) is False


def test_es_ronda_lurker_sin_timing_no_dispara():
    assert (
        es_ronda_lurker({"u": 0.95, "v": 0.95, "seconds_into_round": None}, EQUIPO_JUNTO) is False
    )


def test_tasa_lurker_porcentaje_de_rondas():
    rondas = [
        {
            "mi_evento": {"u": 0.95, "v": 0.95, "seconds_into_round": 30.0},
            "eventos_equipo": EQUIPO_JUNTO,
        },
        {
            "mi_evento": {"u": 0.51, "v": 0.49, "seconds_into_round": 5.0},
            "eventos_equipo": EQUIPO_JUNTO,
        },
    ]
    assert tasa_lurker(rondas) == 50.0


def test_tasa_lurker_sin_rondas_es_cero():
    assert tasa_lurker([]) == 0.0
