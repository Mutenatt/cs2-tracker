import type {
  AutofetchStatus,
  BadgesResponse,
  ClipJob,
  ClipsResponse,
  ClutchTimelineResponse,
  CompareResponse,
  HighlightsResponse,
  DuelsResponse,
  KillsResponse,
  MatchDetail,
  MatchEconomyResponse,
  MonthlySummaryResponse,
  NewsResponse,
  ProfileResponse,
  ProfileTagsResponse,
  RivalsResponse,
  StreamsResponse,
  TeamRankingResponse,
  User,
  WeaponsPageResponse,
  WeaponsResponse,
} from "./types";

// En dev, vite proxya /api -> FastAPI. En prod (webview) se sirve del mismo origen.
const BASE = "/api";

export async function getMe(): Promise<User | null> {
  const r = await fetch(`${BASE}/auth/me`);
  if (r.status === 401) return null;
  if (!r.ok) throw new Error(`GET /auth/me -> ${r.status}`);
  return r.json();
}

export function loginUrl(): string {
  return `${BASE}/auth/login`;
}

export async function logout(): Promise<void> {
  const r = await fetch(`${BASE}/auth/logout`, { method: "POST" });
  if (!r.ok) throw new Error(`POST /auth/logout -> ${r.status}`);
}

export async function getMatch(matchId: string): Promise<MatchDetail> {
  const r = await fetch(`${BASE}/matches/${matchId}`);
  if (!r.ok) throw new Error(`GET /matches/${matchId} -> ${r.status}`);
  return r.json();
}

export async function getKills(matchId: string): Promise<KillsResponse> {
  const r = await fetch(`${BASE}/matches/${matchId}/kills`);
  if (!r.ok) throw new Error(`GET kills -> ${r.status}`);
  return r.json();
}

export async function getWeapons(matchId: string): Promise<WeaponsResponse> {
  const r = await fetch(`${BASE}/matches/${matchId}/weapons`);
  if (!r.ok) throw new Error(`GET weapons -> ${r.status}`);
  return r.json();
}

export async function getMatchDuels(matchId: string): Promise<DuelsResponse> {
  const r = await fetch(`${BASE}/matches/${matchId}/duels`);
  if (!r.ok) throw new Error(`GET duels -> ${r.status}`);
  return r.json();
}

export async function getMatchBadges(matchId: string, steamid: string): Promise<BadgesResponse> {
  const r = await fetch(`${BASE}/matches/${matchId}/badges?steamid=${steamid}`);
  if (!r.ok) throw new Error(`GET badges -> ${r.status}`);
  return r.json();
}

export async function getMatchClutches(
  matchId: string,
  steamid: string
): Promise<ClutchTimelineResponse> {
  const r = await fetch(`${BASE}/matches/${matchId}/clutches?steamid=${steamid}`);
  if (!r.ok) throw new Error(`GET clutches -> ${r.status}`);
  return r.json();
}

export async function getCs2News(): Promise<NewsResponse> {
  const r = await fetch(`${BASE}/news/cs2`);
  if (!r.ok) throw new Error(`GET news -> ${r.status}`);
  return r.json();
}

export async function getTeamRanking(): Promise<TeamRankingResponse> {
  const r = await fetch(`${BASE}/scene/ranking`);
  if (!r.ok) throw new Error(`GET scene ranking -> ${r.status}`);
  return r.json();
}

export async function getLatamStreams(): Promise<StreamsResponse> {
  const r = await fetch(`${BASE}/scene/streams`);
  if (!r.ok) throw new Error(`GET scene streams -> ${r.status}`);
  return r.json();
}

export async function getProfile(steamid: string): Promise<ProfileResponse> {
  const r = await fetch(`${BASE}/players/${steamid}/profile`);
  if (!r.ok) throw new Error(`GET profile -> ${r.status}`);
  return r.json();
}

export async function getWeaponsDetail(steamid: string): Promise<WeaponsPageResponse> {
  const r = await fetch(`${BASE}/players/${steamid}/weapons-detail`);
  if (!r.ok) throw new Error(`GET weapons-detail -> ${r.status}`);
  return r.json();
}

export async function getProfileTags(steamid: string): Promise<ProfileTagsResponse> {
  const r = await fetch(`${BASE}/players/${steamid}/profile-tags`);
  if (!r.ok) throw new Error(`GET profile-tags -> ${r.status}`);
  return r.json();
}

export async function getRivals(steamid: string): Promise<RivalsResponse> {
  const r = await fetch(`${BASE}/players/${steamid}/rivals`);
  if (!r.ok) throw new Error(`GET rivals -> ${r.status}`);
  return r.json();
}

export async function getCompare(steamidA: string, steamidB: string): Promise<CompareResponse> {
  const r = await fetch(`${BASE}/players/${steamidA}/compare/${steamidB}`);
  if (!r.ok) throw new Error(`GET compare -> ${r.status}`);
  return r.json();
}

export async function getMatchEconomy(matchId: string): Promise<MatchEconomyResponse> {
  const r = await fetch(`${BASE}/matches/${matchId}/economy`);
  if (!r.ok) throw new Error(`GET economy -> ${r.status}`);
  return r.json();
}

export async function getHighlights(steamid: string): Promise<HighlightsResponse> {
  const r = await fetch(`${BASE}/players/${steamid}/highlights`);
  if (!r.ok) throw new Error(`GET highlights -> ${r.status}`);
  return r.json();
}

export async function getClips(steamid: string): Promise<ClipsResponse> {
  const r = await fetch(`${BASE}/players/${steamid}/clips`);
  if (!r.ok) throw new Error(`GET clips -> ${r.status}`);
  return r.json();
}

export async function createClip(
  steamid: string,
  matchId: string,
  roundNum: number
): Promise<ClipJob> {
  const r = await fetch(`${BASE}/players/${steamid}/clips`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ match_id: matchId, round_num: roundNum }),
  });
  if (!r.ok) throw new Error(`POST clips -> ${r.status}`);
  return r.json();
}

export function clipDownloadUrl(jobId: number): string {
  return `${BASE}/clips/${jobId}/download`;
}

export async function getMonthlySummary(steamid: string): Promise<MonthlySummaryResponse> {
  const r = await fetch(`${BASE}/players/${steamid}/monthly`);
  if (!r.ok) throw new Error(`GET monthly -> ${r.status}`);
  return r.json();
}

export async function getAutofetchStatus(): Promise<AutofetchStatus> {
  const r = await fetch(`${BASE}/autofetch/status`);
  if (!r.ok) throw new Error(`GET autofetch status -> ${r.status}`);
  return r.json();
}

export async function linkAutofetch(authCode: string, sharecode: string): Promise<AutofetchStatus> {
  const r = await fetch(`${BASE}/autofetch/link`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ auth_code: authCode, sharecode }),
  });
  if (!r.ok) {
    // El backend manda mensajes de error legibles en `detail`.
    const detail = (await r.json().catch(() => null))?.detail;
    throw new Error(typeof detail === "string" ? detail : `POST autofetch link -> ${r.status}`);
  }
  return r.json();
}

export async function unlinkAutofetch(): Promise<AutofetchStatus> {
  const r = await fetch(`${BASE}/autofetch/link`, { method: "DELETE" });
  if (!r.ok) throw new Error(`DELETE autofetch link -> ${r.status}`);
  return r.json();
}

export async function setCustomBackground(url: string): Promise<User> {
  const r = await fetch(`${BASE}/auth/me/background`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!r.ok) {
    const detail = (await r.json().catch(() => null))?.detail;
    throw new Error(typeof detail === "string" ? detail : `PATCH me/background -> ${r.status}`);
  }
  return r.json();
}

export async function clearCustomBackground(): Promise<User> {
  const r = await fetch(`${BASE}/auth/me/background`, { method: "DELETE" });
  if (!r.ok) throw new Error(`DELETE me/background -> ${r.status}`);
  return r.json();
}
