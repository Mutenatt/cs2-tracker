"""
Cliente del gc-sidecar (Parte B del auto-fetch): sharecode -> URL del .dem.

El sidecar (gc-sidecar/, Node) mantiene la sesión con el Game Coordinator
de CS2 vía una cuenta bot del servicio; acá solo se le habla por HTTP
local. La distinción de errores importa para la cadena de sharecodes:
SidecarUnavailable = NO avanzar (reintentar); DemoExpired = avanzar (skip).
"""

from __future__ import annotations

import httpx


class SidecarUnavailable(Exception):
    """El sidecar no responde o no tiene sesión GC: NO avanzar la cadena."""


class DemoExpired(Exception):
    """El GC no tiene URL para esta partida (~30 días): skip deliberado."""


# Cache en memoria del steamid del bot: no cambia en la vida del proceso.
# Solo se cachea un valor no-nulo (si el sidecar todavía no logueó a Steam,
# /health devuelve botSteamId=None, y eso no debe quedar pegado para siempre).
_bot_steamid_cache: str | None = None


def get_bot_steamid(*, base_url: str, client: httpx.Client | None = None) -> str | None:
    """steamid64 de la cuenta bot del gc-sidecar (para el link "agregar de
    amigo" del onboarding). Lo expone /health; nunca hace falta duplicarlo
    en la config del backend."""
    global _bot_steamid_cache
    if _bot_steamid_cache is not None:
        return _bot_steamid_cache
    try:
        if client is not None:
            resp = client.get(f"{base_url}/health")
        else:
            with httpx.Client(timeout=5.0) as c:
                resp = c.get(f"{base_url}/health")
    except httpx.HTTPError:
        return None
    steamid = resp.json().get("botSteamId")
    if steamid:
        _bot_steamid_cache = steamid
    return steamid


def notify_match_ready(
    steamid: str,
    match_id: str,
    *,
    base_url: str,
    frontend_url: str,
    client: httpx.Client | None = None,
) -> None:
    """Avisa por chat de Steam que una partida terminó de ingerirse.
    Best-effort puro: cualquier fallo (sidecar caído, usuario no amigo del
    bot todavía) se ignora, la partida ya quedó disponible en el sitio."""
    message = f"Tu partida ya está lista: {frontend_url}/matches/{match_id}"
    try:
        if client is not None:
            client.post(f"{base_url}/notify", json={"steamid": steamid, "message": message})
        else:
            with httpx.Client(timeout=10.0) as c:
                c.post(f"{base_url}/notify", json={"steamid": steamid, "message": message})
    except httpx.HTTPError:
        pass


def sidecar_healthy(*, base_url: str, client: httpx.Client | None = None) -> bool:
    try:
        if client is not None:
            resp = client.get(f"{base_url}/health")
        else:
            with httpx.Client(timeout=5.0) as c:
                resp = c.get(f"{base_url}/health")
    except httpx.HTTPError:
        return False
    return resp.status_code == 200


def resolve_demo(
    sharecode: str,
    *,
    base_url: str,
    client: httpx.Client | None = None,
    timeout: float = 45.0,
) -> tuple[str, int | None]:
    """(URL del replay .dem.bz2, matchtime unix o None) para un sharecode.
    `client` inyectable para tests (httpx.MockTransport)."""
    try:
        if client is not None:
            resp = client.post(f"{base_url}/resolve", json={"sharecode": sharecode})
        else:
            with httpx.Client(timeout=timeout) as c:
                resp = c.post(f"{base_url}/resolve", json={"sharecode": sharecode})
    except httpx.HTTPError as e:
        raise SidecarUnavailable(str(e)) from e

    if resp.status_code == 404:
        raise DemoExpired(sharecode)
    if resp.status_code != 200:
        raise SidecarUnavailable(f"HTTP {resp.status_code} del gc-sidecar")
    body = resp.json()
    url = body.get("demoUrl")
    if not url:
        raise SidecarUnavailable("respuesta del sidecar sin demoUrl")
    match_time = body.get("matchTime")
    return url, (int(match_time) if match_time else None)


def fetch_premier_profile(
    steamid: str,
    *,
    base_url: str,
    client: httpx.Client | None = None,
    timeout: float = 40.0,
) -> dict | None:
    """CS Rating Premier vigente del jugador vía el GC (requestPlayersProfile
    en el sidecar). None si el GC no lo devolvió (usuario no amigo de la bot,
    offline, o sin Premier) -- caso esperado, best-effort: nunca rompe la
    ingesta. Devuelve {'rating', 'rank_change', 'wins'} si vino."""
    try:
        if client is not None:
            resp = client.post(f"{base_url}/profile", json={"steamid": steamid})
        else:
            with httpx.Client(timeout=timeout) as c:
                resp = c.post(f"{base_url}/profile", json={"steamid": steamid})
    except httpx.HTTPError:
        return None
    if resp.status_code != 200:
        return None
    body = resp.json()
    rating = body.get("rating")
    if not rating:
        return None
    return {
        "rating": int(rating),
        "rank_change": body.get("rankChange"),
        "wins": body.get("wins"),
    }
