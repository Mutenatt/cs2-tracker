"""Test de clasificación de economía y detección de badges derivados. Puro, sin DB."""

from cs2tracker.domain.economia import (
    clasificar_tipo_compra,
    detectar_eco_frag,
    detectar_millonario,
    es_arma_real,
    filtrar_compras_reales,
    tasa_buena_economia,
)


def test_clasificar_tipo_compra_por_umbral():
    assert clasificar_tipo_compra(4500) == "full_buy"
    assert clasificar_tipo_compra(4000) == "full_buy"
    assert clasificar_tipo_compra(3999) == "force_buy"
    assert clasificar_tipo_compra(2000) == "force_buy"
    assert clasificar_tipo_compra(1999) == "semi_eco"
    assert clasificar_tipo_compra(1000) == "semi_eco"
    assert clasificar_tipo_compra(999) == "eco"
    assert clasificar_tipo_compra(0) == "eco"


def test_tasa_buena_economia():
    assert tasa_buena_economia(["full_buy", "eco", "force_buy", "semi_eco"]) == 75.0
    assert tasa_buena_economia([]) == 0.0
    assert tasa_buena_economia(["eco", "eco"]) == 0.0


def test_detectar_eco_frag_requiere_eco_vs_full_buy():
    tipo_compra = {"a": "eco", "b": "full_buy", "c": "eco"}
    kills = [
        {"attacker": "a", "victim": "b"},  # eco mata a full_buy -> cuenta
        {"attacker": "b", "victim": "c"},  # full_buy mata a eco -> no cuenta
        {"attacker": "a", "victim": "c"},  # eco mata a eco -> no cuenta
    ]
    assert detectar_eco_frag(kills, tipo_compra) == ["a"]


def test_detectar_millonario_exige_arma_cara_y_economia_pobre():
    tipo_compra = {"a": "eco", "b": "full_buy", "c": "semi_eco"}
    compras = [
        {"steamid": "a", "item": "awp"},  # eco + arma cara -> millonario
        {"steamid": "b", "item": "awp"},  # full_buy + arma cara -> no cuenta
        {"steamid": "c", "item": "deagle"},  # arma barata -> no cuenta
        {"steamid": "c", "item": "g3sg1"},  # semi_eco + arma cara -> millonario
    ]
    resultado = detectar_millonario(compras, tipo_compra)
    assert {(r["steamid"], r["arma"]) for r in resultado} == {("a", "awp"), ("c", "g3sg1")}


def test_es_arma_real_filtra_utilidad():
    assert es_arma_real("awp") is True
    assert es_arma_real("ak47") is True
    assert es_arma_real("hegrenade") is False
    assert es_arma_real("knife") is False


FREEZE = {0: 1000}
ECONOMY = [{"round_num": 0, "steamid": "a", "cash_spent": 5000}]


def test_filtrar_compras_dentro_de_la_ventana_y_con_gasto():
    compras = [{"round_num": 0, "tick": 500, "steamid": "a", "item": "awp"}]
    assert filtrar_compras_reales(compras, FREEZE, ECONOMY) == {(0, "a"): ["awp"]}


def test_filtrar_compras_descarta_pickup_de_media_ronda():
    # tick 2000 > fin de freezetime (1000): es un drop levantado, no compra.
    compras = [{"round_num": 0, "tick": 2000, "steamid": "a", "item": "awp"}]
    assert filtrar_compras_reales(compras, FREEZE, ECONOMY) == {}


def test_filtrar_compras_descarta_sin_gasto_suficiente():
    # cash_spent 0 < precio del AWP: la levantó, no la compró.
    economy = [{"round_num": 0, "steamid": "a", "cash_spent": 0}]
    compras = [{"round_num": 0, "tick": 500, "steamid": "a", "item": "awp"}]
    assert filtrar_compras_reales(compras, FREEZE, economy) == {}


def test_filtrar_compras_descarta_no_armas_y_rondas_sin_freeze():
    compras = [
        {"round_num": 0, "tick": 500, "steamid": "a", "item": "knife"},  # no es arma
        {"round_num": 5, "tick": 500, "steamid": "a", "item": "awp"},  # ronda sin freeze tick
    ]
    assert filtrar_compras_reales(compras, FREEZE, ECONOMY) == {}
