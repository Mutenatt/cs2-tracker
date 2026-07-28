"""
Endpoints internos, dirección inversa a los demás (gc-sidecar -> backend):
el sidecar los usa para decidir si auto-acepta una solicitud de amistad
entrante (solo de steamids que ya son `User` registrado en el sitio) y para
avisar cuando la amistad quedó confirmada.

El bind local del sidecar ("solo 127.0.0.1") no protege esto, porque el
puerto de la API pública sirve todo junto detrás del proxy de Vite -- la
protección real es el secreto compartido `X-Internal-Secret`. Si
`CS2_INTERNAL_SHARED_SECRET` no está configurado, estos endpoints quedan
deshabilitados (401) en vez de aceptar cualquier request.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from cs2tracker.config import settings
from cs2tracker.db import User
from cs2tracker.db.session import get_engine

router = APIRouter(prefix="/internal", tags=["internal"])


def require_internal_secret(x_internal_secret: str | None = Header(default=None)) -> None:
    if not settings.internal_shared_secret or x_internal_secret != settings.internal_shared_secret:
        raise HTTPException(401, "no autorizado")


@router.get("/steam-users/{steamid}/registered")
def steam_user_registered(
    steamid: str, _: None = Depends(require_internal_secret)
) -> dict[str, bool]:
    with Session(get_engine()) as s:
        return {"registered": s.get(User, steamid) is not None}


@router.post("/steam-users/{steamid}/bot-friend-confirmed")
def steam_user_bot_friend_confirmed(
    steamid: str, _: None = Depends(require_internal_secret)
) -> dict[str, bool]:
    with Session(get_engine()) as s:
        user = s.get(User, steamid)
        if user is None:
            raise HTTPException(404, "usuario no registrado")
        user.bot_friend_added_at = datetime.now(UTC).isoformat()
        s.commit()
        return {"ok": True}
