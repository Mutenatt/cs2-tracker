"""FastAPI: sirve el SQLite como JSON tipado al frontend."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from cs2tracker import maps
from cs2tracker.api import queries
from cs2tracker.api.autofetch import router as autofetch_router
from cs2tracker.api.scene import router as scene_router
from cs2tracker.api.schemas import (
    AccuracyStats,
    BadgeOut,
    BadgesResponse,
    ClipCreateRequest,
    ClipJobOut,
    ClipsResponse,
    ClutchEntry,
    ClutchTimelineResponse,
    CoachInsight,
    CompareResponse,
    ComparisonMetric,
    DuelCell,
    DuelEvent,
    DuelRosterPlayer,
    DuelsResponse,
    DuelTeam,
    EntryHeatmapResponse,
    FriendlyFireSummary,
    HeatmapCell,
    HeatmapResponse,
    HighlightMomentOut,
    HighlightsResponse,
    KillPoint,
    KillsResponse,
    LifetimeStats,
    LoadoutTierStats,
    MapPoolEntry,
    MatchDetail,
    MatchEconomyResponse,
    MatchesPerDayEntry,
    MatchHistoryEntry,
    MatchSummary,
    MilestoneEntry,
    MonthlyDetail,
    MonthlyHeadline,
    MonthlyMvpOut,
    MonthlySummaryResponse,
    MonthlyTotals,
    MonthlyWindow,
    NewsItemOut,
    NewsResponse,
    PlayerRow,
    PlayerWeapons,
    ProfileResponse,
    ProfileTagOut,
    ProfileTagsResponse,
    RankPoint,
    RivalsResponse,
    RivalSummary,
    RoundEconomyOut,
    TacticalSnapshot,
    TeamScore,
    TopMapEntry,
    TopWeaponEntry,
    TradeUtilitySummary,
    UserOut,
    UtilityHeatmapResponse,
    WeaponDetailEntry,
    WeaponsPageResponse,
    WeaponsResponse,
    WeaponStat,
    WinrateTogetherSummary,
)
from cs2tracker.auth import (
    COOKIE_NAME,
    SESSION_MAX_AGE,
    build_login_url,
    create_session_cookie,
    fetch_profile,
    fetch_profiles,
    get_current_steamid,
    verify_callback,
)
from cs2tracker.config import settings
from cs2tracker.db import (
    ClipJob,
    Damage,
    Kill,
    Match,
    MatchPlayer,
    Player,
    PlayerMapZone,
    PlayerMatchStats,
    Round,
    RoundEconomy,
    User,
    init_db,
)
from cs2tracker.db.session import get_engine
from cs2tracker.domain import badges as badges_domain
from cs2tracker.domain import coach as coach_domain
from cs2tracker.domain import duels as duels_domain
from cs2tracker.domain import economia as economia_domain
from cs2tracker.domain import loadouts as loadouts_domain
from cs2tracker.domain import monthly as monthly_domain
from cs2tracker.domain import profile as profile_domain
from cs2tracker.domain import roles as roles_domain
from cs2tracker.infra import steam_news


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(title="cStats API", version="0.1", lifespan=lifespan)
# allow_credentials + wildcard no son compatibles (los navegadores lo
# rechazan): la cookie de sesión de auth.py exige un origen explícito.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(autofetch_router)
app.include_router(scene_router)


@app.get("/auth/login")
def auth_login() -> RedirectResponse:
    return RedirectResponse(build_login_url())


@app.get("/auth/callback")
async def auth_callback(request: Request) -> RedirectResponse:
    steamid = await verify_callback(dict(request.query_params))
    if steamid is None:
        raise HTTPException(400, "login de Steam inválido")

    display_name, avatar_url = await fetch_profile(steamid)
    now = datetime.now(UTC).isoformat()
    with Session(get_engine()) as s:
        if s.get(Player, steamid) is None:
            s.add(Player(steamid=steamid, name=display_name))
        elif display_name:
            s.get(Player, steamid).name = display_name

        user = s.get(User, steamid)
        if user is None:
            s.add(
                User(
                    steamid=steamid,
                    display_name=display_name,
                    avatar_url=avatar_url,
                    last_login_at=now,
                )
            )
        else:
            user.last_login_at = now
            if display_name:
                user.display_name = display_name
            if avatar_url:
                user.avatar_url = avatar_url
        s.commit()

    resp = RedirectResponse(settings.frontend_url)
    resp.set_cookie(
        COOKIE_NAME,
        create_session_cookie(steamid),
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
    )
    return resp


@app.get("/auth/me", response_model=UserOut)
def auth_me(steamid: str = Depends(get_current_steamid)) -> UserOut:
    with Session(get_engine()) as s:
        user = s.get(User, steamid)
        if user is None:
            raise HTTPException(404, "usuario no encontrado")
        return UserOut(
            steamid=user.steamid, display_name=user.display_name, avatar_url=user.avatar_url
        )


@app.post("/auth/logout")
def auth_logout() -> JSONResponse:
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(COOKIE_NAME)
    return resp


@app.get("/matches", response_model=list[MatchSummary])
def list_matches(viewer: str = Depends(get_current_steamid)) -> list[MatchSummary]:
    with Session(get_engine()) as s:
        # Por match_id, no por ingested_at: el match_id de Valve es monótono
        # creciente y zero-padded -> orden cronológico REAL de juego, aunque
        # los demos se hayan ingerido en cualquier orden (auto-fetch).
        # Solo las partidas del viewer -- pertenencia, no un listado global.
        rows = (
            s.execute(
                select(Match)
                .join(MatchPlayer, MatchPlayer.match_id == Match.match_id)
                .where(MatchPlayer.steamid == viewer)
                .order_by(Match.match_id.desc())
            )
            .scalars()
            .all()
        )
        return [
            MatchSummary(
                match_id=m.match_id,
                map=m.map,
                n_rounds=m.n_rounds,
                ingested_at=m.ingested_at,
                played_at=m.played_at,
            )
            for m in rows
        ]


@app.get("/news/cs2", response_model=NewsResponse)
async def cs2_news(_viewer: str = Depends(get_current_steamid)) -> NewsResponse:
    items = await steam_news.fetch_cs2_news(count=8)
    return NewsResponse(
        items=[
            NewsItemOut(title=i.title, summary=i.summary, url=i.url, date=i.date) for i in items[:4]
        ]
    )


@app.get("/matches/{match_id}", response_model=MatchDetail)
def match_detail(match_id: str, viewer: str = Depends(get_current_steamid)) -> MatchDetail:
    with Session(get_engine()) as s:
        m = s.get(Match, match_id)
        if m is None:
            raise HTTPException(404, "match no encontrado")
        _authorize_match(s, viewer, match_id)
        q = (
            select(
                PlayerMatchStats,
                Player.name,
                MatchPlayer.team_num,
                MatchPlayer.rank,
                MatchPlayer.rank_type,
            )
            .join(Player, Player.steamid == PlayerMatchStats.steamid)
            .join(
                MatchPlayer,
                (MatchPlayer.steamid == PlayerMatchStats.steamid)
                & (MatchPlayer.match_id == PlayerMatchStats.match_id),
            )
            .where(PlayerMatchStats.match_id == match_id)
            .order_by(PlayerMatchStats.rating.desc())
        )
        board = [
            PlayerRow(
                steamid=st.steamid,
                name=name,
                team_num=team_num,
                rank=rank,
                rank_type=rank_type,
                kills=st.kills,
                deaths=st.deaths,
                assists=st.assists,
                damage=st.damage,
                adr=st.adr,
                kd=st.kd,
                hs_pct=st.hs_pct,
                kast=st.kast,
                entry_kills=st.entry_kills,
                entry_deaths=st.entry_deaths,
                k2=st.k2,
                k3=st.k3,
                k4=st.k4,
                k5=st.k5,
                clutches=st.clutches,
                rating=st.rating,
            )
            for st, name, team_num, rank, rank_type in s.execute(q).all()
        ]
        score_rows = s.execute(
            select(Round.winner_num, func.count())
            .where(Round.match_id == match_id, Round.winner_num.is_not(None))
            .group_by(Round.winner_num)
        ).all()
        teams = [TeamScore(team_num=tn, score=c) for tn, c in score_rows]
        teams.sort(key=lambda t: t.score, reverse=True)

        return MatchDetail(
            match=MatchSummary(
                match_id=m.match_id,
                map=m.map,
                n_rounds=m.n_rounds,
                ingested_at=m.ingested_at,
                played_at=m.played_at,
            ),
            teams=teams,
            scoreboard=board,
        )


@app.get("/matches/{match_id}/kills", response_model=KillsResponse)
def match_kills(match_id: str, viewer: str = Depends(get_current_steamid)) -> KillsResponse:
    """Muertes proyectadas al radar (u,v en 0..1) para el heatmap."""
    with Session(get_engine()) as s:
        m = s.get(Match, match_id)
        if m is None:
            raise HTTPException(404, "match no encontrado")
        _authorize_match(s, viewer, match_id)
        rows = s.execute(
            select(Kill.victim_x, Kill.victim_y, Kill.headshot, MatchPlayer.team_num)
            .outerjoin(
                MatchPlayer,
                (MatchPlayer.steamid == Kill.victim) & (MatchPlayer.match_id == Kill.match_id),
            )
            .where(Kill.match_id == match_id, Kill.victim_x.is_not(None))
        ).all()

        points: list[KillPoint] = []
        for vx, vy, hs, team in rows:
            uv = maps.to_radar_norm(m.map, vx, vy)
            if uv is None:
                continue
            points.append(KillPoint(u=uv[0], v=uv[1], headshot=bool(hs), victim_team=team))
        return KillsResponse(map=m.map, has_radar=maps.has_radar(m.map), kills=points)


@app.get("/matches/{match_id}/duels", response_model=DuelsResponse)
async def match_duels(match_id: str, viewer: str = Depends(get_current_steamid)) -> DuelsResponse:
    """Matriz de duelos 1v1 (kills vs deaths por par cross-team) + eventos
    crudos para el drill-down, con posiciones proyectadas al radar."""
    with Session(get_engine()) as s:
        m = s.get(Match, match_id)
        if m is None:
            raise HTTPException(404, "match no encontrado")
        _authorize_match(s, viewer, match_id)

        roster_rows = s.execute(
            select(MatchPlayer.steamid, MatchPlayer.team_num, Player.name)
            .join(Player, Player.steamid == MatchPlayer.steamid)
            .where(MatchPlayer.match_id == match_id, MatchPlayer.team_num.in_([2, 3]))
            .order_by(Player.name)
        ).all()
        roster = {sid: tn for sid, tn, _name in roster_rows}

        # Avatares ya cacheados de usuarios registrados (tabla users).
        avatars: dict[str, str | None] = dict(
            s.execute(
                select(User.steamid, User.avatar_url).where(User.steamid.in_(roster.keys()))
            ).all()
        )

        kill_rows = s.execute(select(Kill).where(Kill.match_id == match_id)).scalars().all()
        kills = [
            {
                "attacker": k.attacker,
                "victim": k.victim,
                "round_num": k.round_num,
                "tick": k.tick,
                "weapon": k.weapon,
                "headshot": k.headshot,
                "thru_smoke": k.thru_smoke,
                "noscope": k.noscope,
                "attacker_blind": k.attacker_blind,
                "distance": k.distance,
                "attacker_x": k.attacker_x,
                "attacker_y": k.attacker_y,
                "victim_x": k.victim_x,
                "victim_y": k.victim_y,
            }
            for k in kill_rows
        ]
        data = duels_domain.compute_duels(kills, roster)

        def project(x: float | None, y: float | None) -> tuple[float | None, float | None]:
            if x is None or y is None:
                return None, None
            uv = maps.to_radar_norm(m.map, x, y)
            return (None, None) if uv is None else uv

        events: list[DuelEvent] = []
        for e in data.events:
            au, av = project(e["attacker_x"], e["attacker_y"])
            vu, vv = project(e["victim_x"], e["victim_y"])
            events.append(
                DuelEvent(
                    round_num=e["round_num"],
                    tick=e["tick"],
                    attacker=e["attacker"],
                    victim=e["victim"],
                    weapon=e["weapon"],
                    headshot=bool(e["headshot"]),
                    thru_smoke=bool(e["thru_smoke"]),
                    noscope=bool(e["noscope"]),
                    attacker_blind=bool(e["attacker_blind"]),
                    distance=e["distance"],
                    attacker_u=au,
                    attacker_v=av,
                    victim_u=vu,
                    victim_v=vv,
                )
            )

        teams = [
            DuelTeam(
                team_num=tn,
                players=[
                    DuelRosterPlayer(
                        steamid=sid, name=name, team_num=ptn, avatar_url=avatars.get(sid)
                    )
                    for sid, ptn, name in roster_rows
                    if ptn == tn
                ],
            )
            for tn in (2, 3)
        ]
        response = DuelsResponse(
            map=m.map,
            has_radar=maps.has_radar(m.map),
            teams=teams,
            cells=[DuelCell(**p) for p in data.pairs],
            events=events,
        )

    # Fuera de la sesión (llamada de red): resolver best-effort los avatares
    # que la tabla users no cubre (rivales no registrados).
    missing = [sid for sid in roster if not avatars.get(sid)]
    fetched = await fetch_profiles(missing)
    for team in response.teams:
        for p in team.players:
            if p.avatar_url is None and p.steamid in fetched:
                p.avatar_url = fetched[p.steamid][1]
    return response


@app.get("/matches/{match_id}/weapons", response_model=WeaponsResponse)
def match_weapons(match_id: str, viewer: str = Depends(get_current_steamid)) -> WeaponsResponse:
    """Daño/kills por arma y distribución de hitgroups, por jugador."""
    with Session(get_engine()) as s:
        m = s.get(Match, match_id)
        if m is None:
            raise HTTPException(404, "match no encontrado")
        _authorize_match(s, viewer, match_id)

        names = dict(
            s.execute(
                select(MatchPlayer.steamid, Player.name)
                .join(Player, Player.steamid == MatchPlayer.steamid)
                .where(MatchPlayer.match_id == match_id)
            ).all()
        )

        dmg_by_wpn: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        hitgroups: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for atk, wpn, dmg, hg in s.execute(
            select(Damage.attacker, Damage.weapon, Damage.dmg_health, Damage.hitgroup).where(
                Damage.match_id == match_id, Damage.attacker.is_not(None)
            )
        ).all():
            dmg_by_wpn[atk][wpn or "?"] += dmg or 0
            hitgroups[atk][hg or "?"] += dmg or 0

        kills_by_wpn: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        for atk, wpn in s.execute(
            select(Kill.attacker, Kill.weapon).where(
                Kill.match_id == match_id, Kill.attacker.is_not(None)
            )
        ).all():
            kills_by_wpn[atk][wpn or "?"] += 1

        players: list[PlayerWeapons] = []
        for sid in names:
            wpns = dmg_by_wpn.get(sid, {})
            top = sorted(wpns.items(), key=lambda kv: kv[1], reverse=True)[:3]
            players.append(
                PlayerWeapons(
                    steamid=sid,
                    name=names.get(sid),
                    top_weapons=[
                        WeaponStat(weapon=w, damage=d, kills=kills_by_wpn.get(sid, {}).get(w, 0))
                        for w, d in top
                    ],
                    hitgroups=dict(hitgroups.get(sid, {})),
                )
            )
        return WeaponsResponse(players=players)


_UTILITY_TYPE_TO_EVENT = {
    "flash": "flash_thrown",
    "he": "he_thrown",
    "molotov": "molotov_thrown",
    "smoke": "smoke_thrown",
}


def _authorize_view(s: Session, viewer: str, target: str) -> None:
    if not queries.shares_a_match(s, viewer, target):
        raise HTTPException(403, "no compartís ninguna partida con ese jugador")


def _authorize_match(s: Session, viewer: str, match_id: str) -> None:
    if not queries.is_participant(s, viewer, match_id):
        raise HTTPException(403, "no participaste en esa partida")


def _authorize_self(viewer: str, steamid: str) -> None:
    """Más estricto que _authorize_view: el resumen mensual es privado del
    usuario, ni siquiera compartir una partida alcanza para verlo (a
    diferencia de heatmaps/profile/rivals/compare)."""
    if viewer != steamid:
        raise HTTPException(403, "el resumen mensual es privado")


def _to_cell(zone: PlayerMapZone, count: int) -> HeatmapCell:
    return HeatmapCell(
        grid_x=zone.grid_x,
        grid_y=zone.grid_y,
        count=count,
        top_weapon=zone.top_weapon,
        avg_enemies_blinded=zone.avg_enemies_blinded,
        total_blind_duration=zone.total_blind_duration,
        avg_damage=zone.avg_damage,
    )


@app.get("/players/{steamid}/heatmaps/deaths", response_model=HeatmapResponse)
def heatmap_deaths(
    steamid: str,
    map: str,
    viewer: str = Depends(get_current_steamid),
) -> HeatmapResponse:
    with Session(get_engine()) as s:
        _authorize_view(s, viewer, steamid)
        zones = queries.zones_by_event_type(s, steamid, map, "death")
        cells = [_to_cell(z, z.count) for z in zones if z.count >= queries.MIN_SAMPLE]
        return HeatmapResponse(
            steamid=steamid,
            map=map,
            has_radar=maps.has_radar(map),
            grid_size=maps.GRID_CELLS_PER_AXIS,
            cells=cells,
        )


@app.get("/players/{steamid}/heatmaps/entries", response_model=EntryHeatmapResponse)
def heatmap_entries(
    steamid: str,
    map: str,
    viewer: str = Depends(get_current_steamid),
) -> EntryHeatmapResponse:
    """Dónde gana (entry_kills) y dónde pierde (entry_deaths) la apertura de
    ronda. El conteo por celda es la cantidad de ENTRIES, no de kills/deaths
    en general -- mezclar ambas cosas sería otra métrica."""
    with Session(get_engine()) as s:
        _authorize_view(s, viewer, steamid)
        kills = queries.zones_by_event_type(s, steamid, map, "kill")
        deaths = queries.zones_by_event_type(s, steamid, map, "death")
        min_sample = queries.MIN_SAMPLE
        entry_kills = [_to_cell(z, z.entry_count) for z in kills if z.entry_count >= min_sample]
        entry_deaths = [_to_cell(z, z.entry_count) for z in deaths if z.entry_count >= min_sample]
        return EntryHeatmapResponse(
            steamid=steamid,
            map=map,
            has_radar=maps.has_radar(map),
            grid_size=maps.GRID_CELLS_PER_AXIS,
            entry_kills=entry_kills,
            entry_deaths=entry_deaths,
        )


@app.get("/players/{steamid}/heatmaps/trades", response_model=HeatmapResponse)
def heatmap_trades(
    steamid: str,
    map: str,
    viewer: str = Depends(get_current_steamid),
) -> HeatmapResponse:
    """Dónde muere SIN ser vengado (count = muertes - muertes tradeadas)."""
    with Session(get_engine()) as s:
        _authorize_view(s, viewer, steamid)
        zones = queries.zones_by_event_type(s, steamid, map, "death")
        cells = []
        for z in zones:
            untraded = z.count - z.traded_count
            if untraded >= queries.MIN_SAMPLE:
                cells.append(_to_cell(z, untraded))
        return HeatmapResponse(
            steamid=steamid,
            map=map,
            has_radar=maps.has_radar(map),
            grid_size=maps.GRID_CELLS_PER_AXIS,
            cells=cells,
        )


@app.get("/players/{steamid}/heatmaps/utility", response_model=UtilityHeatmapResponse)
def heatmap_utility(
    steamid: str,
    map: str,
    type: str = "flash",
    viewer: str = Depends(get_current_steamid),
) -> UtilityHeatmapResponse:
    """Efectividad de utilidad por zona. type=flash|he|molotov|smoke -- smoke
    solo trae frecuencia (sin score de efectividad, ver plan Fase 3/4).
    El self/team-flash va aparte en `friendly_fire`, no mezclado en el mapa."""
    event_type = _UTILITY_TYPE_TO_EVENT.get(type)
    if event_type is None:
        raise HTTPException(400, f"type inválido: {type!r}")
    with Session(get_engine()) as s:
        _authorize_view(s, viewer, steamid)
        zones = queries.zones_by_event_type(s, steamid, map, event_type)
        cells = [_to_cell(z, z.count) for z in zones if z.count >= queries.MIN_SAMPLE]

        friendly_fire = None
        if type == "flash":
            total, friendly = queries.friendly_fire_summary(s, steamid)
            friendly_fire = FriendlyFireSummary(
                total_flashes=total,
                friendly_flashes=friendly,
                friendly_flash_rate=round(100.0 * friendly / total, 1) if total else 0.0,
            )

        return UtilityHeatmapResponse(
            steamid=steamid,
            map=map,
            has_radar=maps.has_radar(map),
            grid_size=maps.GRID_CELLS_PER_AXIS,
            event_type=event_type,
            cells=cells,
            friendly_fire=friendly_fire,
        )


@app.get("/matches/{match_id}/badges", response_model=BadgesResponse)
def match_badges(
    match_id: str, steamid: str, viewer: str = Depends(get_current_steamid)
) -> BadgesResponse:
    with Session(get_engine()) as s:
        m = s.get(Match, match_id)
        if m is None:
            raise HTTPException(404, "match no encontrado")
        _authorize_view(s, viewer, steamid)
        inputs = queries.badge_inputs(s, match_id, steamid)
        badges = badges_domain.compute_badges(badges_domain.MatchBadgeInputs(**inputs))
        return BadgesResponse(
            badges=[
                BadgeOut(key=b.key, kind=b.kind, icon=b.icon, title=b.title, detail=b.detail)
                for b in badges
            ]
        )


@app.get("/matches/{match_id}/clutches", response_model=ClutchTimelineResponse)
def match_clutches(
    match_id: str, steamid: str, viewer: str = Depends(get_current_steamid)
) -> ClutchTimelineResponse:
    with Session(get_engine()) as s:
        m = s.get(Match, match_id)
        if m is None:
            raise HTTPException(404, "match no encontrado")
        _authorize_view(s, viewer, steamid)
        rows = queries.clutch_timeline(s, match_id, steamid)
        return ClutchTimelineResponse(
            clutches=[
                ClutchEntry(
                    round_num=c.round_num,
                    enemies_at_start=c.enemies_at_start,
                    outcome=c.outcome,
                )
                for c in rows
            ]
        )


@app.get("/players/{steamid}/rivals", response_model=RivalsResponse)
def player_rivals(steamid: str, viewer: str = Depends(get_current_steamid)) -> RivalsResponse:
    with Session(get_engine()) as s:
        _authorize_view(s, viewer, steamid)
        rows = queries.rivals(s, steamid)
        return RivalsResponse(
            rivals=[
                RivalSummary(
                    steamid=r["steamid"],
                    name=r["name"],
                    matches_together=r["matches_together"],
                    matches_opposed=r["matches_opposed"],
                    avg_rating=r["avg_rating"],
                )
                for r in rows
            ]
        )


@app.get("/players/{steamid_a}/compare/{steamid_b}", response_model=CompareResponse)
def player_compare(
    steamid_a: str,
    steamid_b: str,
    viewer: str = Depends(get_current_steamid),
) -> CompareResponse:
    with Session(get_engine()) as s:
        _authorize_view(s, viewer, steamid_a)
        _authorize_view(s, viewer, steamid_b)
        cmp = queries.compare_players(s, steamid_a, steamid_b)
        if cmp is None:
            raise HTTPException(404, "nunca compartieron una partida")
        return CompareResponse(
            steamid_a=cmp["steamid_a"],
            name_a=cmp["name_a"],
            team_num_a=cmp["team_num_a"],
            steamid_b=cmp["steamid_b"],
            name_b=cmp["name_b"],
            team_num_b=cmp["team_num_b"],
            matches_compared=cmp["matches_compared"],
            metrics=[ComparisonMetric(**m) for m in cmp["metrics"]],
            trade_utility=TradeUtilitySummary(
                trade_kills=queries.lifetime_trade_kills(s, steamid_a),
                flash_assists=queries.flash_assist_count(s, steamid_a),
            ),
            winrate_together=(
                WinrateTogetherSummary(**wt)
                if (wt := queries.winrate_conjunto(s, steamid_a, steamid_b)) is not None
                else None
            ),
        )


@app.get("/players/{steamid}/profile", response_model=ProfileResponse)
def player_profile(
    steamid: str,
    viewer: str = Depends(get_current_steamid),
) -> ProfileResponse:
    with Session(get_engine()) as s:
        _authorize_view(s, viewer, steamid)
        user = s.get(User, steamid)
        player = s.get(Player, steamid)

        history = queries.match_history(s, steamid)
        lifetime = profile_domain.lifetime_stats(history)
        pool = profile_domain.map_pool(history, list(maps.MAP_TRANSFORMS.keys()))
        trade_kills = queries.lifetime_trade_kills(s, steamid)
        biggest_clutch = queries.biggest_clutch_won(s, steamid)
        ms = profile_domain.milestones(history, trade_kills, biggest_clutch)

        recent_deaths = queries.recent_deaths_with_timing(s, steamid)
        pattern = coach_domain.early_round_death_pattern(recent_deaths)
        insight = coach_domain.describe_early_round_deaths(pattern)
        coach_insights = [CoachInsight(**insight)] if insight else []

        # Serie completa (no el slice de 20): el sparkline quiere todo.
        rank_hist = profile_domain.rank_history(history)
        snapshot = TacticalSnapshot(
            best_map=profile_domain.best_map(pool),
            dominant_role=roles_domain.dominant_role(**queries.role_inputs(s, steamid)),
        )

        # AccuracyPanel: ventana de últimas 16 partidas (no lifetime, a
        # diferencia de top_weapons), oldest-first para el sparkline.
        hs_pct_series = [h["hs_pct"] for h in reversed(history[:16])]
        accuracy = profile_domain.accuracy_stats(
            queries.recent_hitgroup_counts(s, steamid), hs_pct_series
        )
        top_weapons_list = profile_domain.top_weapons(queries.lifetime_weapon_kills(s, steamid))

        return ProfileResponse(
            steamid=steamid,
            display_name=(user.display_name if user else None) or (player.name if player else None),
            avatar_url=user.avatar_url if user else None,
            lifetime=LifetimeStats(**lifetime),
            match_history=[MatchHistoryEntry(**h) for h in history[:200]],
            map_pool=[MapPoolEntry(**mp) for mp in pool],
            milestones=[MilestoneEntry(**m) for m in ms],
            coach_insights=coach_insights,
            rank_history=[RankPoint(**p) for p in rank_hist],
            tactical_snapshot=snapshot,
            accuracy=AccuracyStats(**accuracy),
            top_weapons=[TopWeaponEntry(**w) for w in top_weapons_list],
            # Rating vivo del GC solo en el perfil propio (es dato consultado
            # para ese usuario, no scouting de terceros).
            current_premier_rating=(
                user.current_premier_rating if user and viewer == steamid else None
            ),
            current_premier_updated_at=(
                user.current_premier_updated_at if user and viewer == steamid else None
            ),
        )


@app.get("/players/{steamid}/weapons-detail", response_model=WeaponsPageResponse)
def player_weapons_detail(
    steamid: str,
    viewer: str = Depends(get_current_steamid),
) -> WeaponsPageResponse:
    """Landing de armas completa (estilo tracker.gg): detalle por arma
    (incluye cuchillo, a diferencia de ProfileResponse.top_weapons) y
    agregado LOADOUTS por tipo de compra. Misma visibilidad que el resto
    del perfil (pertenencia, no ownership)."""
    with Session(get_engine()) as s:
        _authorize_view(s, viewer, steamid)

        rounds_played = queries.lifetime_rounds_played(s, steamid)
        wb_inputs = queries.weapon_breakdown_inputs(s, steamid)
        weapons = profile_domain.weapon_breakdown(
            wb_inputs["kills_by"], wb_inputs["deaths_by"], wb_inputs["damage_by"], rounds_played
        )

        history = queries.match_history(s, steamid)
        lifetime_adr = profile_domain.lifetime_stats(history)["avg_adr"]
        loadout_rows = queries.loadout_breakdown_inputs(s, steamid)
        loadouts = loadouts_domain.aggregate_loadout_stats(loadout_rows, lifetime_adr)

        return WeaponsPageResponse(
            weapons=[WeaponDetailEntry(**w) for w in weapons],
            loadouts=[LoadoutTierStats(**t) for t in loadouts],
        )


@app.get("/matches/{match_id}/economy", response_model=MatchEconomyResponse)
def match_economy(
    match_id: str, viewer: str = Depends(get_current_steamid)
) -> MatchEconomyResponse:
    """Economía por jugador por ronda (equip value post-compra + tipo de
    compra derivado). Vacío en partidas ingeridas antes de round_economy
    (re-ingerir con --force). Misma visibilidad que el resto del match."""
    with Session(get_engine()) as s:
        _authorize_match(s, viewer, match_id)
        rows = (
            s.execute(
                select(RoundEconomy)
                .where(RoundEconomy.match_id == match_id)
                .order_by(RoundEconomy.round_num)
            )
            .scalars()
            .all()
        )
        return MatchEconomyResponse(
            rounds=[
                RoundEconomyOut(
                    round_num=r.round_num,
                    steamid=r.steamid,
                    equip_value=r.equip_value,
                    tipo_compra=economia_domain.clasificar_tipo_compra(r.equip_value),
                )
                for r in rows
            ]
        )


@app.get("/players/{steamid}/profile-tags", response_model=ProfileTagsResponse)
def player_profile_tags(
    steamid: str, viewer: str = Depends(get_current_steamid)
) -> ProfileTagsResponse:
    """Lectura del cache de tags de perfil (ver
    queries.recompute_profile_tags -- se recalcula al ingerir, no acá).
    Mismo modelo de autorización que el resto del perfil: alcanza con
    compartir una partida con el dueño, no hace falta ser el dueño (es un
    perfil de scouting, no un dato privado)."""
    with Session(get_engine()) as s:
        _authorize_view(s, viewer, steamid)
        tags = queries.profile_tags_for(s, steamid)
        return ProfileTagsResponse(
            tags=[
                ProfileTagOut(
                    tag_id=t.tag_id,
                    detalle=t.detalle,
                    calculado_en=t.calculado_en,
                    ventana_partidas=t.ventana_partidas,
                )
                for t in tags
            ]
        )


def _find_demo(demo_file: str) -> Path | None:
    """Busca el .dem por nombre bajo demos_dir (los de autofetch viven en
    un subdirectorio). None = ya no está en disco (retención/limpieza) y
    el clip no se puede generar."""
    for p in settings.demos_dir.rglob(demo_file):
        return p
    return None


def _render_clip_job(job_id: int) -> None:
    """BackgroundTask: renderiza el clip del job y actualiza su estado.
    Sesión propia (corre después de que el request cerró la suya)."""
    from cs2tracker.infra import clips as clips_infra

    with Session(get_engine()) as s:
        job = s.get(ClipJob, job_id)
        if job is None:
            return
        m = s.get(Match, job.match_id)
        player = s.get(Player, job.steamid)
        dem = _find_demo(m.demo_file) if m else None
        if m is None or m.map is None or dem is None:
            job.status, job.error = "error", "demo no disponible en disco"
            s.commit()
            return
        job.status = "rendering"
        s.commit()
        settings.clips_dir.mkdir(parents=True, exist_ok=True)
        out = settings.clips_dir / f"clip_{job.id}_{job.match_id}_r{job.round_num}.mp4"
        try:
            clips_infra.render_clip(
                dem_path=dem,
                map_name=m.map,
                round_num=job.round_num,
                steamid=job.steamid,
                label=job.label,
                player_name=(player.name if player else None) or job.steamid,
                out_path=out,
            )
        except Exception as exc:  # noqa: BLE001 -- el error se persiste, no se pierde
            job.status, job.error = "error", str(exc)
        else:
            job.status, job.file_path = "done", str(out)
        s.commit()


@app.get("/players/{steamid}/highlights", response_model=HighlightsResponse)
def player_highlights(
    steamid: str, viewer: str = Depends(get_current_steamid)
) -> HighlightsResponse:
    """Momentos clipeables del usuario (privado, como monthly: los clips
    son SU contenido para SUS redes, no scouting)."""
    _authorize_self(viewer, steamid)
    with Session(get_engine()) as s:
        moments = queries.highlight_moments(s, steamid)
        return HighlightsResponse(
            moments=[
                HighlightMomentOut(
                    match_id=m["match_id"],
                    round_num=m["round_num"],
                    score=m["score"],
                    label=m["label"],
                    map=m["map"],
                    demo_available=bool(m["demo_file"] and _find_demo(m["demo_file"])),
                )
                for m in moments
            ]
        )


@app.post("/players/{steamid}/clips", response_model=ClipJobOut)
def create_clip(
    steamid: str,
    body: ClipCreateRequest,
    background: BackgroundTasks,
    viewer: str = Depends(get_current_steamid),
) -> ClipJobOut:
    _authorize_self(viewer, steamid)
    with Session(get_engine()) as s:
        # Solo momentos detectados: evita renders arbitrarios de cualquier
        # ronda (costo de CPU) y garantiza que el label sea real.
        moment = next(
            (
                m
                for m in queries.highlight_moments(s, steamid)
                if m["match_id"] == body.match_id and m["round_num"] == body.round_num
            ),
            None,
        )
        if moment is None:
            raise HTTPException(404, "ese momento no está entre tus highlights")
        job = ClipJob(
            steamid=steamid,
            match_id=body.match_id,
            round_num=body.round_num,
            label=moment["label"],
            status="pending",
            created_at=datetime.now(UTC).isoformat(),
        )
        s.add(job)
        s.commit()
        s.refresh(job)
        background.add_task(_render_clip_job, job.id)
        return ClipJobOut(
            id=job.id,
            match_id=job.match_id,
            round_num=job.round_num,
            label=job.label,
            status=job.status,
            error=None,
            created_at=job.created_at,
        )


@app.get("/players/{steamid}/clips", response_model=ClipsResponse)
def list_clips(steamid: str, viewer: str = Depends(get_current_steamid)) -> ClipsResponse:
    _authorize_self(viewer, steamid)
    with Session(get_engine()) as s:
        jobs = (
            s.execute(select(ClipJob).where(ClipJob.steamid == steamid).order_by(ClipJob.id.desc()))
            .scalars()
            .all()
        )
        return ClipsResponse(
            clips=[
                ClipJobOut(
                    id=j.id,
                    match_id=j.match_id,
                    round_num=j.round_num,
                    label=j.label,
                    status=j.status,
                    error=j.error,
                    created_at=j.created_at,
                )
                for j in jobs
            ]
        )


@app.get("/clips/{job_id}/download")
def download_clip(job_id: int, viewer: str = Depends(get_current_steamid)) -> FileResponse:
    with Session(get_engine()) as s:
        job = s.get(ClipJob, job_id)
        if job is None or job.steamid != viewer:
            # 404 también para clips ajenos: no filtrar su existencia.
            raise HTTPException(404, "clip no encontrado")
        if job.status != "done" or not job.file_path:
            raise HTTPException(409, f"clip no listo (estado: {job.status})")
        return FileResponse(
            job.file_path,
            media_type="video/mp4",
            filename=f"cstats_{job.label.replace(' ', '_')}_r{job.round_num + 1}.mp4",
        )


@app.get("/players/{steamid}/monthly", response_model=MonthlySummaryResponse)
def player_monthly(
    steamid: str, viewer: str = Depends(get_current_steamid)
) -> MonthlySummaryResponse:
    _authorize_self(viewer, steamid)
    with Session(get_engine()) as s:
        window = monthly_domain.month_bounds(datetime.now(UTC), settings.app_tz)
        start = window.start_utc.isoformat()
        end = window.end_utc.isoformat()
        rows = queries.monthly_window_rows(s, steamid, start, end)
        clutches = queries.monthly_clutches_won(s, steamid, start, end)
        summary = monthly_domain.compute_monthly_summary(rows, clutches, window)

        mvp = summary.detail.mvp
        return MonthlySummaryResponse(
            window=MonthlyWindow(
                from_date=summary.window.from_date,
                to=summary.window.to_date,
                tz=summary.window.tz,
            ),
            totals=MonthlyTotals(**vars(summary.totals)),
            headline=MonthlyHeadline(**vars(summary.headline)),
            detail=MonthlyDetail(
                adr_avg=summary.detail.adr_avg,
                kast_pct=summary.detail.kast_pct,
                clutches_won=summary.detail.clutches_won,
                entry_kills=summary.detail.entry_kills,
                matches_per_day=[
                    MatchesPerDayEntry(day=d.day, count=d.count)
                    for d in summary.detail.matches_per_day
                ],
                top_maps=[
                    TopMapEntry(map_id=t.map_id, wins=t.wins, losses=t.losses)
                    for t in summary.detail.top_maps
                ],
                mvp=MonthlyMvpOut(**vars(mvp)) if mvp else None,
            ),
        )


def run() -> None:
    import uvicorn

    uvicorn.run(app, host=settings.api_host, port=settings.api_port)


if __name__ == "__main__":
    run()
