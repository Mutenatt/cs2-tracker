"""Test de domain/loadouts.py: clasificación de tipo de compra por ronda y
agregado de la tabla LOADOUTS (K/D, ADR, ACS, DDΔ, KAST%, ESR%)."""

from cs2tracker.domain.loadouts import (
    aggregate_loadout_stats,
    is_pistol_round,
    loadout_tier,
)


def test_is_pistol_round_arranques_de_mitad():
    assert is_pistol_round(0) is True
    assert is_pistol_round(12) is True
    assert is_pistol_round(1) is False
    assert is_pistol_round(11) is False


def test_is_pistol_round_overtime():
    # OT arranca en la ronda 24, se repite cada 3 (MR3 por lado).
    assert is_pistol_round(24) is True
    assert is_pistol_round(27) is True
    assert is_pistol_round(25) is False


def test_loadout_tier_pistol_pisa_equip_value():
    # Ronda de pistol con equip_value alto (ganó la anterior y compró
    # armor+granadas) sigue siendo "pistol", no "full_buy".
    assert loadout_tier(round_num=0, equip_value=4000) == "pistol"


def test_loadout_tier_umbrales():
    assert loadout_tier(round_num=5, equip_value=4000) == "full_buy"
    assert loadout_tier(round_num=5, equip_value=3900) == "full_buy"
    assert loadout_tier(round_num=5, equip_value=1000) == "semi_buy"
    assert loadout_tier(round_num=5, equip_value=999) == "eco"
    assert loadout_tier(round_num=5, equip_value=0) == "eco"


def test_aggregate_loadout_stats_devuelve_siempre_las_4_filas():
    rows = [
        {
            "tier": "full_buy",
            "kills": 2,
            "deaths": 1,
            "assists": 1,
            "damage": 150,
            "kast": True,
            "entry_attempt": True,
            "entry_win": True,
        },
    ]
    out = aggregate_loadout_stats(rows, lifetime_adr=80.0)
    tiers = {t["tier"] for t in out}
    assert tiers == {"pistol", "full_buy", "semi_buy", "eco"}

    eco = next(t for t in out if t["tier"] == "eco")
    assert eco["rounds"] == 0
    assert eco["kd"] == 0.0
    assert eco["adr"] == 0.0
    assert eco["dd"] == 0.0
    assert eco["kast_pct"] == 0.0
    assert eco["esr_pct"] == 0.0


def test_aggregate_loadout_stats_calcula_kd_adr_dd_kast_esr():
    rows = [
        {
            "tier": "full_buy",
            "kills": 3,
            "deaths": 1,
            "assists": 0,
            "damage": 200,
            "kast": True,
            "entry_attempt": True,
            "entry_win": True,
        },
        {
            "tier": "full_buy",
            "kills": 0,
            "deaths": 1,
            "assists": 0,
            "damage": 50,
            "kast": False,
            "entry_attempt": False,
            "entry_win": False,
        },
    ]
    out = aggregate_loadout_stats(rows, lifetime_adr=100.0)
    full = next(t for t in out if t["tier"] == "full_buy")

    assert full["rounds"] == 2
    assert full["kills"] == 3
    assert full["deaths"] == 2
    assert full["kd"] == 1.5
    assert full["adr"] == 125.0
    assert full["dd"] == 25.0  # 125 - 100
    assert full["kast_pct"] == 50.0
    assert full["esr_pct"] == 100.0  # 1 entry attempt, 1 entry win


def test_aggregate_loadout_stats_kd_sin_muertes():
    rows = [
        {
            "tier": "eco",
            "kills": 2,
            "deaths": 0,
            "assists": 0,
            "damage": 100,
            "kast": True,
            "entry_attempt": False,
            "entry_win": False,
        },
    ]
    out = aggregate_loadout_stats(rows, lifetime_adr=80.0)
    eco = next(t for t in out if t["tier"] == "eco")
    assert eco["kd"] == 2.0  # sin división por cero
