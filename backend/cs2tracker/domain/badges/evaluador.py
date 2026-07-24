"""
Evaluador genérico: recorre un catálogo de `BadgeDef` y devuelve los que
matchean. PURA -- no toca DB ni conoce el shape legacy (ver render.py).
"""

from __future__ import annotations

from .types import BadgeDef, MatchBadgeInputs, UmbralTipo

# Con menos jugadores que esto, un ranking/percentil entre los participantes
# de la partida es demasiado ruidoso para mostrarse como logro (mismo
# espíritu que MIN_SAMPLE en api/queries.py). Solo aplica a badges
# RELATIVO_PARTIDA -- hoy ninguno del catálogo lo es, pero el guardrail
# corre igual para que el próximo que se agregue lo herede gratis.
MIN_JUGADORES_RELATIVO = 8


def evaluar_badges(m: MatchBadgeInputs, definiciones: list[BadgeDef]) -> list[dict]:
    resultado = []
    for b in definiciones:
        if b.umbral_tipo == UmbralTipo.RELATIVO_PARTIDA and (
            m.player_count is not None and m.player_count < MIN_JUGADORES_RELATIVO
        ):
            continue
        if b.condicion(m):
            resultado.append(
                {
                    "id": b.id,
                    "label": b.label,
                    "categoria": b.categoria,
                    "tier": b.tier,
                    "detalle": b.detalle(m) if b.detalle else None,
                }
            )
    return resultado
