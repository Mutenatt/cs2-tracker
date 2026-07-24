"""
Detección del rol Lurker: "jugador del bando atacante que juega separado
del grupo principal para pillar desprevenidos a los enemigos". PURA --
recibe eventos ya resueltos (ver api/queries.py::lurker_inputs), no toca
la DB.

Límite honesto (ver docs de revisión): esto mide aislamiento posicional +
timing tardío en rondas de ataque -- es lo que los datos permiten probar.
NO mide "cortó rotaciones" ni "engañó sobre el sitio" (no hay tracking de
trayectos enemigos ni zonas de sitio con nombre en el proyecto todavía).
El texto de cualquier badge/tag que use esto debe describir el patrón
observado, no atribuirle la intención o el efecto que sugiere el nombre
del rol.
"""

from __future__ import annotations

DEFAULT_UMBRAL_DISTANCIA = 0.25  # en unidades u,v normalizadas (0..1 del radar)
DEFAULT_UMBRAL_TARDIO_SEG = 25.0  # más tardío que el umbral de "muerte temprana" de Coach's Corner


def aislamiento_ronda(mi_evento: dict, eventos_equipo: list[dict]) -> float | None:
    """Distancia (u,v) entre mi evento y el centroide de los eventos de mis
    compañeros en la misma ronda. None si el equipo no tuvo eventos con
    coordenadas esa ronda, o si mi propio evento no tiene coordenadas
    (mapa sin radar) -- no se fabrica una distancia sin datos."""
    coords = [
        (e["u"], e["v"])
        for e in eventos_equipo
        if e.get("u") is not None and e.get("v") is not None
    ]
    if not coords or mi_evento.get("u") is None or mi_evento.get("v") is None:
        return None
    centroide_u = sum(c[0] for c in coords) / len(coords)
    centroide_v = sum(c[1] for c in coords) / len(coords)
    return ((mi_evento["u"] - centroide_u) ** 2 + (mi_evento["v"] - centroide_v) ** 2) ** 0.5


def es_ronda_lurker(
    mi_evento: dict,
    eventos_equipo: list[dict],
    umbral_distancia: float = DEFAULT_UMBRAL_DISTANCIA,
    umbral_tardio_seg: float = DEFAULT_UMBRAL_TARDIO_SEG,
) -> bool:
    """True si mi primer evento de la ronda es tardío Y está aislado del
    centroide del equipo. `mi_evento` debe ser el evento más temprano de
    la ronda para ese jugador (ver lurker_inputs, ya viene ordenado)."""
    sir = mi_evento.get("seconds_into_round")
    if sir is None or sir < umbral_tardio_seg:
        return False
    distancia = aislamiento_ronda(mi_evento, eventos_equipo)
    return distancia is not None and distancia >= umbral_distancia


def tasa_lurker(
    rondas_atacante: list[dict],
    umbral_distancia: float = DEFAULT_UMBRAL_DISTANCIA,
    umbral_tardio_seg: float = DEFAULT_UMBRAL_TARDIO_SEG,
) -> float:
    """% de rondas en bando atacante que califican como 'ronda lurker'.
    Cada elemento de `rondas_atacante`: {mi_evento, eventos_equipo} (ver
    api/queries.py::lurker_inputs). 0.0 si no jugó ninguna ronda de ataque
    con datos -- no None, para poder promediarlo directo sin chequeos."""
    if not rondas_atacante:
        return 0.0
    lurker_rounds = sum(
        1
        for r in rondas_atacante
        if es_ronda_lurker(r["mi_evento"], r["eventos_equipo"], umbral_distancia, umbral_tardio_seg)
    )
    return round(100.0 * lurker_rounds / len(rondas_atacante), 1)
