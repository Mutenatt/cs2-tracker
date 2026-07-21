"""Escena pro para el Home: ranking mundial de equipos + streams LATAM.

Ambos endpoints son best-effort sobre fuentes externas y SIEMPRE devuelven
200 — la degradación se expresa en el body (source="valve"/"unavailable",
configured=False) para que el Home nunca se rompa por un tercero caído.
"""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends

from cs2tracker.api.schemas import (
    RankedTeamOut,
    StreamOut,
    StreamsResponse,
    TeamRankingResponse,
)
from cs2tracker.auth import get_current_steamid
from cs2tracker.config import settings
from cs2tracker.infra import kick, twitch
from cs2tracker.infra.hltv_ranking import RankedTeam, fetch_hltv_top10
from cs2tracker.infra.streams_common import LiveStream
from cs2tracker.infra.ttl_cache import cache
from cs2tracker.infra.valve_ranking import fetch_valve_top10

router = APIRouter(prefix="/scene", tags=["scene"])

_RANKING_KEY = "scene:ranking"
_STREAMS_KEY = "scene:streams"

# Anti-stampede: dos requests simultáneas con cache frío no deben disparar
# dos scrapes contra Cloudflare — la segunda espera y encuentra el cache.
_ranking_lock = asyncio.Lock()
_streams_lock = asyncio.Lock()


def _to_out(teams: list[RankedTeam]) -> list[RankedTeamOut]:
    return [
        RankedTeamOut(
            position=t.position,
            name=t.name,
            points=t.points,
            change=t.change,
            logo_url=t.logo_url,
        )
        for t in teams
    ]


@router.get("/ranking", response_model=TeamRankingResponse)
async def team_ranking(_viewer: str = Depends(get_current_steamid)) -> TeamRankingResponse:
    cached = cache.get(_RANKING_KEY)
    if cached is not None:
        return cached

    async with _ranking_lock:
        cached = cache.get(_RANKING_KEY)
        if cached is not None:
            return cached

        teams = await fetch_hltv_top10()
        if teams:
            resp = TeamRankingResponse(source="hltv", teams=_to_out(teams))
            cache.set(_RANKING_KEY, resp, settings.ranking_cache_ttl)
            return resp

        teams = await fetch_valve_top10()
        if teams:
            resp = TeamRankingResponse(source="valve", teams=_to_out(teams))
            cache.set(_RANKING_KEY, resp, settings.ranking_cache_ttl)
            return resp

        # Ninguna fuente respondió: cachear corto para reintentar pronto.
        resp = TeamRankingResponse(source="unavailable", teams=[])
        cache.set(_RANKING_KEY, resp, settings.ranking_error_ttl)
        return resp


def _stream_url(s: LiveStream) -> str:
    if s.platform == "kick":
        return f"https://kick.com/{s.login}"
    return f"https://www.twitch.tv/{s.login}"


@router.get("/streams", response_model=StreamsResponse)
async def latam_streams(_viewer: str = Depends(get_current_steamid)) -> StreamsResponse:
    if not (twitch.is_configured() or kick.is_configured()):
        return StreamsResponse(configured=False, streams=[])

    cached = cache.get(_STREAMS_KEY)
    if cached is not None:
        return cached

    async with _streams_lock:
        cached = cache.get(_STREAMS_KEY)
        if cached is not None:
            return cached

        # Cada fetch ya es best-effort ([] si su plataforma no está
        # configurada o falla) — la mezcla nunca rompe por un lado caído.
        twitch_streams, kick_streams = await asyncio.gather(
            twitch.fetch_latam_cs_streams(limit=8),
            kick.fetch_latam_cs_streams(limit=8),
        )
        merged = sorted(twitch_streams + kick_streams, key=lambda s: s.viewers, reverse=True)[:8]
        resp = StreamsResponse(
            configured=True,
            streams=[
                StreamOut(
                    platform=s.platform,
                    channel=s.channel,
                    channel_slug=s.login,
                    url=_stream_url(s),
                    title=s.title,
                    viewers=s.viewers,
                    language=s.language,
                    thumbnail_url=s.thumbnail_url,
                )
                for s in merged
            ],
        )
        cache.set(_STREAMS_KEY, resp, settings.streams_cache_ttl)
        return resp
