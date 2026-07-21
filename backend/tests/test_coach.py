"""Test de Coach's Corner: patrón de muerte temprana de ronda."""

from cs2tracker.domain.coach import (
    describe_early_round_deaths,
    early_round_death_pattern,
    seconds_into_round,
)


def test_seconds_into_round_calcula_delta_en_segundos():
    freeze_ticks = {0: 1000}
    assert seconds_into_round(0, 1000 + 64 * 10, freeze_ticks, tickrate=64) == 10.0


def test_seconds_into_round_sin_freeze_tick_devuelve_none():
    assert seconds_into_round(0, 5000, {}, tickrate=64) is None


def test_seconds_into_round_tick_anterior_al_freeze_devuelve_none():
    assert seconds_into_round(0, 500, {0: 1000}, tickrate=64) is None


def test_early_round_death_pattern_sin_muertes():
    p = early_round_death_pattern([])
    assert p["matches_analyzed"] == 0
    assert p["early_death_pct"] == 0.0


def test_early_round_death_pattern_detecta_muertes_tempranas():
    deaths = [
        {"match_id": "m1", "map": "de_mirage", "seconds_into_round": 5.0},
        {"match_id": "m1", "map": "de_mirage", "seconds_into_round": 40.0},
        {"match_id": "m2", "map": "de_mirage", "seconds_into_round": 8.0},
    ]
    p = early_round_death_pattern(deaths, threshold_s=15.0)
    assert p["matches_analyzed"] == 2
    assert p["total_deaths"] == 3
    assert p["early_deaths"] == 2
    assert p["early_death_pct"] == 66.7
    assert p["avg_early_death_time_s"] == 6.5
    assert p["dominant_map"] == "de_mirage"


def test_describe_early_round_deaths_sin_datos_devuelve_none():
    assert describe_early_round_deaths(early_round_death_pattern([])) is None


def test_describe_early_round_deaths_baja_confianza_con_pocas_partidas():
    deaths = [{"match_id": "m1", "map": "de_mirage", "seconds_into_round": 40.0}]
    pattern = early_round_death_pattern(deaths)
    insight = describe_early_round_deaths(pattern)
    assert insight["low_confidence"] is True
    assert "0 de 1 muertes" in insight["text"]


def test_describe_early_round_deaths_alta_confianza_con_muchas_partidas():
    deaths = [
        {"match_id": f"m{i}", "map": "de_mirage", "seconds_into_round": 5.0} for i in range(10)
    ]
    pattern = early_round_death_pattern(deaths)
    insight = describe_early_round_deaths(pattern)
    assert insight["low_confidence"] is False
    assert "100%" in insight["text"]
