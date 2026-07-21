"""
Cadena de sharecodes vía Steam Web API (GetNextMatchSharingCode).

Parte A del auto-fetch (modelo Leetify): con el Game Authentication Code
que el propio usuario generó en Steam y su último sharecode conocido, la
API devuelve el siguiente de la cadena. Nunca se manejan credenciales de
Steam del usuario. La Parte B (sharecode -> URL del .dem vía Game
Coordinator) vive en el gc-sidecar; ver gc_client.py.
"""

from __future__ import annotations

import httpx

NEXT_CODE_URL = "https://api.steampowered.com/ICSGOPlayers_730/GetNextMatchSharingCode/v1"


class SharecodeChainError(Exception):
    """Fallo genérico hablando con GetNextMatchSharingCode."""


class AuthCodeInvalid(SharecodeChainError):
    """HTTP 403: el usuario revocó/regeneró su auth code; hay que re-vincular."""


class RateLimited(SharecodeChainError):
    """HTTP 429: bajar el ritmo y reintentar en el próximo ciclo."""


def get_next_sharecode(
    steamid: str,
    auth_code: str,
    known_code: str,
    *,
    api_key: str,
    client: httpx.Client | None = None,
    timeout: float = 10.0,
) -> str | None:
    """Un paso de la cadena: el sharecode siguiente a known_code, o None si
    no hay partida más nueva (nextcode "n/a" o HTTP 202).

    `client` inyectable para tests (httpx.MockTransport).
    """
    params = {
        "key": api_key,
        "steamid": steamid,
        "steamidkey": auth_code,
        "knowncode": known_code,
    }
    if client is not None:
        resp = client.get(NEXT_CODE_URL, params=params)
    else:
        with httpx.Client(timeout=timeout) as c:
            resp = c.get(NEXT_CODE_URL, params=params)

    if resp.status_code == 202:
        return None
    if resp.status_code == 403:
        raise AuthCodeInvalid("Steam rechazó el auth code (403): revocado o inválido")
    if resp.status_code == 429:
        raise RateLimited("rate limit de la Steam Web API (429)")
    if resp.status_code != 200:
        raise SharecodeChainError(f"HTTP {resp.status_code} de GetNextMatchSharingCode")

    next_code = resp.json().get("result", {}).get("nextcode")
    if not next_code or next_code == "n/a":
        return None
    return next_code
