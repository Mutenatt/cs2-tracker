"""Aproximaciones puras usadas por el render de clips (infra/clips.py) para
ubicar el origen de la trayectoria de una granada: el demo solo expone el
tick de detonación/efecto (ver `Grenade` en db/models.py), no el de
lanzamiento, así que se resta un tiempo de vuelo fijo por tipo de arma."""

from __future__ import annotations

TICKS_PER_SECOND = 64

_FLIGHT_SECONDS = {
    "flashbang": 1.5,
    "hegrenade": 1.0,
    "inferno": 1.0,
    "smokegrenade": 1.5,
    "decoy": 1.5,
}
_DEFAULT_FLIGHT_SECONDS = 1.2


def estimate_throw_tick(detonation_tick: int, weapon: str, round_start_tick: int) -> int:
    """Tick aproximado de lanzamiento: detonation_tick menos un tiempo de
    vuelo fijo por arma, sin bajar de round_start_tick (no tiene sentido un
    origen anterior al inicio de la ronda que se está clipeando)."""
    flight_s = _FLIGHT_SECONDS.get(weapon, _DEFAULT_FLIGHT_SECONDS)
    flight_ticks = int(flight_s * TICKS_PER_SECOND)
    return max(round_start_tick, detonation_tick - flight_ticks)
