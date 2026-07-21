"""Test de la matriz de duelos 1v1 (agregación + exclusiones + orden)."""

from cs2tracker.domain import compute_duels

ROSTER = {"a1": 2, "a2": 2, "b1": 3, "b2": 3}


def _kill(atk, vic, round_num=0, tick=100, **extra):
    base = {
        "attacker": atk,
        "victim": vic,
        "round_num": round_num,
        "tick": tick,
        "weapon": "ak47",
        "headshot": False,
        "thru_smoke": False,
        "noscope": False,
        "attacker_blind": False,
        "distance": 10.0,
        "attacker_x": 0.0,
        "attacker_y": 0.0,
        "victim_x": 1.0,
        "victim_y": 1.0,
    }
    base.update(extra)
    return base


def _pair(pairs, a, b):
    return next(p for p in pairs if p["steamid_a"] == a and p["steamid_b"] == b)


def test_agregacion_basica():
    kills = [
        _kill("a1", "b1", round_num=0, tick=100),
        _kill("a1", "b1", round_num=2, tick=300),
        _kill("b1", "a1", round_num=1, tick=200),
    ]
    r = compute_duels(kills, ROSTER)
    p = _pair(r.pairs, "a1", "b1")
    assert p["kills_a"] == 2 and p["kills_b"] == 1
    assert len(r.events) == 3
    assert [e["round_num"] for e in r.events] == [0, 1, 2]


def test_excluye_team_kills():
    r = compute_duels([_kill("a1", "a2")], ROSTER)
    assert all(p["kills_a"] == 0 and p["kills_b"] == 0 for p in r.pairs)
    assert r.events == []


def test_excluye_attacker_null():
    r = compute_duels([_kill(None, "b1")], ROSTER)
    assert all(p["kills_a"] == 0 and p["kills_b"] == 0 for p in r.pairs)
    assert r.events == []


def test_excluye_suicidio():
    r = compute_duels([_kill("a1", "a1")], ROSTER)
    assert all(p["kills_a"] == 0 and p["kills_b"] == 0 for p in r.pairs)
    assert r.events == []


def test_pares_cero_desde_roster():
    roster = {f"a{i}": 2 for i in range(5)} | {f"b{i}": 3 for i in range(5)}
    r = compute_duels([], roster)
    assert len(r.pairs) == 25
    assert all(p["kills_a"] == 0 and p["kills_b"] == 0 for p in r.pairs)
    assert r.events == []


def test_swap_irrelevante():
    # El par se identifica por steamids: kills antes y después del swap de
    # bandos (ronda 1 vs 20) acumulan en el mismo par.
    kills = [
        _kill("a1", "b1", round_num=1, tick=100),
        _kill("a1", "b1", round_num=20, tick=9000),
    ]
    r = compute_duels(kills, ROSTER)
    assert _pair(r.pairs, "a1", "b1")["kills_a"] == 2


def test_atacante_fuera_de_roster():
    r = compute_duels([_kill("fantasma", "b1")], ROSTER)
    assert all(p["kills_a"] == 0 and p["kills_b"] == 0 for p in r.pairs)
    assert r.events == []
    # team_num raro (espectador) no genera pares
    r2 = compute_duels([], {"a1": 2, "x": None})
    assert r2.pairs == []


def test_round_null_va_al_final():
    kills = [
        _kill("a1", "b1", round_num=None, tick=50),
        _kill("a1", "b1", round_num=3, tick=400),
    ]
    r = compute_duels(kills, ROSTER)
    assert _pair(r.pairs, "a1", "b1")["kills_a"] == 2
    assert [e["round_num"] for e in r.events] == [3, None]
