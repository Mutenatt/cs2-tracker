"""
Tokens personales (API keys) para clientes que no son el navegador -- hoy
solo el overlay de escritorio (ver app/). Separado de auth.py/
auth_password.py a propósito: esos dos son sesión (cookie, con expiración
corta/renovable); esto es un secreto de larga vida que el usuario genera una
vez desde /settings y pega en otro proceso.

Hash con SHA-256 simple, NO Argon2: el token es 32 bytes de secrets.
token_urlsafe (256 bits de entropía), así que un hash lento contra fuerza
bruta no aporta nada (a diferencia de una password humana, corta y
adivinable) y sí costaría una consulta lenta en cada request autenticado del
overlay. El hash es solo para no guardar el secreto en claro en la DB.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from cs2tracker.db.models import ApiToken
from cs2tracker.db.session import get_engine

TOKEN_PREFIX = "cst_"
# Mostrado en la lista de tokens para que el usuario reconozca cuál es cuál
# sin que alcance para reconstruir el secreto (mismo criterio que GitHub PATs).
VISIBLE_PREFIX_LEN = len(TOKEN_PREFIX) + 6


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_token(steamid: str, name: str) -> tuple[ApiToken, str]:
    """Devuelve (fila, token en claro). El token en claro NUNCA se persiste
    ni se puede volver a mostrar -- el caller lo devuelve al usuario una
    sola vez, en la respuesta de creación."""
    raw = TOKEN_PREFIX + secrets.token_urlsafe(32)
    now = datetime.now(UTC).isoformat()
    row = ApiToken(
        steamid=steamid,
        name=name,
        token_hash=_hash(raw),
        token_prefix=raw[:VISIBLE_PREFIX_LEN],
        created_at=now,
    )
    with Session(get_engine()) as s:
        s.add(row)
        s.commit()
        s.refresh(row)
    return row, raw


def steamid_for_token(raw_token: str) -> str | None:
    """Valida un token del header Authorization y bumpea last_used_at.
    None si no existe, está revocado, o no tiene el prefijo esperado."""
    if not raw_token.startswith(TOKEN_PREFIX):
        return None
    with Session(get_engine()) as s:
        row = s.execute(
            select(ApiToken).where(ApiToken.token_hash == _hash(raw_token))
        ).scalar_one_or_none()
        if row is None or row.revoked_at is not None:
            return None
        row.last_used_at = datetime.now(UTC).isoformat()
        s.commit()
        return row.steamid
