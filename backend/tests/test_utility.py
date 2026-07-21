"""Test de efectividad de utilidad: flashes y daño de HE/molotov."""

from cs2tracker.domain.utility import (
    compute_flash_effectiveness,
    compute_utility_damage,
    find_flash_assists,
)

TEAMS = {"A": 2, "A2": 2, "B": 3, "B2": 3}


def test_flash_ciega_rivales():
    grenades = [
        {"round_num": 0, "tick": 100, "thrower": "A", "weapon": "flashbang", "entity_id": 5},
    ]
    blinds = [
        {
            "round_num": 0,
            "tick": 110,
            "attacker": "A",
            "victim": "B",
            "duration": 2.5,
            "entity_id": 5,
        },
        {
            "round_num": 0,
            "tick": 115,
            "attacker": "A",
            "victim": "B2",
            "duration": 1.0,
            "entity_id": 5,
        },
    ]
    eff = compute_flash_effectiveness(grenades, blinds, TEAMS)
    assert eff[0].enemies_blinded == 2
    assert eff[0].blind_duration_total == 3.5
    assert eff[0].teammates_blinded == 0


def test_flash_self_team_no_cuenta_como_enemigo():
    grenades = [
        {"round_num": 0, "tick": 100, "thrower": "A", "weapon": "flashbang", "entity_id": 5},
    ]
    blinds = [
        {
            "round_num": 0,
            "tick": 105,
            "attacker": "A",
            "victim": "A2",
            "duration": 1.5,
            "entity_id": 5,
        },
    ]
    eff = compute_flash_effectiveness(grenades, blinds, TEAMS)
    assert eff[0].teammates_blinded == 1
    assert eff[0].enemies_blinded == 0


def test_flash_entity_id_distinto_no_se_asocia():
    # Un blind con entity_id que no matchea ninguna flash del round -> se ignora.
    grenades = [
        {"round_num": 0, "tick": 100, "thrower": "A", "weapon": "flashbang", "entity_id": 5},
    ]
    blinds = [
        {
            "round_num": 0,
            "tick": 110,
            "attacker": "A",
            "victim": "B",
            "duration": 2.0,
            "entity_id": 99,
        },
    ]
    eff = compute_flash_effectiveness(grenades, blinds, TEAMS)
    assert eff[0].enemies_blinded == 0
    assert eff[0].blind_duration_total == 0.0


def test_flash_mismo_entity_id_otro_round_no_se_confunde():
    # entity_id se recicla entre rounds -> el match debe scopearse por round_num.
    grenades = [
        {"round_num": 0, "tick": 50, "thrower": "A", "weapon": "flashbang", "entity_id": 5},
        {"round_num": 1, "tick": 100, "thrower": "A", "weapon": "flashbang", "entity_id": 5},
    ]
    blinds = [
        {
            "round_num": 1,
            "tick": 110,
            "attacker": "A",
            "victim": "B",
            "duration": 2.0,
            "entity_id": 5,
        },
    ]
    eff = compute_flash_effectiveness(grenades, blinds, TEAMS)
    assert eff[0].enemies_blinded == 0
    assert eff[1].enemies_blinded == 1


def test_find_flash_assists_companero_cego_a_la_victima():
    # A2 tira una flash que ciega a B (compañero de A). A mata a B mientras
    # sigue cegado -> flash assist para A2.
    kills = [{"round_num": 0, "tick": 120, "attacker": "A", "victim": "B"}]
    blinds = [
        {"round_num": 0, "tick": 100, "attacker": "A2", "victim": "B", "duration": 2.0},
    ]
    assists = find_flash_assists(kills, blinds, TEAMS, tickrate=64)
    assert assists == [{"round_num": 0, "killer": "A", "victim": "B", "flash_thrower": "A2"}]


def test_find_flash_assists_propia_flash_no_cuenta():
    # A ciega y mata él mismo -> no es asistencia de OTRO jugador.
    kills = [{"round_num": 0, "tick": 120, "attacker": "A", "victim": "B"}]
    blinds = [{"round_num": 0, "tick": 100, "attacker": "A", "victim": "B", "duration": 2.0}]
    assert find_flash_assists(kills, blinds, TEAMS) == []


def test_find_flash_assists_fuera_de_ventana_no_cuenta():
    kills = [{"round_num": 0, "tick": 500, "attacker": "A", "victim": "B"}]
    blinds = [{"round_num": 0, "tick": 100, "attacker": "A2", "victim": "B", "duration": 1.0}]
    assert find_flash_assists(kills, blinds, TEAMS, tickrate=64) == []


def test_find_flash_assists_flash_enemiga_no_cuenta():
    # El que tiró la flash es del equipo RIVAL, no compañero del killer.
    kills = [{"round_num": 0, "tick": 120, "attacker": "A", "victim": "B"}]
    blinds = [{"round_num": 0, "tick": 100, "attacker": "B2", "victim": "B", "duration": 2.0}]
    assert find_flash_assists(kills, blinds, TEAMS) == []


def test_utility_damage_suma_por_tirada():
    grenades = [
        {"round_num": 0, "tick": 100, "thrower": "A", "weapon": "inferno"},
    ]
    damages = [
        {"round_num": 0, "tick": 110, "attacker": "A", "weapon": "inferno", "dmg_health": 10},
        {"round_num": 0, "tick": 130, "attacker": "A", "weapon": "inferno", "dmg_health": 8},
        # otro arma o otro round no debe sumar
        {"round_num": 0, "tick": 120, "attacker": "A", "weapon": "ak47", "dmg_health": 40},
    ]
    dmg = compute_utility_damage(grenades, damages)
    assert dmg[0] == 18
