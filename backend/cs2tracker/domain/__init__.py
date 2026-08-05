"""Capa de dominio: lógica de negocio pura, sin DB ni framework web."""

from cs2tracker.domain.clip_utility import estimate_throw_tick
from cs2tracker.domain.coach import (
    describe_early_round_deaths,
    early_round_death_pattern,
    seconds_into_round,
)
from cs2tracker.domain.duels import DuelData, compute_duels
from cs2tracker.domain.kast import compute_kast, find_trade_kills, find_traded_deaths
from cs2tracker.domain.monthly import (
    MatchesPerDay,
    MonthBounds,
    MonthlyDetail,
    MonthlyHeadline,
    MonthlyMvp,
    MonthlySummary,
    MonthlyTotals,
    TopMap,
    compute_monthly_summary,
    month_bounds,
)
from cs2tracker.domain.rating import compute_rating
from cs2tracker.domain.roles import dominant_role
from cs2tracker.domain.rounds import (
    compute_round_stats,
    find_clutch_situations,
    find_entry_events,
)
from cs2tracker.domain.stats import PlayerStat, compute_stats
from cs2tracker.domain.teams import TeamResolution, resolve_teams
from cs2tracker.domain.utility import (
    FlashEffect,
    compute_flash_effectiveness,
    compute_utility_damage,
    find_flash_assists,
)

__all__ = [
    "estimate_throw_tick",
    "DuelData",
    "compute_duels",
    "PlayerStat",
    "compute_stats",
    "TeamResolution",
    "resolve_teams",
    "compute_kast",
    "find_traded_deaths",
    "find_trade_kills",
    "compute_round_stats",
    "find_entry_events",
    "find_clutch_situations",
    "compute_rating",
    "dominant_role",
    "FlashEffect",
    "compute_flash_effectiveness",
    "compute_utility_damage",
    "find_flash_assists",
    "early_round_death_pattern",
    "describe_early_round_deaths",
    "seconds_into_round",
    "MatchesPerDay",
    "TopMap",
    "MonthBounds",
    "MonthlyDetail",
    "MonthlyHeadline",
    "MonthlyMvp",
    "MonthlySummary",
    "MonthlyTotals",
    "compute_monthly_summary",
    "month_bounds",
]
