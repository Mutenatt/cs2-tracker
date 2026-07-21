"""Test de agregados de Perfil (lifetime, map pool, milestones) a partir de historial."""

from cs2tracker.domain.profile import lifetime_stats, map_pool, milestones

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
