"""
Adaptador entre el resultado del evaluador (BadgeDef -> dict declarativo) y
el shape legacy `Badge` que ya sirve `api/main.py` y consume
`BadgeStrip.tsx`. Mantiene la presentación (ícono, "good"/"warn") separada
de la definición del badge -- BadgeDef no sabe nada de cómo se ve.
"""

from __future__ import annotations

from .types import Badge, Tier

TIER_ICON: dict[Tier, str] = {
    Tier.POSITIVO: "🏅",
    Tier.NEUTRAL: "ℹ️",
    Tier.WARNING: "⚠️",
}

# El shape legacy solo tiene 2 kinds ("good"/"warn"); NEUTRAL no tiene badge
# real todavía -- se mapea a "good" hasta que el frontend soporte un tercer
# estilo visual.
TIER_KIND: dict[Tier, str] = {
    Tier.POSITIVO: "good",
    Tier.NEUTRAL: "good",
    Tier.WARNING: "warn",
}


def to_legacy(resultado: dict) -> Badge:
    tier: Tier = resultado["tier"]
    return Badge(
        key=resultado["id"],
        kind=TIER_KIND[tier],
        icon=TIER_ICON[tier],
        title=resultado["label"],
        detail=resultado["detalle"] or "",
    )
