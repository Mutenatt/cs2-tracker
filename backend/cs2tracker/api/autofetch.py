"""
Vinculación del auto-fetch (modelo Leetify).

El usuario registra su Game Authentication Code + un sharecode inicial
(ambos generados por él en help.steampowered.com, appid 730 issue 128) y
el worker (cs2-ingest --source steam) avanza su cadena de sharecodes y
trae los demos. Acá solo vive el alta/baja/estado; el polling no.
"""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from cs2tracker.api.schemas import AutofetchLinkIn, AutofetchStatusOut
from cs2tracker.auth import get_current_steamid
from cs2tracker.config import settings
from cs2tracker.db import User
from cs2tracker.db.session import get_engine
from cs2tracker.infra.sharecode import extract_sharecode
from cs2tracker.infra.steam_sharecodes import (
    AuthCodeInvalid,
    SharecodeChainError,
    get_next_sharecode,
)

router = APIRouter(prefix="/autofetch", tags=["autofetch"])

# Formato del Game Authentication Code que emite Steam: AAAA-AAAAA-AAAA.
AUTH_CODE_RE = re.compile(r"^[A-Za-z0-9]{4}-[A-Za-z0-9]{5}-[A-Za-z0-9]{4}$")


def _status_out(user: User | None) -> AutofetchStatusOut:
    if user is None or user.steam_auth_code is None:
        return AutofetchStatusOut(
            linked=False,
            status=user.autofetch_status if user else None,
            error=user.autofetch_error if user else None,
            last_sharecode=user.last_sharecode if user else None,
            last_polled_at=None,
            last_fetched_at=None,
        )
    return AutofetchStatusOut(
        linked=True,
        status=user.autofetch_status,
        error=user.autofetch_error,
        last_sharecode=user.last_sharecode,
        last_polled_at=user.last_polled_at,
        last_fetched_at=user.last_fetched_at,
    )


@router.get("/status", response_model=AutofetchStatusOut)
def autofetch_status(steamid: str = Depends(get_current_steamid)) -> AutofetchStatusOut:
    with Session(get_engine()) as s:
        return _status_out(s.get(User, steamid))


@router.post("/link", response_model=AutofetchStatusOut)
def autofetch_link(
    body: AutofetchLinkIn, steamid: str = Depends(get_current_steamid)
) -> AutofetchStatusOut:
    if not settings.steam_api_key:
        raise HTTPException(503, "el servidor no tiene CS2_STEAM_API_KEY configurada")

    auth_code = body.auth_code.strip()
    if not AUTH_CODE_RE.match(auth_code):
        raise HTTPException(400, "auth code inválido: el formato es AAAA-AAAAA-AAAA")

    sharecode = extract_sharecode(body.sharecode)
    if sharecode is None:
        raise HTTPException(400, "sharecode inválido: el formato es CSGO-XXXXX-...")

    # Validación en vivo contra Steam ANTES de persistir: un paso de la
    # cadena con el propio code como knowncode ("n/a" también es éxito).
    try:
        get_next_sharecode(steamid, auth_code, sharecode, api_key=settings.steam_api_key)
    except AuthCodeInvalid:
        raise HTTPException(
            400, "Steam rechazó el auth code: verificá que sea el de TU cuenta y esté vigente"
        ) from None
    except SharecodeChainError:
        raise HTTPException(502, "Steam no respondió; probá de nuevo en un rato") from None

    with Session(get_engine()) as s:
        user = s.get(User, steamid)
        if user is None:
            raise HTTPException(401, "no autenticado")
        user.steam_auth_code = auth_code
        user.last_sharecode = sharecode
        user.autofetch_status = "active"
        user.autofetch_error = None
        s.commit()
        return _status_out(user)


@router.delete("/link", response_model=AutofetchStatusOut)
def autofetch_unlink(steamid: str = Depends(get_current_steamid)) -> AutofetchStatusOut:
    with Session(get_engine()) as s:
        user = s.get(User, steamid)
        if user is None:
            raise HTTPException(401, "no autenticado")
        # last_sharecode se conserva a propósito: re-vincular retoma la
        # cadena donde quedó, sin perder partidas intermedias.
        user.steam_auth_code = None
        user.autofetch_status = None
        user.autofetch_error = None
        s.commit()
        return _status_out(user)
