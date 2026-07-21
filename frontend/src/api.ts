import type {
  AutofetchStatus,
  BadgesResponse,
  ClutchTimelineResponse,
  DuelsResponse,
  KillsResponse,
  MatchDetail,
  MatchSummary,
  MonthlySummaryResponse,
  NewsResponse,
  ProfileResponse,
  StreamsResponse,
  TeamRankingResponse,
  User,
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

export async function listMatches(): Promise<MatchSummary[]> {
  const r = await fetch(`${BASE}/matches`);
  if (!r.ok) throw new Error(`GET /matches -> ${r.status}`);
  return r.json();
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
