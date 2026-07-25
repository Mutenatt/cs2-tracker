"""Test de agregados de Perfil (lifetime, map pool, milestones) a partir de historial."""

from cs2tracker.domain.profile import (
    accuracy_stats,
    lifetime_stats,
    map_pool,
    milestones,
    top_weapons,
    weapon_breakdown,
)

HISTORY = [
    {
        "map": "de_mirage",
        "won": True,
        "rating": 1.65,
        "adr": 133.9,
        "kd": 1.50,
        "kast": 86.4,
        "my_score": 13,
        "opponent_score": 8,
    },
    {
        "map": "de_mirage",
        "won": False,
        "rating": 1.29,
        "adr": 120.1,
        "kd": 1.23,
        "kast": 61.3,
        "my_score": 14,
        "opponent_score": 16,
    },
]


def test_lifetime_stats_promedia_todas_las_partidas():
    lt = lifetime_stats(HISTORY)
    assert lt["matches_played"] == 2
    assert lt["wins"] == 1
    assert lt["win_rate"] == 50.0
    assert lt["avg_rating"] == 1.47
    assert lt["avg_adr"] == 127.0


def test_lifetime_stats_sin_partidas():
    lt = lifetime_stats([])
    assert lt["matches_played"] == 0
    assert lt["win_rate"] == 0.0


def test_map_pool_marca_mapas_sin_datos():
    pool = map_pool(HISTORY, ["de_mirage", "de_inferno"])
    by_map = {p["map"]: p for p in pool}

    assert by_map["de_mirage"]["matches_played"] == 2
    assert by_map["de_mirage"]["wins"] == 1
    assert by_map["de_mirage"]["has_data"] is True

    assert by_map["de_inferno"]["has_data"] is False
    assert by_map["de_inferno"]["matches_played"] == 0
    assert by_map["de_inferno"]["avg_kd"] is None


def test_map_pool_ordena_con_datos_primero():
    pool = map_pool(HISTORY, ["de_inferno", "de_mirage"])
    assert [p["map"] for p in pool] == ["de_mirage", "de_inferno"]


def test_milestones_mejor_rating_y_adr():
    ms = {m["key"]: m for m in milestones(HISTORY, trade_kills_total=5)}
    assert ms["best_rating"]["value"] == "1.65"
    assert "victoria" in ms["best_rating"]["context"]
    assert ms["best_adr"]["value"] == "133.9"
    assert ms["trade_kills"]["value"] == "5"


def test_milestones_sin_partidas():
    assert milestones([], trade_kills_total=0) == []


def test_milestones_incluye_clutch_mas_grande_si_hay_uno():
    clutch = {"match_id": "m1", "map": "de_mirage", "round_num": 11, "enemies_at_start": 4}
    ms = {m["key"]: m for m in milestones(HISTORY, trade_kills_total=5, biggest_clutch=clutch)}
    assert ms["biggest_clutch"]["value"] == "1v4"
    assert "ronda 11" in ms["biggest_clutch"]["context"]


def test_milestones_sin_clutch_ganado_no_lo_incluye():
    ms = {m["key"]: m for m in milestones(HISTORY, trade_kills_total=5, biggest_clutch=None)}
    assert "biggest_clutch" not in ms


def test_map_pool_incluye_mapas_reales_fuera_del_pool_conocido():
    history = HISTORY + [
        {"map": "de_cache", "won": True, "rating": 1.0, "adr": 80.0, "kd": 1.0, "kast": 70.0}
    ]
    pool = map_pool(history, ["de_mirage"])  # de_cache no está en known_maps
    by_map = {p["map"]: p for p in pool}
    assert by_map["de_cache"]["has_data"] is True
    assert by_map["de_cache"]["matches_played"] == 1


def test_best_map_por_win_rate_y_desempate():
    from cs2tracker.domain.profile import best_map

    pool = [
        {"map": "de_mirage", "matches_played": 4, "wins": 2, "has_data": True},
        {"map": "de_nuke", "matches_played": 2, "wins": 2, "has_data": True},
        {"map": "de_dust2", "matches_played": 4, "wins": 4, "has_data": True},
        {"map": "de_train", "matches_played": 0, "wins": 0, "has_data": False},
    ]
    # dust2 y nuke tienen 100% win rate; gana dust2 por más partidas.
    assert best_map(pool) == "de_dust2"


def test_best_map_sin_datos():
    from cs2tracker.domain.profile import best_map

    assert (
        best_map([{"map": "de_train", "matches_played": 0, "wins": 0, "has_data": False}]) is None
    )
    assert best_map([]) is None


def test_rank_history_invierte_y_proyecta():
    from cs2tracker.domain.profile import rank_history

    history = [
        {
            "match_id": "m2",
            "ingested_at": "2026-02",
            "map": "de_nuke",
            "won": False,
            "rank": 12000,
            "rank_type": 11,
            "comp_wins": 20,
            "kd": 1.0,
        },
        {
            "match_id": "m1",
            "ingested_at": "2026-01",
            "map": "de_mirage",
            "won": True,
            "rank": 11500,
            "rank_type": 11,
            "comp_wins": 19,
            "kd": 2.0,
        },
    ]
    rh = rank_history(history)
    assert [p["match_id"] for p in rh] == ["m1", "m2"]  # oldest-first
    assert rh[0]["rank"] == 11500
    assert "kd" not in rh[0]  # proyección mínima


def test_rank_history_calcula_rating_after_y_delta():
    from cs2tracker.domain.profile import rank_history

    # newest-first como viene de match_history: m3 (más nueva) -> m1 (más vieja).
    history = [
        {"match_id": "m3", "rank": 12641, "rank_type": 11},
        {"match_id": "m2", "rank": 12327, "rank_type": 11},
        {"match_id": "m1", "rank": 11500, "rank_type": 11},
    ]
    rh = {p["match_id"]: p for p in rank_history(history)}
    # rating DESPUÉS de m1 = entrada de m2; delta = 12327 - 11500 = +827.
    assert rh["m1"]["rating_after"] == 12327
    assert rh["m1"]["rating_delta"] == 827
    # m2 -> m3
    assert rh["m2"]["rating_after"] == 12641
    assert rh["m2"]["rating_delta"] == 314
    # la más nueva no tiene partida siguiente: sin dato de salida.
    assert rh["m3"]["rating_after"] is None
    assert rh["m3"]["rating_delta"] is None


def test_rank_history_saltea_calibrando_y_no_premier_al_parear():
    from cs2tracker.domain.profile import rank_history

    # Entre dos Premier válidas hay una calibrando (rank 0) y una no-Premier.
    history = [
        {"match_id": "nuevo", "rank": 13000, "rank_type": 11},
        {"match_id": "no_premier", "rank": 5, "rank_type": 6},
        {"match_id": "calibrando", "rank": 0, "rank_type": 11},
        {"match_id": "viejo", "rank": 12500, "rank_type": 11},
    ]
    rh = {p["match_id"]: p for p in rank_history(history)}
    # 'viejo' se empareja con 'nuevo' salteando las dos del medio.
    assert rh["viejo"]["rating_after"] == 13000
    assert rh["viejo"]["rating_delta"] == 500
    # las inválidas no reciben delta.
    assert rh["calibrando"]["rating_delta"] is None
    assert rh["no_premier"]["rating_delta"] is None
    assert rh["nuevo"]["rating_after"] is None


def test_map_pool_losses_excluye_partidas_irresueltas():
    history = HISTORY + [
        {"map": "de_mirage", "won": None, "rating": 1.0, "adr": 80.0, "kd": 1.0, "kast": 70.0}
    ]
    pool = map_pool(history, ["de_mirage"])
    mirage = next(p for p in pool if p["map"] == "de_mirage")
    assert mirage["matches_played"] == 3
    assert mirage["wins"] == 1
    assert mirage["losses"] == 1  # la partida won=None no cuenta como derrota


def test_accuracy_stats_bucketea_por_zona():
    hitgroups = {
        "head": 20,
        "chest": 30,
        "stomach": 10,
        "generic": 5,
        "neck": 5,
        "left_arm": 5,
        "right_arm": 5,
        "left_leg": 10,
        "right_leg": 10,
    }
    acc = accuracy_stats(hitgroups, hs_pct_series=[40.0, 50.0])
    assert acc["head_hits"] == 20
    assert acc["body_hits"] == 60  # chest+stomach+generic+neck+left_arm+right_arm
    assert acc["legs_hits"] == 20
    assert acc["head_pct"] == 20.0
    assert acc["body_pct"] == 60.0
    assert acc["legs_pct"] == 20.0
    assert acc["hs_pct_series"] == [40.0, 50.0]


def test_accuracy_stats_sin_datos():
    acc = accuracy_stats({}, hs_pct_series=[])
    assert acc["head_pct"] == 0.0
    assert acc["head_hits"] == 0


def test_top_weapons_ordena_y_categoriza():
    weapons = top_weapons({"ak47": 50, "m4a1": 10, "deagle": 8, "knife": 3, "world": 1})
    assert [w["name"] for w in weapons] == ["ak47", "m4a1", "deagle"]
    assert weapons[0]["category"] == "rifle"
    assert weapons[2]["category"] == "pistol"


def test_top_weapons_corta_a_top_3():
    weapons = top_weapons({"ak47": 5, "m4a1": 4, "deagle": 3, "awp": 2})
    assert len(weapons) == 3
    assert [w["name"] for w in weapons] == ["ak47", "m4a1", "deagle"]


def test_weapon_breakdown_calcula_hs_pct_adr_y_kills_por_ronda():
    kills_by = [
        {"weapon": "ak47", "headshot": True, "distance": 500.0},
        {"weapon": "ak47", "headshot": False, "distance": 1200.0},
    ]
    deaths_by = [{"weapon": "awp"}]
    damage_by = {"ak47": 200}
    rows = weapon_breakdown(kills_by, deaths_by, damage_by, rounds_played=10)
    by_name = {r["name"]: r for r in rows}

    assert by_name["ak47"]["kills"] == 2
    assert by_name["ak47"]["hs_pct"] == 50.0
    assert by_name["ak47"]["adr"] == 20.0
    assert by_name["ak47"]["kills_per_round"] == 0.2
    assert by_name["ak47"]["category"] == "rifle"
    # 1200 unidades Hammer -> metros (0.01905 por unidad).
    assert by_name["ak47"]["longest_kill_m"] == round(1200 * 0.01905, 1)

    assert by_name["awp"]["kills"] == 0
    assert by_name["awp"]["deaths"] == 1
    assert by_name["awp"]["longest_kill_m"] == 0.0


def test_weapon_breakdown_incluye_cuchillo_como_melee():
    rows = weapon_breakdown(
        kills_by=[{"weapon": "knife", "headshot": False, "distance": 30.0}],
        deaths_by=[],
        damage_by={},
        rounds_played=5,
    )
    assert len(rows) == 1
    assert rows[0]["name"] == "knife"
    assert rows[0]["category"] == "melee"


def test_weapon_breakdown_excluye_causas_no_arma():
    rows = weapon_breakdown(
        kills_by=[{"weapon": "world", "headshot": False, "distance": None}],
        deaths_by=[{"weapon": "hegrenade"}],
        damage_by={"inferno": 40},
        rounds_played=5,
    )
    assert rows == []


def test_weapon_breakdown_sin_rondas_no_divide_por_cero():
    rows = weapon_breakdown(
        kills_by=[{"weapon": "ak47", "headshot": False, "distance": None}],
        deaths_by=[],
        damage_by={},
        rounds_played=0,
    )
    assert rows[0]["adr"] == 0.0
    assert rows[0]["kills_per_round"] == 0.0
    assert rows[0]["longest_kill_m"] == 0.0
