"""Test de triggers de badges (dopamine loop). Puro, sin DB."""

from cs2tracker.domain.badges import MatchBadgeInputs, compute_badges

BASE = {
    "entry_kills": 0,
    "entry_kill_win_rate": 0.0,
    "clutches_won": 0,
    "avg_flash_blind_duration": None,
    "grenade_damage": 0,
    "team_flashes": 0,
    "team_flashes_total": 0,
}


def _inputs(**overrides) -> MatchBadgeInputs:
    return MatchBadgeInputs(**{**BASE, **overrides})


def test_sin_triggers_no_hay_badges():
    assert compute_badges(_inputs()) == []


def test_entry_king_requiere_volumen_y_winrate():
    assert compute_badges(_inputs(entry_kills=3, entry_kill_win_rate=60.0))[0].key == "entry_king"
    # 3 FK pero bajo winrate -> no dispara
    assert compute_badges(_inputs(entry_kills=3, entry_kill_win_rate=59.9)) == []
    # buen winrate pero pocas FK -> no dispara
    assert compute_badges(_inputs(entry_kills=2, entry_kill_win_rate=100.0)) == []


def test_clutch_minister():
    badges = compute_badges(_inputs(clutches_won=2))
    assert badges[0].key == "clutch_minister"
    assert compute_badges(_inputs(clutches_won=1)) == []


def test_utility_god_por_duracion_o_por_dano():
    assert compute_badges(_inputs(avg_flash_blind_duration=2.5))[0].key == "utility_god"
    assert compute_badges(_inputs(grenade_damage=300))[0].key == "utility_god"
    assert compute_badges(_inputs(avg_flash_blind_duration=2.4, grenade_damage=299)) == []


def test_team_flasher_es_anti_badge():
    badges = compute_badges(_inputs(team_flashes=5, team_flashes_total=19))
    assert badges[0].key == "team_flasher"
    assert badges[0].kind == "warn"


def test_varios_badges_a_la_vez():
    badges = compute_badges(_inputs(clutches_won=2, team_flashes=12, team_flashes_total=19))
    keys = {b.key for b in badges}
    assert keys == {"clutch_minister", "team_flasher"}
