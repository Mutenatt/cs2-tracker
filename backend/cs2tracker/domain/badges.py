"""
Badges de partida (dopamine loop): triggers puros sobre insumos ya
agregados por api/queries.py::badge_inputs. PURA, no toca la DB.
"""

from __future__ import annotations

from dataclasses import dataclass

ENTRY_KING_MIN_FB = 3
ENTRY_KING_MIN_WINRATE = 60.0
CLUTCH_MINISTER_MIN = 2
UTILITY_GOD_MIN_BLIND_S = 2.5
UTILITY_GOD_MIN_DMG = 300
TEAM_FLASHER_MIN = 5


@dataclass
class Badge:
    key: str
    kind: str  # "good" | "warn"
    icon: str
    title: str
    detail: str


@dataclass
class MatchBadgeInputs:
    entry_kills: int
    entry_kill_win_rate: float  # 0..100 (0 si entry_kills == 0)
    clutches_won: int
    avg_flash_blind_duration: float | None  # solo tiradas que cegaron >=1 rival
    grenade_damage: int
    team_flashes: int
    team_flashes_total: int


def compute_badges(m: MatchBadgeInputs) -> list[Badge]:
    badges: list[Badge] = []

    if m.entry_kills >= ENTRY_KING_MIN_FB and m.entry_kill_win_rate >= ENTRY_KING_MIN_WINRATE:
        badges.append(
            Badge(
                key="entry_king",
                kind="good",
                icon="🏅",
                title="Entry King",
                detail=(
                    f"{m.entry_kills} entry kills, {m.entry_kill_win_rate:.0f}% "
                    "de rondas ganadas tras entrar"
                ),
            )
        )

    if m.clutches_won >= CLUTCH_MINISTER_MIN:
        badges.append(
            Badge(
                key="clutch_minister",
                kind="good",
                icon="🏅",
                title="Clutch Minister",
                detail=f"{m.clutches_won} clutches ganados esta partida",
            )
        )

    utility_god_blind = (
        m.avg_flash_blind_duration is not None
        and m.avg_flash_blind_duration >= UTILITY_GOD_MIN_BLIND_S
    )
    utility_god_dmg = m.grenade_damage >= UTILITY_GOD_MIN_DMG
    if utility_god_blind or utility_god_dmg:
        parts = []
        if utility_god_blind:
            parts.append(f"Promedio de {m.avg_flash_blind_duration:.1f}s cegando rivales por flash")
        if utility_god_dmg:
            parts.append(f"{m.grenade_damage} de daño con granadas")
        badges.append(
            Badge(
                key="utility_god",
                kind="good",
                icon="🏅",
                title="Utility God",
                detail=" · ".join(parts),
            )
        )

    if m.team_flashes >= TEAM_FLASHER_MIN:
        badges.append(
            Badge(
                key="team_flasher",
                kind="warn",
                icon="⚠️",
                title="Team Flasher",
                detail=f"{m.team_flashes} de {m.team_flashes_total} flashes cegaron a un compañero",
            )
        )

    return badges
