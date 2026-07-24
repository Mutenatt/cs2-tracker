"""Test de triggers de badges (dopamine loop). Puro, sin DB."""

from cs2tracker.domain.badges import Categoria, MatchBadgeInputs, Tier, UmbralTipo, compute_badges
from cs2tracker.domain.badges.evaluador import MIN_JUGADORES_RELATIVO, evaluar_badges
from cs2tracker.domain.badges.types import BadgeDef

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


def test_team_flasher_detalle_no_es_enganoso():
    # El denominador (team_flashes_total) son TODAS las flashes tiradas, no
    # las que cegaron a alguien -- el texto debe dejarlo explícito.
    badges = compute_badges(_inputs(team_flashes=5, team_flashes_total=19))
    assert badges[0].detail == "5 flashes cegaron a un compañero (de 19 tiradas en total)"


def test_compute_badges_devuelve_shape_legacy_completo():
    badges = compute_badges(_inputs(clutches_won=2))
    assert badges[0].key == "clutch_minister"
    assert badges[0].kind == "good"
    assert badges[0].icon == "🏅"
    assert badges[0].title == "Clutch Minister"


_SIEMPRE_TRUE = BadgeDef(
    id="siempre",
    label="Siempre",
    categoria=Categoria.CLUTCH,
    tier=Tier.POSITIVO,
    umbral_tipo=UmbralTipo.RELATIVO_PARTIDA,
    condicion=lambda m: True,
)


def test_guardrail_saltea_relativo_partida_con_pocos_jugadores():
    pocos = _inputs(player_count=MIN_JUGADORES_RELATIVO - 1)
    assert evaluar_badges(pocos, [_SIEMPRE_TRUE]) == []


def test_guardrail_no_afecta_con_jugadores_suficientes():
    suficientes = _inputs(player_count=MIN_JUGADORES_RELATIVO)
    resultado = evaluar_badges(suficientes, [_SIEMPRE_TRUE])
    assert [r["id"] for r in resultado] == ["siempre"]


def test_guardrail_no_afecta_si_no_se_sabe_la_cantidad_de_jugadores():
    # player_count=None (default) -> no se asume nada, no se bloquea.
    sin_dato = _inputs()
    resultado = evaluar_badges(sin_dato, [_SIEMPRE_TRUE])
    assert [r["id"] for r in resultado] == ["siempre"]


def test_force_buy_ganador():
    assert compute_badges(_inputs(force_buy_wins=2))[0].key == "force_buy_ganador"
    assert compute_badges(_inputs(force_buy_wins=1)) == []


def test_eco_frag():
    assert compute_badges(_inputs(eco_frags=1))[0].key == "eco_frag"
    assert compute_badges(_inputs(eco_frags=0)) == []


def test_millonario_requiere_arma():
    badges = compute_badges(_inputs(millonario_weapon="awp"))
    assert badges[0].key == "millonario"
    assert badges[0].detail == "Terminó con awp estando en eco/semi-eco"
    assert compute_badges(_inputs(millonario_weapon=None)) == []


def test_ahorra_bien_requiere_umbral_y_dato():
    assert compute_badges(_inputs(economia_rate=80.0))[0].key == "ahorra_bien"
    assert compute_badges(_inputs(economia_rate=79.9)) == []
    # None (partida sin re-ingerir con --force) no dispara -- no se asume 0.
    assert compute_badges(_inputs(economia_rate=None)) == []
