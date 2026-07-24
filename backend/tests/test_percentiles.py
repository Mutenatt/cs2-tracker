"""Test de percentiles globales y tags derivados. Puro, sin DB."""

from cs2tracker.domain.percentiles import (
    MIN_JUGADORES_GLOBAL,
    calcular_percentiles,
    evaluar_tags_globales,
)


def test_calcular_percentiles_lista_simple():
    p = calcular_percentiles([float(x) for x in range(1, 101)])  # 1..100
    assert p["p25"] == 25.75
    assert p["p50"] == 50.5
    assert p["p75"] == 75.25
    assert p["p90"] == 90.1


def test_calcular_percentiles_vacio_y_un_valor():
    assert calcular_percentiles([]) == {"p25": 0.0, "p50": 0.0, "p75": 0.0, "p90": 0.0}
    assert calcular_percentiles([5.0]) == {"p25": 5.0, "p50": 5.0, "p75": 5.0, "p90": 5.0}


GLOBALES = {
    "adr": {"p25": 60.0, "p50": 75.0, "p75": 90.0, "p90": 110.0},
    "entry_attempts": {"p25": 1.0, "p50": 2.0, "p75": 3.0, "p90": 4.5},
    "kill_participation": {"p25": 10.0, "p50": 14.0, "p75": 18.0, "p90": 22.0},
}


def test_evaluar_tags_por_encima_del_p75():
    stats = {"adr": 95.0, "entry_attempts": 1.0, "kill_participation": 19.0}
    tags = evaluar_tags_globales(stats, GLOBALES, n_players=50)
    assert {t["tag_id"] for t in tags} == {"maquina_de_dano", "alta_participacion"}
    maquina = next(t for t in tags if t["tag_id"] == "maquina_de_dano")
    assert maquina["detalle"] == {"valor": 95.0, "umbral": 90.0, "percentil": "p75"}


def test_evaluar_tags_guardrail_de_muestra_global():
    stats = {"adr": 500.0, "entry_attempts": 99.0, "kill_participation": 99.0}
    assert evaluar_tags_globales(stats, GLOBALES, n_players=MIN_JUGADORES_GLOBAL - 1) == []


def test_evaluar_tags_sin_metrica_no_rompe():
    assert evaluar_tags_globales({}, GLOBALES, n_players=50) == []
    assert evaluar_tags_globales({"adr": 95.0}, {}, n_players=50) == []
