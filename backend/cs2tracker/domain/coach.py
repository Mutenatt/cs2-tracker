"""
Coach's Corner: patrones de "muerte temprana de ronda" sobre las últimas
partidas del jugador. PURA -- recibe muertes ya resueltas (ver
api/queries.py::recent_deaths_with_timing), no toca la DB.

`seconds_into_round` se calcula al ingerir (ver ingest.py) a partir del tick
de fin de freezetime (round_freeze_end) -- si el demo no expuso ese evento,
la muerte queda sin este dato y se excluye acá, no se fabrica un valor.
"""

from __future__ import annotations

from collections import Counter

DEFAULT_EARLY_THRESHOLD_S = 15.0
MIN_CONFIDENT_MATCHES = 8  # por debajo de esto, se marca como baja confianza
DEFAULT_TICKRATE = 64  # servers de Premier/Competitivo de CS2 corren a 64 tick


def seconds_into_round(
    round_num: int | None,
    tick: int | None,
    freeze_end_ticks: dict[int, int],
    tickrate: int = DEFAULT_TICKRATE,
) -> float | None:
    """Segundos desde que la ronda se volvió "viva" hasta `tick`. None si no
    hay dato de freezetime para esa ronda (demo sin round_freeze_end) o si
    `tick` es anterior al fin de freezetime (no debería pasar, pero por las
    dudas no se fabrica un número negativo)."""
    if round_num is None or tick is None:
        return None
    freeze_tick = freeze_end_ticks.get(round_num)
    if freeze_tick is None or tick < freeze_tick:
        return None
    return round((tick - freeze_tick) / tickrate, 1)


def early_round_death_pattern(
    deaths: list[dict],
    threshold_s: float = DEFAULT_EARLY_THRESHOLD_S,
) -> dict:
    """deaths: [{match_id, map, seconds_into_round}], todas con
    seconds_into_round no nulo. Sobre como mucho las últimas N partidas del
    jugador (recorte lo hace la query, no esta función)."""
    if not deaths:
        return {
            "matches_analyzed": 0,
            "total_deaths": 0,
            "early_deaths": 0,
            "early_death_pct": 0.0,
            "avg_early_death_time_s": None,
            "dominant_map": None,
        }
    matches_analyzed = len({d["match_id"] for d in deaths})
    early = [d for d in deaths if d["seconds_into_round"] <= threshold_s]
    avg_time = round(sum(d["seconds_into_round"] for d in early) / len(early), 1) if early else None
    dominant_map = None
    if early:
        counts = Counter(d["map"] for d in early if d.get("map"))
        if counts:
            dominant_map = counts.most_common(1)[0][0]
    return {
        "matches_analyzed": matches_analyzed,
        "total_deaths": len(deaths),
        "early_deaths": len(early),
        "early_death_pct": round(100.0 * len(early) / len(deaths), 1),
        "avg_early_death_time_s": avg_time,
        "dominant_map": dominant_map,
    }


def describe_early_round_deaths(
    pattern: dict,
    threshold_s: float = DEFAULT_EARLY_THRESHOLD_S,
    min_confident_matches: int = MIN_CONFIDENT_MATCHES,
) -> dict | None:
    """Arma el texto del insight a partir del patrón ya calculado. None si no
    hay ninguna muerte con dato de timing (nada que decir)."""
    if pattern["matches_analyzed"] == 0:
        return None
    low_confidence = pattern["matches_analyzed"] < min_confident_matches
    if pattern["early_deaths"] == 0:
        text = (
            f"No se detectó ningún patrón de muerte temprana en tus últimas "
            f"{pattern['matches_analyzed']} partidas (0 de {pattern['total_deaths']} muertes "
            f"dentro de los primeros ~{threshold_s:.0f}s de ronda)."
        )
    else:
        map_part = f" en {pattern['dominant_map']}" if pattern["dominant_map"] else ""
        text = (
            f"Morís dentro de los primeros ~{threshold_s:.0f}s de ronda en el "
            f"{pattern['early_death_pct']:.0f}% de tus muertes recientes{map_part} "
            f"(tiempo promedio: {pattern['avg_early_death_time_s']:.1f}s)."
        )
    return {
        "text": text,
        "low_confidence": low_confidence,
        "matches_analyzed": pattern["matches_analyzed"],
    }
