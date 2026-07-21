"""
Inferencia del rol dominante de un jugador a partir de agregados reales de
sus partidas. PURA: recibe números ya agregados (ver api/queries.py::
role_inputs), devuelve una etiqueta o None.

Orden de especificidad (el primero que matchea gana): un AWPer dedicado se
reconoce aunque también entre primero; un entry se reconoce aunque tire
flashes. Umbrales:
- awper: >= 35% de las kills con AWP (un main AWPer ronda 40-50%; 0.35
  tolera rondas de eco).
- entry: >= 3 duelos de apertura (entry kills + entry deaths) por partida --
  entrar consistentemente primero, gane o pierda el duelo.
- support: >= 3 flashes efectivas (cegaron a >= 1 enemigo) por partida.
- rifler: el resto.
"""

from __future__ import annotations

AWP_SHARE_THRESHOLD = 0.35
ENTRY_ATTEMPTS_PER_MATCH = 3.0
EFFECTIVE_FLASHES_PER_MATCH = 3.0


def dominant_role(
    *,
    matches_played: int,
    total_kills: int,
    awp_kills: int,
    entry_kills: int,
    entry_deaths: int,
    effective_flashes: int,
) -> str | None:
    """Devuelve "awper" | "entry" | "support" | "rifler", o None sin partidas."""
    if matches_played <= 0:
        return None
    if total_kills > 0 and awp_kills / total_kills >= AWP_SHARE_THRESHOLD:
        return "awper"
    if (entry_kills + entry_deaths) / matches_played >= ENTRY_ATTEMPTS_PER_MATCH:
        return "entry"
    if effective_flashes / matches_played >= EFFECTIVE_FLASHES_PER_MATCH:
        return "support"
    return "rifler"
