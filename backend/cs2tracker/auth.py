"""
Login con Steam (OpenID 2.0) + sesión propia vía cookie firmada.

No usa contraseñas ni credenciales de Steam de terceros -- es el flujo oficial
de Steam: el usuario loguea EN steamcommunity.com, Steam nos redirige de vuelta
con una respuesta firmada que verificamos server-to-server. steamid64 pasa a
ser la identidad del usuario (users.steamid).

La cookie de sesión es un token firmado (itsdangerous), no un JWT: no hace
falta interoperar con otros sistemas todavía, y evita la superficie extra de
JWT (algoritmos, claims) para lo que por ahora es solo "quién sos".
"""

from __future__ import annotations

import re
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, Request
from itsdangerous import BadSignature, URLSafeTimedSerializer

from cs2tracker.config import settings

STEAM_OPENID_URL = "https://steamcommunity.com/openid/login"
_CLAIMED_ID_RE = re.compile(r"^https://steamcommunity\.com/openid/id/(\d+)$")

COOKIE_NAME = "cs2_session"
SESSION_MAX_AGE = 30 * 24 * 3600  # 30 días

# Si no hay CS2_SESSION_SECRET en el entorno, se genera uno al arrancar el
# proceso: nunca hay un secreto débil hardcodeado, a costa de invalidar
# sesiones existentes en cada restart (aceptable para este prototipo).
_session_secret = settings.session_secret or secrets.token_hex(32)
_serializer = URLSafeTimedSerializer(_session_secret, salt="cs2tracker-session")


def build_login_url() -> str:
    """URL a la que redirigir al usuario para iniciar el login con Steam."""
    return_to = f"{settings.api_public_url}/auth/callback"
    params = {
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.mode": "checkid_setup",
        "openid.return_to": return_to,
        "openid.realm": settings.api_public_url,
        "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
        "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
    }
    return f"{STEAM_OPENID_URL}?{urlencode(params)}"


async def verify_callback(params: dict[str, str]) -> str | None:
    """Verifica la respuesta de Steam (server-to-server) y devuelve el
    steamid64 si es válida, None si no."""
    claimed_id = params.get("openid.claimed_id", "")
    m = _CLAIMED_ID_RE.match(claimed_id)
    if not m:
        return None

    check_params = dict(params)
    check_params["openid.mode"] = "check_authentication"
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(STEAM_OPENID_URL, data=check_params)
    if resp.status_code != 200 or "is_valid:true" not in resp.text:
        return None
    return m.group(1)


async def fetch_profile(steamid: str) -> tuple[str | None, str | None]:
    """(display_name, avatar_url) vía Steam Web API. Best-effort: sin
    CS2_STEAM_API_KEY configurada, o si falla la request, devuelve (None, None)
    -- el login sigue funcionando igual, solo sin esos datos."""
    profiles = await fetch_profiles([steamid])
    return profiles.get(steamid, (None, None))


async def fetch_profiles(steamids: list[str]) -> dict[str, tuple[str | None, str | None]]:
    """steamid -> (personaname, avatar_url) en una sola request a
    GetPlayerSummaries (acepta hasta 100 ids). Mismo best-effort que
    fetch_profile: sin API key o ante cualquier fallo devuelve {}."""
    if not settings.steam_api_key or not steamids:
        return {}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/",
                params={"key": settings.steam_api_key, "steamids": ",".join(steamids)},
            )
        players = resp.json().get("response", {}).get("players", [])
        return {p["steamid"]: (p.get("personaname"), p.get("avatarfull")) for p in players}
    except Exception:
        return {}


def create_session_cookie(steamid: str) -> str:
    return _serializer.dumps({"steamid": steamid})


def read_session_cookie(value: str | None) -> str | None:
    if not value:
        return None
    try:
        data = _serializer.loads(value, max_age=SESSION_MAX_AGE)
    except BadSignature:
        return None
    return data.get("steamid")


def get_current_steamid(request: Request) -> str:
    """Dependency de FastAPI: 401 si no hay sesión válida."""
    steamid = read_session_cookie(request.cookies.get(COOKIE_NAME))
    if steamid is None:
        raise HTTPException(401, "no autenticado")
    return steamid


def get_current_steamid_optional(request: Request) -> str | None:
    return read_session_cookie(request.cookies.get(COOKIE_NAME))
