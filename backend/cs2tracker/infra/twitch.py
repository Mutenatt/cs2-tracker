"""Streams de CS en vivo vía Twitch Helix (API oficial).

Flujo client-credentials: POST id.twitch.tv/oauth2/token con el client_id y
secret de la app (dev.twitch.tv/console) da un app access token que dura
días; se cachea a nivel módulo y se renueva solo. "LATAM" se aproxima por
idioma del stream (es + pt) — Helix no expone país del streamer.

Best-effort como steam_news: cualquier falla devuelve [].
"""

from __future__ import annotations

import time

import httpx

from cs2tracker.config import settings
from cs2tracker.infra.streams_common import LiveStream

# Categoría "Counter-Strike" en Twitch (la de CS:GO, renombrada para CS2).
CS_GAME_ID = "32399"
_TOKEN_URL = "https://id.twitch.tv/oauth2/token"
_STREAMS_URL = "https://api.twitch.tv/helix/streams"

# App access token cacheado: (token, monotonic de expiración con margen).
_token: tuple[str, float] | None = None


def is_configured() -> bool:
    return bool(settings.twitch_client_id and settings.twitch_client_secret)


async def _get_token(client: httpx.AsyncClient) -> str:
    global _token
    if _token is not None and time.monotonic() < _token[1]:
        return _token[0]
    resp = await client.post(
        _TOKEN_URL,
        data={
            "client_id": settings.twitch_client_id,
            "client_secret": settings.twitch_client_secret,
            "grant_type": "client_credentials",
        },
    )
    resp.raise_for_status()
    body = resp.json()
    # Margen de 60 s para no usar un token al borde de expirar.
    _token = (body["access_token"], time.monotonic() + body["expires_in"] - 60)
    return _token[0]


async def _get_streams(client: httpx.AsyncClient, token: str, limit: int) -> httpx.Response:
    return await client.get(
        _STREAMS_URL,
        # Params repetidos (language dos veces) => lista de tuplas.
        params=[
            ("game_id", CS_GAME_ID),
            ("language", "es"),
            ("language", "pt"),
            ("first", str(limit)),
        ],
        headers={
            "Client-Id": settings.twitch_client_id or "",
            "Authorization": f"Bearer {token}",
        },
    )


async def fetch_latam_cs_streams(limit: int = 8) -> list[LiveStream]:
    """Streams de CS en es/pt ordenados por viewers (orden que ya da Helix).
    Best-effort: [] ante cualquier falla; reintenta una vez si el token
    cacheado fue revocado (401)."""
    global _token
    if not is_configured():
        return []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            token = await _get_token(client)
            resp = await _get_streams(client, token, limit)
            if resp.status_code == 401:
                _token = None
                token = await _get_token(client)
                resp = await _get_streams(client, token, limit)
            resp.raise_for_status()
            raw = resp.json().get("data", [])
    except Exception:
        return []

    streams = []
    for s in raw:
        thumb = s.get("thumbnail_url", "")
        streams.append(
            LiveStream(
                platform="twitch",
                channel=s.get("user_name", ""),
                login=s.get("user_login", ""),
                title=s.get("title", ""),
                viewers=int(s.get("viewer_count", 0)),
                language=s.get("language", ""),
                thumbnail_url=thumb.replace("{width}", "440").replace("{height}", "248"),
            )
        )
    return streams
