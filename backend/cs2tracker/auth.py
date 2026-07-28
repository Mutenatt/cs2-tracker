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
from html.parser import HTMLParser
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, Request
from itsdangerous import BadSignature, URLSafeTimedSerializer

from cs2tracker.config import settings

STEAM_OPENID_URL = "https://steamcommunity.com/openid/login"
_CLAIMED_ID_RE = re.compile(r"^https://steamcommunity\.com/openid/id/(\d+)$")

COOKIE_NAME = "cs2_session"
SESSION_MAX_AGE = 30 * 24 * 3600  # 30 días

# Algunos CDNs sirven contenido reducido a clientes sin User-Agent de
# navegador; sin esto, GetPlayerSummaries igual funciona (es la Web API
# oficial) pero el scraping del perfil público puede devolver menos markup.
# El resto de los headers imita un navegador real -- steamcommunity.com
# devuelve 429 más seguido a requests que solo traen un User-Agent (sin
# Accept/Accept-Language), aunque el rate-limit de fondo sigue siendo de
# Steam y no algo que se pueda evitar del todo.
_BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
}

# Fallback: URL directa a un .webm/.mp4 de un CDN de Steam en cualquier parte
# del HTML. Más tolerante que el parser estructurado (_ProfileBackgroundParser)
# ante cambios de markup -- Steam no documenta esto y varía.
_VIDEO_URL_RE = re.compile(
    r"https://[a-z0-9.-]*(?:steamstatic|akamaihd|fastly)[a-z0-9./_-]*\.(?:webm|mp4)",
    re.IGNORECASE,
)

_BACKGROUND_URL_RE = re.compile(
    r"url\(\s*['\"]?((?:https?:)?//[^)'\"\s]+)['\"]?\s*\)", re.IGNORECASE
)


def _normalise_steam_url(url: str) -> str | None:
    """Acepta URLs absolutas y protocol-relative que devuelve Steam."""
    url = url.replace(r"\u002F", "/").replace(r"\/", "/").strip()
    if url.startswith("//"):
        return f"https:{url}"
    if url.startswith(("https://", "http://")):
        return url
    return None


# Si no hay CS2_SESSION_SECRET en el entorno, se genera uno al arrancar el
# proceso: nunca hay un secreto débil hardcodeado, a costa de invalidar
# sesiones existentes en cada restart (aceptable para este prototipo).
_session_secret = settings.session_secret or secrets.token_hex(32)
_serializer = URLSafeTimedSerializer(_session_secret, salt="cs2tracker-session")


class _ProfileBackgroundParser(HTMLParser):
    """Backgrounds de perfil de Steam vienen en dos formas:

    1. Estático: un <div style="background-image: url(...)"> (los de siempre,
       comprados en la Points Shop o de items del inventario).
    2. Animado: un <video><source src="...webm"></video> (Points Shop
       "Animated Backgrounds"). No hay background-image en ese caso -- el
       fondo ES el video.

    Priorizamos el estático si aparece (más simple/liviano), y si no,
    devolvemos el video (preferimos .webm sobre .mp4 por tamaño/calidad).
    El caller (frontend) distingue cuál es por la extensión del URL.
    """

    def __init__(self) -> None:
        super().__init__()
        self.background_url: str | None = None
        self._video_webm: str | None = None
        self._video_mp4: str | None = None
        self._in_video = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.background_url is not None:
            return
        attr_map = {k: v for k, v in attrs if k is not None}

        if tag == "video":
            self._in_video = True
            return
        if tag == "source" and self._in_video:
            src = attr_map.get("src")
            type_ = attr_map.get("type", "")
            # Algunos <source> no traen type -- si el src ya termina en
            # .webm/.mp4, alcanza con eso.
            is_webm = "webm" in type_ or (src is not None and src.lower().endswith(".webm"))
            is_mp4 = "mp4" in type_ or (src is not None and src.lower().endswith(".mp4"))
            if src and is_webm and self._video_webm is None:
                self._video_webm = src
            elif src and is_mp4 and self._video_mp4 is None:
                self._video_mp4 = src
            return

        style = attr_map.get("style", "")
        # Steam ha usado tanto background-image como el shorthand background,
        # y en algunos perfiles sirve una URL que empieza con //.
        if tag != "div" or "background" not in style.lower():
            return
        match = _BACKGROUND_URL_RE.search(style)
        if match:
            candidate = _normalise_steam_url(match.group(1))
            if candidate:
                self.background_url = candidate

    def handle_endtag(self, tag: str) -> None:
        if tag == "video":
            self._in_video = False

    def result(self) -> str | None:
        return self.background_url or self._video_webm or self._video_mp4


def parse_profile_background_url(html: str) -> str | None:
    parser = _ProfileBackgroundParser()
    parser.feed(html)
    found = parser.result()
    if found:
        return found
    # Steam también puede emitir el estilo en un <style> en vez de inline.
    # Filtramos a sus CDNs para no confundirlo con iconos u otras imágenes de
    # la página de perfil.
    for match in _BACKGROUND_URL_RE.finditer(html):
        candidate = _normalise_steam_url(match.group(1))
        cdn_hosts = ("steamcommunity", "steamstatic", "akamaihd", "fastly")
        if candidate and any(host in candidate for host in cdn_hosts):
            return candidate
    # Fallback tolerante a markup no previsto: primera URL de video de Steam
    # que aparezca en todo el documento.
    m = _VIDEO_URL_RE.search(html)
    return m.group(0) if m else None


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


async def fetch_profile(steamid: str) -> tuple[str | None, str | None, str | None]:
    """(display_name, avatar_url, background_url) vía Steam Web API y perfil público."""
    profiles = await fetch_profiles([steamid])
    return profiles.get(steamid, (None, None, None))


ProfileMap = dict[str, tuple[str | None, str | None, str | None]]


async def fetch_profiles(steamids: list[str]) -> ProfileMap:
    """steamid -> (personaname, avatar_url, background_url)."""
    if not settings.steam_api_key or not steamids:
        print(
            "[cs2tracker.auth] fetch_profiles: sin CS2_STEAM_API_KEY o steamids "
            "vacío, no se busca nada"
        )
        return {}
    try:
        async with httpx.AsyncClient(timeout=10.0, headers=_BROWSER_HEADERS) as client:
            resp = await client.get(
                "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/",
                params={"key": settings.steam_api_key, "steamids": ",".join(steamids)},
            )
        players = resp.json().get("response", {}).get("players", [])
        result: ProfileMap = {}
        for p in players:
            steamid = str(p["steamid"])
            background_url = None
            try:
                async with httpx.AsyncClient(timeout=10.0, headers=_BROWSER_HEADERS) as client:
                    public_resp = await client.get(f"https://steamcommunity.com/profiles/{steamid}")
                if public_resp.status_code == 200:
                    background_url = parse_profile_background_url(public_resp.text)
                    print(
                        f"[cs2tracker.auth] steam background {steamid}: "
                        f"status={public_resp.status_code} len={len(public_resp.text)} "
                        f"-> {background_url or '(ninguno encontrado)'}"
                    )
                else:
                    print(
                        f"[cs2tracker.auth] steam background {steamid}: "
                        f"status={public_resp.status_code} (perfil no accesible)"
                    )
            except Exception as exc:
                print(
                    f"[cs2tracker.auth] steam background {steamid}: excepción al parsear -> {exc!r}"
                )
                background_url = None
            result[steamid] = (p.get("personaname"), p.get("avatarfull"), background_url)
        return result
    except Exception as exc:
        print(
            f"[cs2tracker.auth] fetch_profiles: excepción al llamar a GetPlayerSummaries -> {exc!r}"
        )
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
