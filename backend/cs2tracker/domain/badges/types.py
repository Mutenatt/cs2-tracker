"""
Tipos del sistema de badges data-driven. `BadgeDef` es la definición
declarativa de un badge; `Badge` es el shape legacy que ya consume
`api/main.py`/`BadgeStrip.tsx` (frontend) -- se mantiene sin cambios para
no romper el contrato existente (ver `render.py` para el adaptador entre
ambos).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum


class Categoria(StrEnum):
    ENTRY = "entry"
    CLUTCH = "clutch"
    UTILIDAD = "utilidad"
    ROL = "rol"
    ECONOMIA = "economia"


class Tier(StrEnum):
    POSITIVO = "positivo"  # verde
    NEUTRAL = "neutral"  # amarillo
    WARNING = "warning"  # rojo


class UmbralTipo(StrEnum):
    ABSOLUTO = "absoluto"  # constante fija, no depende de la partida
    RELATIVO_PARTIDA = "relativo"  # ranking/percentil entre los jugadores de la partida


@dataclass
class MatchBadgeInputs:
    entry_kills: int
    entry_kill_win_rate: float  # 0..100 (0 si entry_kills == 0)
    clutches_won: int
    avg_flash_blind_duration: float | None  # solo tiradas que cegaron >=1 rival
    grenade_damage: int
    team_flashes: int
    team_flashes_total: int
    # % de rondas de ataque que califican como "ronda lurker" (ver
    # domain/lurker.py::tasa_lurker). None = no jugó ninguna ronda de
    # ataque con datos evaluables esta partida (no se fabrica un 0 con
    # significado distinto a "no lurkeó nada").
    lurker_rate: float | None = None
    # Economía (ver domain/economia.py). None en millonario_weapon = no
    # compró nada calificable; force_buy_wins/eco_frags en 0 por default
    # ya que "no pasó" es una respuesta real, no "no se sabe" -- a
    # diferencia de economia_rate, que si la partida no tiene datos de
    # round_economy (no re-ingerida con --force) queda en None.
    force_buy_wins: int = 0
    eco_frags: int = 0
    millonario_weapon: str | None = None
    economia_rate: float | None = None
    # Cantidad de jugadores de la partida -- solo lo usa el guardrail de
    # muestra chica para badges RELATIVO_PARTIDA (ninguno hoy). Opcional y
    # sin default de negocio: None = "no se sabe", nunca se asume 10.
    player_count: int | None = None


@dataclass(frozen=True)
class BadgeDef:
    id: str  # slug único, ej. "utility_god"
    label: str  # texto mostrado, ej. "Utility God"
    categoria: Categoria
    tier: Tier
    umbral_tipo: UmbralTipo
    condicion: Callable[[MatchBadgeInputs], bool]
    detalle: Callable[[MatchBadgeInputs], str] | None = None


@dataclass
class Badge:
    """Shape legacy servido hoy por /matches/{id}/badges (BadgeOut) y
    consumido por BadgeStrip.tsx. No cambia de forma con el refactor
    data-driven -- ver render.py::to_legacy."""

    key: str
    kind: str  # "good" | "warn"
    icon: str
    title: str
    detail: str
