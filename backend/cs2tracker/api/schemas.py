"""Schemas Pydantic: contrato tipado de la API (y OpenAPI gratis)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class RegisterIn(BaseModel):
    email: str
    password: str


class LoginIn(BaseModel):
    email: str
    password: str


class ForgotPasswordIn(BaseModel):
    email: str


class ResetPasswordIn(BaseModel):
    token: str
    new_password: str


class MeOut(BaseModel):
    pending: bool
    steamid: str | None
    display_name: str | None
    avatar_url: str | None
    steam_background_url: str | None = None
    custom_background_url: str | None = None
    email: str | None
    email_verified_at: str | None
    onboarding_completed_at: str | None


class CustomBackgroundIn(BaseModel):
    url: str


class AutofetchLinkIn(BaseModel):
    auth_code: str
    sharecode: str  # acepta el código pelado o la URL steam://... completa


class AutofetchStatusOut(BaseModel):
    linked: bool
    status: str | None  # None | 'active' | 'revoked' | 'error'
    error: str | None
    last_sharecode: str | None
    last_polled_at: str | None
    last_fetched_at: str | None


AgeBucket = Literal["13-17", "18-24", "25-34", "35-44", "45+"]
AcquisitionChannel = Literal["youtube", "twitch", "reddit", "amigo", "buscador", "otro"]
PrimaryGoal = Literal["competitivo", "casual", "coaching", "equipo", "otro"]


class DemographicsIn(BaseModel):
    age_bucket: AgeBucket
    country: str
    acquisition_channel: AcquisitionChannel
    primary_goal: PrimaryGoal


class OnboardingStatusOut(BaseModel):
    demographics_completed: bool
    autofetch_linked: bool
    bot_friend_added_at: str | None
    bot_steamid: str | None
    onboarding_completed_at: str | None


class MatchSummary(BaseModel):
    match_id: str
    map: str | None
    n_rounds: int | None
    ingested_at: str | None = None
    played_at: str | None = None  # matchtime del GC; NULL = ingesta manual sin backfill


class PlayerRow(BaseModel):
    steamid: str
    name: str | None
    team_num: int | None
    rank: int | None = None  # CS Rating crudo del demo; 0 = calibrando
    rank_type: int | None = None  # 11 = Premier
    kills: int
    deaths: int
    assists: int
    damage: int
    adr: float
    kd: float
    hs_pct: float
    kast: float
    entry_kills: int
    entry_deaths: int
    k2: int
    k3: int
    k4: int
    k5: int
    clutches: int
    rating: float


class TeamScore(BaseModel):
    team_num: int
    score: int


class MatchDetail(BaseModel):
    match: MatchSummary
    teams: list[TeamScore]
    scoreboard: list[PlayerRow]


class KillPoint(BaseModel):
    u: float
    v: float
    headshot: bool
    victim_team: int | None


class KillsResponse(BaseModel):
    map: str | None
    has_radar: bool
    kills: list[KillPoint]


class WeaponStat(BaseModel):
    weapon: str
    kills: int
    damage: int


class PlayerWeapons(BaseModel):
    steamid: str
    name: str | None
    top_weapons: list[WeaponStat]
    hitgroups: dict[str, int]


class WeaponsResponse(BaseModel):
    players: list[PlayerWeapons]


class HeatmapCell(BaseModel):
    grid_x: int
    grid_y: int
    count: int  # métrica principal de esta vista (no siempre = total de eventos)
    top_weapon: str | None = None
    avg_enemies_blinded: float | None = None
    total_blind_duration: float | None = None
    avg_damage: float | None = None


class HeatmapResponse(BaseModel):
    steamid: str
    map: str
    has_radar: bool
    grid_size: int
    cells: list[HeatmapCell]


class EntryHeatmapResponse(BaseModel):
    steamid: str
    map: str
    has_radar: bool
    grid_size: int
    entry_kills: list[HeatmapCell]
    entry_deaths: list[HeatmapCell]


class FriendlyFireSummary(BaseModel):
    total_flashes: int
    friendly_flashes: int
    friendly_flash_rate: float  # 0..100


class UtilityHeatmapResponse(BaseModel):
    steamid: str
    map: str
    has_radar: bool
    grid_size: int
    event_type: str
    cells: list[HeatmapCell]
    friendly_fire: FriendlyFireSummary | None = None


class LifetimeStats(BaseModel):
    matches_played: int
    wins: int
    win_rate: float  # 0..100
    avg_rating: float
    avg_adr: float
    avg_kd: float
    avg_kast: float


class MapPoolEntry(BaseModel):
    map: str
    matches_played: int
    wins: int
    losses: int
    avg_kd: float | None
    win_rate: float | None  # 0..100
    has_data: bool


class MatchHistoryEntry(BaseModel):
    match_id: str
    map: str | None
    n_rounds: int | None
    ingested_at: str | None
    played_at: str | None = None  # matchtime del GC; NULL = ingesta manual sin backfill
    team_num: int | None
    my_score: int | None
    opponent_score: int | None
    won: bool | None
    kills: int
    deaths: int
    assists: int
    adr: float
    kd: float
    rating: float
    hs_pct: float
    rank_type: int | None = None  # 11 = Premier; otro no-null = Competitivo; None = sin clasificar


class MilestoneEntry(BaseModel):
    key: str
    label: str
    value: str
    context: str | None


class CoachInsight(BaseModel):
    text: str
    low_confidence: bool
    matches_analyzed: int


class RankPoint(BaseModel):
    match_id: str
    ingested_at: str | None
    map: str | None
    won: bool | None
    rank: int | None  # NULL = demo viejo sin re-ingerir; 0 = calibrando
    rank_type: int | None  # 11 = Premier
    comp_wins: int | None
    # CS Rating resultante de esta partida y su delta (ver profile.rank_history):
    # el rating de entrada de la partida Premier siguiente. NULL en la última
    # (todavía sin partida posterior) y en puntos no-Premier/calibrando.
    rating_after: int | None = None
    rating_delta: int | None = None


class TacticalSnapshot(BaseModel):
    best_map: str | None
    dominant_role: str | None  # "awper" | "entry" | "support" | "rifler"


class AccuracyStats(BaseModel):
    head_pct: float
    head_hits: int
    body_pct: float
    body_hits: int
    legs_pct: float
    legs_hits: int
    hs_pct_series: list[float]  # oldest-first, últimas N partidas


class TopWeaponEntry(BaseModel):
    name: str
    category: str  # 'rifle' | 'pistol' | 'smg' | 'sniper' | 'shotgun' | 'heavy'
    kills: int


class WeaponDetailEntry(BaseModel):
    name: str
    category: str  # ídem TopWeaponEntry, + 'melee'
    kills: int
    deaths: int
    hs_pct: float
    adr: float
    kills_per_round: float
    longest_kill_m: float


class LoadoutTierStats(BaseModel):
    tier: str  # 'pistol' | 'full_buy' | 'semi_buy' | 'eco'
    rounds: int
    kills: int
    deaths: int
    kd: float
    adr: float
    acs: float  # aproximación propia -- ver domain/loadouts.py
    dd: float  # DDΔ: ADR de este tier menos el ADR lifetime del jugador
    kast_pct: float
    esr_pct: float  # entry success rate


class WeaponsPageResponse(BaseModel):
    weapons: list[WeaponDetailEntry]
    loadouts: list[LoadoutTierStats]


class ProfileResponse(BaseModel):
    steamid: str
    display_name: str | None
    avatar_url: str | None
    lifetime: LifetimeStats
    match_history: list[MatchHistoryEntry]
    map_pool: list[MapPoolEntry]
    milestones: list[MilestoneEntry]
    coach_insights: list[CoachInsight]
    rank_history: list[RankPoint]
    tactical_snapshot: TacticalSnapshot
    accuracy: AccuracyStats
    top_weapons: list[TopWeaponEntry]
    # CS Rating Premier vigente consultado en vivo al GC (Capa 2). None si
    # nunca se pudo (bot no amiga/offline); ahí el frontend cae al rating de
    # entrada de la última partida (Capa 1). Solo se sirve en el perfil propio.
    current_premier_rating: int | None = None
    current_premier_updated_at: str | None = None


class BadgeOut(BaseModel):
    key: str
    kind: str
    icon: str
    title: str
    detail: str


class BadgesResponse(BaseModel):
    badges: list[BadgeOut]


class ProfileTagOut(BaseModel):
    tag_id: str
    detalle: dict | None
    calculado_en: str
    ventana_partidas: int


class ProfileTagsResponse(BaseModel):
    tags: list[ProfileTagOut]


class RoundEconomyOut(BaseModel):
    round_num: int
    steamid: str
    equip_value: int
    tipo_compra: str  # 'full_buy' | 'force_buy' | 'semi_eco' | 'eco'


class MatchEconomyResponse(BaseModel):
    rounds: list[RoundEconomyOut]


class HighlightMomentOut(BaseModel):
    match_id: str
    round_num: int
    score: int
    label: str
    map: str | None
    demo_available: bool  # False = el .dem ya no está en disco, no se puede clipear


class HighlightsResponse(BaseModel):
    moments: list[HighlightMomentOut]


class ClipJobOut(BaseModel):
    id: int
    match_id: str
    round_num: int
    label: str
    status: str  # 'pending' | 'rendering' | 'done' | 'error'
    error: str | None
    created_at: str


class ClipsResponse(BaseModel):
    clips: list[ClipJobOut]


class ClipCreateRequest(BaseModel):
    match_id: str
    round_num: int


class ClutchEntry(BaseModel):
    round_num: int
    enemies_at_start: int
    outcome: str  # "won" | "lost"


class ClutchTimelineResponse(BaseModel):
    clutches: list[ClutchEntry]


class RivalSummary(BaseModel):
    steamid: str
    name: str | None
    matches_together: int
    matches_opposed: int
    avg_rating: float


class RivalsResponse(BaseModel):
    rivals: list[RivalSummary]


class ComparisonMetric(BaseModel):
    key: str
    label: str
    value_a: float
    value_b: float


class TradeUtilitySummary(BaseModel):
    trade_kills: int
    flash_assists: int


class WinrateTogetherSummary(BaseModel):
    matches_together: int  # solo partidas en el MISMO equipo, resultado resuelto
    wins: int
    losses: int
    win_rate: float  # 0..100


class CompareResponse(BaseModel):
    steamid_a: str
    name_a: str | None
    team_num_a: int | None
    steamid_b: str
    name_b: str | None
    team_num_b: int | None
    matches_compared: int
    metrics: list[ComparisonMetric]
    trade_utility: TradeUtilitySummary
    # None = nunca compartieron equipo (pueden haber sido siempre rivales).
    winrate_together: WinrateTogetherSummary | None


class DuelRosterPlayer(BaseModel):
    steamid: str
    name: str | None
    team_num: int  # 2 = T, 3 = CT (bando de la primera ronda)
    # Cacheado en users (registrados) o resuelto vía Steam Web API (best-effort).
    avatar_url: str | None = None


class DuelTeam(BaseModel):
    team_num: int
    players: list[DuelRosterPlayer]


class DuelCell(BaseModel):
    steamid_a: str  # jugador del team_num=2
    steamid_b: str  # jugador del team_num=3
    kills_a: int  # veces que a mató a b
    kills_b: int


class DuelEvent(BaseModel):
    round_num: int | None
    tick: int | None
    attacker: str
    victim: str
    weapon: str | None
    headshot: bool
    thru_smoke: bool
    noscope: bool
    attacker_blind: bool
    distance: float | None
    attacker_u: float | None  # None si el mapa no tiene radar o falta posición
    attacker_v: float | None
    victim_u: float | None
    victim_v: float | None


class DuelsResponse(BaseModel):
    map: str | None
    has_radar: bool
    teams: list[DuelTeam]  # siempre ordenado [team 2, team 3]
    cells: list[DuelCell]
    events: list[DuelEvent]


class NewsItemOut(BaseModel):
    title: str
    summary: str
    url: str
    date: datetime


class NewsResponse(BaseModel):
    items: list[NewsItemOut]


class RankedTeamOut(BaseModel):
    position: int
    name: str
    points: int
    change: int | None  # None = equipo nuevo en el ranking; 0 = sin cambio
    logo_url: str | None  # solo HLTV; Valve no publica logos


class TeamRankingResponse(BaseModel):
    source: str  # "hltv" | "valve" (fallback) | "unavailable"
    teams: list[RankedTeamOut]


class StreamOut(BaseModel):
    platform: str  # "twitch" | "kick"
    channel: str
    channel_slug: str  # para el player embebido (player.twitch.tv / player.kick.com)
    url: str
    title: str
    viewers: int
    language: str  # "es" | "pt"
    thumbnail_url: str


class StreamsResponse(BaseModel):
    # False = no hay credenciales de NINGUNA plataforma (CS2_TWITCH_* / CS2_KICK_*)
    configured: bool
    streams: list[StreamOut]


class MonthlyWindow(BaseModel):
    # "from" es palabra reservada en Python -> alias Pydantic (construir con
    # from_date=..., serializa como "from" en el JSON de salida).
    model_config = {"populate_by_name": True}

    from_date: str = Field(alias="from")
    to: str
    tz: str


class MonthlyTotals(BaseModel):
    matches: int
    winrate: int  # 0..100
    kd: float


class MonthlyHeadline(BaseModel):
    best_streak_wins: int
    rating: float
    hs_pct: int  # 0..100


class MatchesPerDayEntry(BaseModel):
    day: str  # "01".."31", zero-padded día del mes
    count: int


class TopMapEntry(BaseModel):
    map_id: str
    wins: int
    losses: int


class MonthlyMvpOut(BaseModel):
    map_id: str
    round: int
    clutch_size: int
    kills_in_round: int


class MonthlyDetail(BaseModel):
    adr_avg: float
    kast_pct: int
    clutches_won: int
    entry_kills: int
    matches_per_day: list[MatchesPerDayEntry]
    top_maps: list[TopMapEntry]
    mvp: MonthlyMvpOut | None


class MonthlySummaryResponse(BaseModel):
    window: MonthlyWindow
    totals: MonthlyTotals
    headline: MonthlyHeadline
    detail: MonthlyDetail
