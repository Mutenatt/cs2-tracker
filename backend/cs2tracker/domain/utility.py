"""
Efectividad de utilidad: PURA. Recibe granadas y sus efectos como dicts, no
toca DB ni parser.

Un 'grenade' es un dict con: thrower, round_num, tick, weapon, x, y, z, y
opcionalmente entity_id (id de entidad del engine, ver más abajo).
Un 'blind' es un dict con: attacker, victim, round_num, tick, duration, y
opcionalmente entity_id.
Un 'damage' es un dict con: attacker, victim, round_num, tick, weapon, dmg_health.

Valores de `weapon` (confirmados contra demoparser2 0.41.4 con una demo real,
ver infra/parser.py): 'flashbang', 'hegrenade', 'inferno' (molotov/incendiary
-- así se llama tanto el evento de detonación como el weapon en player_hurt),
'smokegrenade', 'decoy'.

compute_flash_effectiveness liga blind -> flash por (round_num, entity_id):
demoparser2 comparte el entityid entre flashbang_detonate y player_blind, así
que la asociación es exacta, no una heurística.

compute_utility_damage NO tiene ese lujo: player_hurt no expone un entityid
que lo ligue a la granada. Se asocia por ventana de ticks (mismo patrón que
domain/kast.py usa para detectar trades) -- es una heurística, documentarlo
así en cualquier lugar que consuma el resultado.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass

DEFAULT_DAMAGE_WINDOW_TICKS = 320  # ~5s a 64 tick
DEFAULT_TICKRATE = 64  # servers de Premier/Competitivo de CS2 corren a 64 tick

_HE_MOLOTOV_WEAPONS = {"hegrenade", "inferno"}


@dataclass
class FlashEffect:
    enemies_blinded: int = 0
    blind_duration_total: float = 0.0
    teammates_blinded: int = 0


def compute_flash_effectiveness(
    grenades: Iterable[dict],
    blinds: Iterable[dict],
    teams: dict[str, int],
) -> dict[int, FlashEffect]:
    """Por cada flash tirada (índice en `grenades`), cuenta enemigos cegados,
    duración total de ceguera a rivales, y a cuántos compañeros cegó
    (self/team-flash)."""
    grenades = list(grenades)
    by_key: dict[tuple[int | None, int], int] = {}
    result: dict[int, FlashEffect] = {}
    for idx, g in enumerate(grenades):
        if g.get("weapon") != "flashbang":
            continue
        result[idx] = FlashEffect()
        eid = g.get("entity_id")
        if eid is not None:
            by_key[(g.get("round_num"), eid)] = idx

    for b in blinds:
        idx = by_key.get((b.get("round_num"), b.get("entity_id")))
        if idx is None:
            continue
        attacker, victim = b.get("attacker"), b.get("victim")
        same_team = teams.get(victim) == teams.get(attacker) and teams.get(attacker) is not None
        eff = result[idx]
        if same_team:
            eff.teammates_blinded += 1
        else:
            eff.enemies_blinded += 1
            eff.blind_duration_total += b.get("duration") or 0.0

    return result


def compute_utility_damage(
    grenades: Iterable[dict],
    damages: Iterable[dict],
    window_ticks: int = DEFAULT_DAMAGE_WINDOW_TICKS,
) -> dict[int, int]:
    """Por cada tirada de HE/molotov (índice en `grenades`), suma el daño
    infligido por ese jugador con esa arma en esa ronda dentro de la ventana
    posterior a la detonación (heurística: sin entity_id disponible en
    player_hurt para ligarlo de forma exacta)."""
    grenades = list(grenades)
    throws_by_round: dict[int, list[tuple[int, dict]]] = defaultdict(list)
    for idx, g in enumerate(grenades):
        if g.get("weapon") in _HE_MOLOTOV_WEAPONS:
            throws_by_round[g.get("round_num")].append((idx, g))

    result: dict[int, int] = {idx: 0 for group in throws_by_round.values() for idx, _ in group}

    for d in damages:
        weapon = d.get("weapon")
        if weapon not in _HE_MOLOTOV_WEAPONS:
            continue
        dtick = d.get("tick") or 0
        candidates = [
            (idx, g)
            for idx, g in throws_by_round.get(d.get("round_num"), [])
            if g.get("thrower") == d.get("attacker")
            and g.get("weapon") == weapon
            and 0 <= dtick - (g.get("tick") or 0) <= window_ticks
        ]
        if not candidates:
            continue
        idx, _ = max(candidates, key=lambda ig: ig[1].get("tick") or 0)
        result[idx] += d.get("dmg_health") or 0

    return result


def find_flash_assists(
    kills: Iterable[dict],
    blinds: Iterable[dict],
    teams: dict[str, int],
    tickrate: int = DEFAULT_TICKRATE,
) -> list[dict]:
    """Kills de un jugador mientras la VÍCTIMA estaba activamente cegada por
    la flash de un COMPAÑERO del killer (si el propio killer tiró esa flash,
    es su propia jugada, no la asistencia de otro). Sin entity_id que ligue
    kill->blind directamente (a diferencia de compute_flash_effectiveness):
    heurística por ventana de tiempo, mismo patrón que
    compute_utility_damage -- documentarlo igual en quien la consuma.

    Devuelve [{round_num, killer, victim, flash_thrower}]."""
    blinds = list(blinds)
    assists: list[dict] = []
    for k in kills:
        killer, victim = k.get("attacker"), k.get("victim")
        rnd, tick = k.get("round_num"), k.get("tick") or 0
        if not killer or not victim or killer == victim:
            continue
        killer_team = teams.get(killer)
        for b in blinds:
            if b.get("round_num") != rnd or b.get("victim") != victim:
                continue
            thrower = b.get("attacker")
            if not thrower or thrower == killer or teams.get(thrower) != killer_team:
                continue
            btick = b.get("tick") or 0
            duration_ticks = (b.get("duration") or 0.0) * tickrate
            if btick <= tick <= btick + duration_ticks:
                assists.append(
                    {"round_num": rnd, "killer": killer, "victim": victim, "flash_thrower": thrower}
                )
                break
    return assists
