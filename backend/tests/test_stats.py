"""Tests de la capa de dominio (pura, sin DB)."""

from cs2tracker.domain import compute_stats


def test_compute_stats_basico():
    # 2 rondas. A: 2 kills (1 HS) 0 muertes; B mata a A; C asiste.
    kills = [
        {"attacker": "A", "victim": "B", "assister": "C", "headshot": True},
        {"attacker": "A", "victim": "B", "assister": None, "headshot": False},
        {"attacker": "B", "victim": "A", "assister": None, "headshot": False},
    ]
    damages = [
        {"attacker": "A", "victim": "B", "dmg_health": 100},
        {"attacker": "A", "victim": "B", "dmg_health": 100},
        {"attacker": "A", "victim": "C", "dmg_health": 40},
        {"attacker": "A", "victim": "A", "dmg_health": 15},  # self -> ignora
    ]
    res = {p.steamid: p for p in compute_stats(kills, damages, n_rounds=2)}

    assert res["A"].kills == 2
    assert res["A"].deaths == 1
    assert res["A"].hs_kills == 1
    assert res["A"].damage == 240  # self-damage excluido
    assert res["A"].adr(2) == 120.0
    assert res["A"].kd == 2.0
    assert res["A"].hs_pct == 50.0
    assert res["B"].kills == 1
    assert res["B"].deaths == 2
    assert res["C"].assists == 1
    assert res["C"].kills == 0


def test_orden_por_kills():
    kills = [
        {"attacker": "A", "victim": "B"},
        {"attacker": "A", "victim": "B"},
        {"attacker": "B", "victim": "A"},
    ]
    ordered = compute_stats(kills, [], n_rounds=1)
    assert ordered[0].steamid == "A"
    assert ordered[0].kills == 2
