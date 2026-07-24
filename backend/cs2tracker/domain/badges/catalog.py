"""
Catálogo v1 de badges de partida -- mismos triggers y umbrales que el
if/else original, ahora como definiciones declarativas que evalúa
`evaluador.py`. Ajustar un umbral es tocar una constante acá, no lógica.
"""

from __future__ import annotations

from .types import BadgeDef, Categoria, MatchBadgeInputs, Tier, UmbralTipo

ENTRY_KING_MIN_FB = 3
ENTRY_KING_MIN_WINRATE = 60.0
CLUTCH_MINISTER_MIN = 2
UTILITY_GOD_MIN_BLIND_S = 2.5
UTILITY_GOD_MIN_DMG = 300
TEAM_FLASHER_MIN = 5
# Umbral absoluto en vez de percentil entre compañeros de partida (que exigiría
# extender el evaluador a contexto multi-jugador, fuera de alcance de esta
# pasada -- ver docs de revisión). Punto de partida sin datos reales para
# calibrar, ajustar cuando haya volumen.
LURKEA_MUCHO_MIN_RATE = 40.0
FORCE_BUY_GANADOR_MIN = 2
ECO_FRAG_MIN = 1
AHORRA_BIEN_MIN_RATE = 80.0


def _utility_god_blind(m: MatchBadgeInputs) -> bool:
    return m.avg_flash_blind_duration is not None and m.avg_flash_blind_duration >= (
        UTILITY_GOD_MIN_BLIND_S
    )


def _utility_god_detalle(m: MatchBadgeInputs) -> str:
    parts = []
    if _utility_god_blind(m):
        parts.append(f"Promedio de {m.avg_flash_blind_duration:.1f}s cegando rivales por flash")
    if m.grenade_damage >= UTILITY_GOD_MIN_DMG:
        parts.append(f"{m.grenade_damage} de daño con granadas")
    return " · ".join(parts)


CATALOG: list[BadgeDef] = [
    BadgeDef(
        id="entry_king",
        label="Entry King",
        categoria=Categoria.ENTRY,
        tier=Tier.POSITIVO,
        umbral_tipo=UmbralTipo.ABSOLUTO,
        condicion=lambda m: (
            m.entry_kills >= ENTRY_KING_MIN_FB and m.entry_kill_win_rate >= ENTRY_KING_MIN_WINRATE
        ),
        detalle=lambda m: (
            f"{m.entry_kills} entry kills, {m.entry_kill_win_rate:.0f}% "
            "de rondas ganadas tras entrar"
        ),
    ),
    BadgeDef(
        id="clutch_minister",
        label="Clutch Minister",
        categoria=Categoria.CLUTCH,
        tier=Tier.POSITIVO,
        umbral_tipo=UmbralTipo.ABSOLUTO,
        condicion=lambda m: m.clutches_won >= CLUTCH_MINISTER_MIN,
        detalle=lambda m: f"{m.clutches_won} clutches ganados esta partida",
    ),
    BadgeDef(
        id="utility_god",
        label="Utility God",
        categoria=Categoria.UTILIDAD,
        tier=Tier.POSITIVO,
        umbral_tipo=UmbralTipo.ABSOLUTO,
        condicion=lambda m: _utility_god_blind(m) or m.grenade_damage >= UTILITY_GOD_MIN_DMG,
        detalle=_utility_god_detalle,
    ),
    BadgeDef(
        id="team_flasher",
        label="Team Flasher",
        categoria=Categoria.UTILIDAD,
        tier=Tier.WARNING,
        umbral_tipo=UmbralTipo.ABSOLUTO,
        condicion=lambda m: m.team_flashes >= TEAM_FLASHER_MIN,
        detalle=lambda m: (
            f"{m.team_flashes} flashes cegaron a un compañero "
            f"(de {m.team_flashes_total} tiradas en total)"
        ),
    ),
    BadgeDef(
        id="lurkea_mucho",
        label="Lurkea mucho",
        categoria=Categoria.ROL,
        tier=Tier.NEUTRAL,
        umbral_tipo=UmbralTipo.ABSOLUTO,
        condicion=lambda m: m.lurker_rate is not None and m.lurker_rate >= LURKEA_MUCHO_MIN_RATE,
        # Describe el patrón observado (aislamiento + timing tardío), no le
        # atribuye intención ("cortó rotaciones") ni efecto ("engañó el
        # sitio") -- ver domain/lurker.py.
        detalle=lambda m: (
            f"Jugó aislado del grupo en el {m.lurker_rate:.0f}% de sus rondas "
            "como atacante, con bajas tardías"
        ),
    ),
    BadgeDef(
        id="force_buy_ganador",
        label="Force buy ganador",
        categoria=Categoria.ECONOMIA,
        tier=Tier.POSITIVO,
        umbral_tipo=UmbralTipo.ABSOLUTO,
        condicion=lambda m: m.force_buy_wins >= FORCE_BUY_GANADOR_MIN,
        detalle=lambda m: f"Ganó {m.force_buy_wins} rondas en force-buy esta partida",
    ),
    BadgeDef(
        id="eco_frag",
        label="Eco frag",
        categoria=Categoria.ECONOMIA,
        tier=Tier.POSITIVO,
        umbral_tipo=UmbralTipo.ABSOLUTO,
        condicion=lambda m: m.eco_frags >= ECO_FRAG_MIN,
        detalle=lambda m: (
            f"{m.eco_frags} baja{'s' if m.eco_frags != 1 else ''} en eco contra rivales full-buy"
        ),
    ),
    BadgeDef(
        id="millonario",
        label="Millonario",
        categoria=Categoria.ECONOMIA,
        tier=Tier.NEUTRAL,
        umbral_tipo=UmbralTipo.ABSOLUTO,
        condicion=lambda m: m.millonario_weapon is not None,
        # Límite honesto (ver domain/economia.py::detectar_millonario): puede
        # haber sido una compra o una recogida del piso, el parser no
        # distingue -- el texto no afirma "gastó su plata", solo que terminó
        # con el arma en un momento de economía floja.
        detalle=lambda m: f"Terminó con {m.millonario_weapon} estando en eco/semi-eco",
    ),
    BadgeDef(
        id="ahorra_bien",
        label="Ahorra bien",
        categoria=Categoria.ECONOMIA,
        tier=Tier.POSITIVO,
        umbral_tipo=UmbralTipo.ABSOLUTO,
        condicion=lambda m: m.economia_rate is not None and m.economia_rate >= AHORRA_BIEN_MIN_RATE,
        detalle=lambda m: f"Evitó el eco total en el {m.economia_rate:.0f}% de sus rondas",
    ),
]
