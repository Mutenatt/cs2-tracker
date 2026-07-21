"""
Rating estilo HLTV 2.0 (APROXIMACION). La formula real es propietaria; esta es
la reverse-engineered ampliamente citada. Sirve como indicador global de impacto.

    impact = 2.13*KPR + 0.42*APR - 0.41
    rating = 0.0073*KAST + 0.3591*KPR - 0.5329*DPR + 0.2372*impact
             + 0.0032*ADR + 0.1587
KAST en porcentaje (0..100). ~1.0 = jugador promedio.
"""

from __future__ import annotations


def compute_rating(
    kills: int, deaths: int, assists: int, adr: float, kast: float, n_rounds: int
) -> float:
    r = max(n_rounds, 1)
    kpr = kills / r
    dpr = deaths / r
    apr = assists / r
    impact = 2.13 * kpr + 0.42 * apr - 0.41
    rating = 0.0073 * kast + 0.3591 * kpr - 0.5329 * dpr + 0.2372 * impact + 0.0032 * adr + 0.1587
    return round(max(rating, 0.0), 2)
