"""
Lógica de estadísticas: PURA. Recibe eventos como dicts, no toca DB ni parser.
Esto la hace trivial de testear y de portar (p. ej. a Rust en el futuro).

Un 'kill' es un dict con: attacker, victim, assister, headshot (bool).
Un 'damage' es un dict con: attacker, victim, dmg_health (int).
attacker/victim/assister son steamids (str) o None.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass
class PlayerStat:
    steamid: str
    name: str | None
    kills: int = 0
    deaths: int = 0
    assists: int = 0
    hs_kills: int = 0
    damage: int = 0

    @property
    def kd(self) -> float:
        return self.kills / self.deaths if self.deaths else float(self.kills)

    @property
    def hs_pct(self) -> float:
        return 100.0 * self.hs_kills / self.kills if self.kills else 0.0

    def adr(self, n_rounds: int) -> float:
        return self.damage / max(n_rounds, 1)


def compute_stats(
    kills: Iterable[dict],
    damages: Iterable[dict],
    n_rounds: int,
    names: dict[str, str] | None = None,
) -> list[PlayerStat]:
    """
    Agrega K/D/A/HS/daño por jugador. Ordena por kills desc.
    - kill cuenta para el atacante solo si attacker != victim (no suicidio/mundo).
    - daño excluye self-damage.
    - ADR usa dmg_health (ya capado al HP restante -> sin overkill).
    """
    names = names or {}
    players: dict[str, PlayerStat] = {}

    def bucket(sid: str) -> PlayerStat:
        return players.setdefault(sid, PlayerStat(steamid=sid, name=names.get(sid)))

    for k in kills:
        atk, vic, ast = k.get("attacker"), k.get("victim"), k.get("assister")
        if vic:
            bucket(vic).deaths += 1
        if atk and atk != vic:
            p = bucket(atk)
            p.kills += 1
            if k.get("headshot"):
                p.hs_kills += 1
        if ast and ast != vic:
            bucket(ast).assists += 1

    for d in damages:
        atk, vic = d.get("attacker"), d.get("victim")
        if atk and atk != vic:
            bucket(atk).damage += int(d.get("dmg_health") or 0)

    return sorted(
        players.values(),
        key=lambda p: (p.kills, p.adr(n_rounds)),
        reverse=True,
    )
