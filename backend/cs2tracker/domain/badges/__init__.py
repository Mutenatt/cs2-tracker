"""
Badges de partida (dopamine loop): catálogo declarativo (`catalog.py`)
evaluado por un motor genérico (`evaluador.py`), servido bajo el mismo
shape legacy (`Badge`) que ya consume `api/main.py`/`BadgeStrip.tsx` (ver
`render.py`). PURO, no toca la DB -- insumos ya agregados por
`api/queries.py::badge_inputs`.

`compute_badges` es el único punto de entrada público; el resto del
proyecto no necesita saber que por dentro hay un catálogo declarativo en
vez de if/else.
"""

from __future__ import annotations

from .catalog import CATALOG
from .evaluador import evaluar_badges
from .render import to_legacy
from .types import Badge, BadgeDef, Categoria, MatchBadgeInputs, Tier, UmbralTipo

__all__ = [
    "Badge",
    "BadgeDef",
    "Categoria",
    "MatchBadgeInputs",
    "Tier",
    "UmbralTipo",
    "compute_badges",
]


def compute_badges(m: MatchBadgeInputs) -> list[Badge]:
    return [to_legacy(r) for r in evaluar_badges(m, CATALOG)]
