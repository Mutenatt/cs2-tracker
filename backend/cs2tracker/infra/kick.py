"""Streams de CS en vivo vía la API pública oficial de Kick.

Mismo esquema que twitch.py: app access token por client credentials
(id.kick.com, form-urlencoded; las credenciales salen de una app creada en
kick.com → Settings → Developer, requiere 2FA) y luego GET a
/public/v2/livestreams filtrando por categoría e idioma (es + pt). A
diferencia de Helix hay dos vueltas extra: el id de la categoría
Counter-Strike se resuelve una vez contra /public/v2/categories (y se cachea
a nivel módulo), y v2 no documenta orden por viewers, así que se ordena acá.

Best-effort: cualquier falla devuelve [].
"""

from __future__ import annotations

import time

import httpx

from cs2tracker.config import settings
from cs2tracker.infra.streams_common import LiveStream

_TOKEN_URL = "https://id.kick.com/oauth/token"
_CATEGORIES_URL = "https://api.kick.com/public/v2/categories"
_LIVESTREAMS_URL = "https://api.kick.com/public/v2/livestreams"

# App access token cacheado: (token, monotonic de expiración con margen).
_token: tuple[str, float] | None = None
# Id de la categoría Counter-Strike, resuelto una sola vez.
_category_id: int | None = None


def is_configured() -> bool:
    return bool(settings.kick_client_id and settings.kick_client_secret)


async def _get_token(client: httpx.AsyncClient) -> str:
    global _token
    if _token is not None and time.monotonic() < _token[1]:
        return _token[0]
    resp = await client.post(
        _TOKEN_URL,
        data={
            "client_id": settings.kick_client_id,
            "client_secret": settings.kick_client_secret,
            "grant_type": "client_credentials",
        },
    )
    resp.raise_for_status()
    body = resp.json()
    _token = (body["access_token"], time.monotonic() + int(body["expires_in"]) - 60)
    return _token[0]


def pick_cs_category(categories: list[dict]) -> int | None:
    """Elige la categoría de Counter-Strike de la respuesta de /categories.
    Pura (testeable). Prefiere el nombre exacto "Counter-Strike"; si no,
    cualquiera que empiece así (cubre un eventual "Counter-Strike 2")."""
    starts_with = None
    for c in categories:
        name = c.get("name", "")
        if name == "Counter-Strike":
            return c.get("id")
        if name.startswith("Counter-Strike") and starts_with is None:
            starts_with = c.get("id")
    return starts_with


async def _get_category_id(client: httpx.AsyncClient, token: str) -> int | None:
    global _category_id
    if _category_id is not None:
        return _category_id
    resp = await client.get(
        _CATEGORIES_URL,
        params={"name": "Counter-Strike"},
        headers={"Authorization": f"Bearer {token}"},
    )
    resp.raise_for_status()
    _category_id = pick_cs_category(resp.json().get("data", []))
    return _category_id


async def _get_streams(client: httpx.AsyncClient, token: str, category_id: int) -> httpx.Response:
    return await client.get(
        _LIVESTREAMS_URL,
        # Params repetidos (language_code dos veces) => lista de tuplas.
        params=[
            ("category_id", str(category_id)),
            ("language_code", "es"),
            ("language_code", "pt"),
            ("limit", "50"),
        ],
        headers={"Authorization": f"Bearer {token}"},
    )


async def fetch_latam_cs_streams(limit: int = 8) -> list[LiveStream]:
    """Streams de CS en es/pt ordenados por viewers. Best-effort: [] ante
    cualquier falla; reintenta una vez si el token cacheado fue revocado."""
    global _token
    if not is_configured():
        return []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            token = await _get_token(client)
            category_id = await _get_category_id(client, token)
            if category_id is None:
                return []
            resp = await _get_streams(client, token, category_id)
            if resp.status_code == 401:
                _token = None
                token = await _get_token(client)
                resp = await _get_streams(client, token, category_id)
            resp.raise_for_status()
            raw = resp.json().get("data", [])
    except Exception:
        return []

    streams = []
    for s in raw:
        slug = (s.get("channel") or {}).get("slug", "")
        user = s.get("broadcaster_user") or {}
        streams.append(
            LiveStream(
                platform="kick",
                channel=user.get("username", "") or slug,
                login=slug,
                title=s.get("title", ""),
                viewers=int(s.get("viewer_count", 0)),
                language=(s.get("language_code") or "").split("-")[0],
                thumbnail_url=s.get("thumbnail", "") or "",
            )
        )
    streams.sort(key=lambda s: s.viewers, reverse=True)
    return streams[:limit]
