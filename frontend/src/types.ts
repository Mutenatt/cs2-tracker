// Contrato con el backend (espeja los schemas Pydantic de la API).

export interface User {
  steamid: string;
  display_name: string | null;
  avatar_url: string | null;
}

export interface MatchSummary {
  match_id: string;
  map: string | null;
  n_rounds: number | null;
  ingested_at?: string | null;
  played_at?: string | null; // matchtime del GC; null = ingesta manual sin backfill
}

export interface PlayerRow {
  steamid: string;
  name: string | null;
  team_num: number | null;
  rank: number | null; // CS Rating crudo del demo; 0 = calibrando
  rank_type: number | null; // 11 = Premier
  kills: number;
  deaths: number;
  assists: number;
  damage: number;
  adr: number;
  kd: number;
  hs_pct: number;
  kast: number;
  entry_kills: number;
  entry_deaths: number;
  k2: number;
  k3: number;
  k4: number;
  k5: number;
  clutches: number;
  rating: number;
}

export interface TeamScore {
  team_num: number;
  score: number;
}

export interface MatchDetail {
  match: MatchSummary;
  teams: TeamScore[];
  scoreboard: PlayerRow[];
}

export interface KillPoint {
  u: number;
  v: number;
  headshot: boolean;
  victim_team: number | null;
}

export interface KillsResponse {
  map: string | null;
  has_radar: boolean;
  kills: KillPoint[];
}

export interface WeaponStat {
  weapon: string;
  kills: number;
  damage: number;
}

export interface PlayerWeapons {
  steamid: string;
  name: string | null;
  top_weapons: WeaponStat[];
  hitgroups: Record<string, number>;
}

export interface WeaponsResponse {
  players: PlayerWeapons[];
}

export interface LifetimeStats {
  matches_played: number;
  wins: number;
  win_rate: number;
  avg_rating: number;
  avg_adr: number;
  avg_kd: number;
  avg_kast: number;
}

export interface MapPoolEntry {
  map: string;
  matches_played: number;
  wins: number;
  losses: number;
  avg_kd: number | null;
  win_rate: number | null;
  has_data: boolean;
}

export interface MatchHistoryEntry {
  match_id: string;
  map: string | null;
  n_rounds: number | null;
  ingested_at: string | null;
  played_at?: string | null; // matchtime del GC; null = ingesta manual sin backfill
  team_num: number | null;
  my_score: number | null;
  opponent_score: number | null;
  won: boolean | null;
  kills: number;
  deaths: number;
  assists: number;
  adr: number;
  kd: number;
  rating: number;
  hs_pct: number;
  rank_type: number | null; // 11 = Premier; otro no-null = Competitivo; null = sin clasificar
}

export interface Badge {
  key: string;
  kind: "good" | "warn";
  icon: string;
  title: string;
  detail: string;
}

export interface BadgesResponse {
  badges: Badge[];
}

export interface ClutchEntry {
  round_num: number;
  enemies_at_start: number;
  outcome: "won" | "lost";
}

export interface ClutchTimelineResponse {
  clutches: ClutchEntry[];
}

export interface MilestoneEntry {
  key: string;
  label: string;
  value: string;
  context: string | null;
}

export interface CoachInsight {
  text: string;
  low_confidence: boolean;
  matches_analyzed: number;
}

export interface AccuracyStats {
  head_pct: number;
  head_hits: number;
  body_pct: number;
  body_hits: number;
  legs_pct: number;
  legs_hits: number;
  hs_pct_series: number[]; // oldest-first, últimas N partidas
}

export type WeaponCategory = "rifle" | "pistol" | "smg" | "sniper" | "shotgun" | "heavy" | "melee";

export interface TopWeaponEntry {
  name: string;
  category: WeaponCategory;
  kills: number;
}

export interface WeaponDetailEntry {
  name: string;
  category: WeaponCategory;
  kills: number;
  deaths: number;
  hs_pct: number;
  adr: number;
  kills_per_round: number;
  longest_kill_m: number;
}

export type LoadoutTier = "pistol" | "full_buy" | "semi_buy" | "eco";

export interface LoadoutTierStats {
  tier: LoadoutTier;
  rounds: number;
  kills: number;
  deaths: number;
  kd: number;
  adr: number;
  acs: number;
  dd: number;
  kast_pct: number;
  esr_pct: number;
}

export interface WeaponsPageResponse {
  weapons: WeaponDetailEntry[];
  loadouts: LoadoutTierStats[];
}

export interface ProfileResponse {
  steamid: string;
  display_name: string | null;
  avatar_url: string | null;
  lifetime: LifetimeStats;
  match_history: MatchHistoryEntry[];
  map_pool: MapPoolEntry[];
  milestones: MilestoneEntry[];
  coach_insights: CoachInsight[];
  rank_history: RankPoint[];
  tactical_snapshot: TacticalSnapshot;
  accuracy: AccuracyStats;
  top_weapons: TopWeaponEntry[];
  current_premier_rating: number | null; // rating vivo del GC (solo perfil propio)
  current_premier_updated_at: string | null;
}

export interface DuelRosterPlayer {
  steamid: string;
  name: string | null;
  team_num: number; // 2 = T, 3 = CT (bando de la primera ronda)
  avatar_url: string | null; // users cacheado o Steam Web API (best-effort)
}

export interface DuelTeam {
  team_num: number;
  players: DuelRosterPlayer[];
}

export interface DuelCell {
  steamid_a: string; // jugador del team_num=2
  steamid_b: string; // jugador del team_num=3
  kills_a: number; // veces que a mató a b
  kills_b: number;
}

export interface DuelEvent {
  round_num: number | null;
  tick: number | null;
  attacker: string;
  victim: string;
  weapon: string | null;
  headshot: boolean;
  thru_smoke: boolean;
  noscope: boolean;
  attacker_blind: boolean;
  distance: number | null;
  attacker_u: number | null;
  attacker_v: number | null;
  victim_u: number | null;
  victim_v: number | null;
}

export interface DuelsResponse {
  map: string | null;
  has_radar: boolean;
  teams: DuelTeam[]; // siempre ordenado [team 2, team 3]
  cells: DuelCell[];
  events: DuelEvent[];
}

export interface RankPoint {
  match_id: string;
  ingested_at: string | null;
  map: string | null;
  won: boolean | null;
  rank: number | null; // NULL = demo viejo sin re-ingerir; 0 = calibrando
  rank_type: number | null; // 11 = Premier
  comp_wins: number | null;
  rating_after: number | null; // CS Rating resultante (entrada de la partida siguiente)
  rating_delta: number | null; // +/- de esta partida; NULL en la última y no-Premier
}

export interface TacticalSnapshot {
  best_map: string | null;
  dominant_role: string | null; // "awper" | "entry" | "support" | "rifler"
}

export interface ComparisonMetric {
  key: string;
  label: string;
  value_a: number;
  value_b: number;
}

export interface TradeUtilitySummary {
  trade_kills: number;
  flash_assists: number;
}

export interface WinrateTogetherSummary {
  matches_together: number; // solo partidas en el MISMO equipo, resultado resuelto
  wins: number;
  losses: number;
  win_rate: number; // 0..100
}

export interface CompareResponse {
  steamid_a: string;
  name_a: string | null;
  team_num_a: number | null;
  steamid_b: string;
  name_b: string | null;
  team_num_b: number | null;
  matches_compared: number;
  metrics: ComparisonMetric[];
  trade_utility: TradeUtilitySummary;
  winrate_together: WinrateTogetherSummary | null; // null = nunca compartieron equipo
}

export interface RivalSummary {
  steamid: string;
  name: string | null;
  matches_together: number;
  matches_opposed: number;
  avg_rating: number;
}

export interface RivalsResponse {
  rivals: RivalSummary[];
}

export interface ProfileTag {
  tag_id: string;
  detalle: Record<string, number | string> | null;
  calculado_en: string;
  ventana_partidas: number;
}

export interface ProfileTagsResponse {
  tags: ProfileTag[];
}

export type TipoCompra = "full_buy" | "force_buy" | "semi_eco" | "eco";

export interface RoundEconomyEntry {
  round_num: number;
  steamid: string;
  equip_value: number;
  tipo_compra: TipoCompra;
}

export interface MatchEconomyResponse {
  rounds: RoundEconomyEntry[];
}

export interface HighlightMoment {
  match_id: string;
  round_num: number;
  score: number;
  label: string;
  map: string | null;
  demo_available: boolean; // false = el .dem ya no está en disco, no clipeable
}

export interface HighlightsResponse {
  moments: HighlightMoment[];
}

export interface ClipJob {
  id: number;
  match_id: string;
  round_num: number;
  label: string;
  status: "pending" | "rendering" | "done" | "error";
  error: string | null;
  created_at: string;
}

export interface ClipsResponse {
  clips: ClipJob[];
}

export interface AutofetchStatus {
  linked: boolean;
  status: "active" | "revoked" | "error" | null;
  error: string | null;
  last_sharecode: string | null;
  last_polled_at: string | null;
  last_fetched_at: string | null;
}

export interface NewsItemDto {
  title: string;
  summary: string;
  url: string;
  date: string;
}

export interface NewsResponse {
  items: NewsItemDto[];
}

export interface RankedTeamDto {
  position: number;
  name: string;
  points: number;
  change: number | null; // null = equipo nuevo en el ranking; 0 = sin cambio
  logo_url: string | null; // solo HLTV; Valve no publica logos
}

export interface TeamRankingResponse {
  source: "hltv" | "valve" | "unavailable";
  teams: RankedTeamDto[];
}

export interface StreamDto {
  platform: "twitch" | "kick";
  channel: string;
  channel_slug: string; // para el player embebido (player.twitch.tv / player.kick.com)
  url: string;
  title: string;
  viewers: number;
  language: string; // "es" | "pt"
  thumbnail_url: string;
}

export interface StreamsResponse {
  // false = no hay credenciales de ninguna plataforma (CS2_TWITCH_* / CS2_KICK_*)
  configured: boolean;
  streams: StreamDto[];
}

export interface MonthlyWindow {
  from: string;
  to: string;
  tz: string;
}

export interface MonthlyTotals {
  matches: number;
  winrate: number; // 0..100
  kd: number;
}

export interface MonthlyHeadline {
  best_streak_wins: number;
  rating: number;
  hs_pct: number; // 0..100
}

export interface MatchesPerDayEntry {
  day: string; // "01".."31", zero-padded día del mes
  count: number;
}

export interface TopMapEntry {
  map_id: string;
  wins: number;
  losses: number;
}

export interface MonthlyMvp {
  map_id: string;
  round: number;
  clutch_size: number;
  kills_in_round: number;
}

export interface MonthlyDetail {
  adr_avg: number;
  kast_pct: number;
  clutches_won: number;
  entry_kills: number;
  matches_per_day: MatchesPerDayEntry[];
  top_maps: TopMapEntry[];
  mvp: MonthlyMvp | null;
}

export interface MonthlySummaryResponse {
  window: MonthlyWindow;
  totals: MonthlyTotals;
  headline: MonthlyHeadline;
  detail: MonthlyDetail;
}
