"""
Winrate "jugando juntos" entre dos usuarios. PURA -- recibe el resultado ya
resuelto de las partidas donde compartieron equipo (ver
api/queries.py::winrate_conjunto), no toca la DB.

Decisión clave (hereda la del doc original que revisamos): solo cuentan
partidas donde ambos estuvieron en el MISMO equipo. Si estuvieron en
equipos rivales, esa partida no es parte de "winrate jugando juntos" --
queda para un contador aparte de enfrentamientos (ver
api/queries.py::rivals, matches_opposed).
"""

from __future__ import annotations


def calcular_winrate_conjunto(partidas_compartidas: list[dict]) -> dict:
    """`partidas_compartidas`: una entrada `{"won": bool}` por partida
    donde ambos jugadores compartieron equipo Y el resultado está resuelto
    (partidas con ganador irresoluto ya se filtraron antes de llegar acá)."""
    total = len(partidas_compartidas)
    if total == 0:
        return {"matches_together": 0, "wins": 0, "losses": 0, "win_rate": 0.0}
    wins = sum(1 for p in partidas_compartidas if p["won"])
    return {
        "matches_together": total,
        "wins": wins,
        "losses": total - wins,
        "win_rate": round(100.0 * wins / total, 1),
    }
