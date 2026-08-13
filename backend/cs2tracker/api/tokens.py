"""
Alta/baja de tokens personales (ver cs2tracker/api_tokens.py) desde
/settings en la web -- el usuario genera uno, lo pega en el overlay de
escritorio (ver app/), y puede revocarlo en cualquier momento sin tocar su
sesión de navegador (son mecanismos independientes, ver
auth.get_current_actor). Requiere cookie de sesión real: un token no puede
usarse para crear OTRO token (si se filtra uno, el radio de daño es "leer
lineups", no "generar más acceso")."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from cs2tracker.api.schemas import (
    ApiTokenCreatedOut,
    ApiTokenCreateIn,
    ApiTokenOut,
    ApiTokensResponse,
)
from cs2tracker.api_tokens import create_token
from cs2tracker.auth import get_current_steamid
from cs2tracker.db import ApiToken
from cs2tracker.db.session import get_engine

router = APIRouter(prefix="/account/tokens", tags=["tokens"])

MAX_TOKENS_PER_USER = 10


@router.get("", response_model=ApiTokensResponse)
def list_tokens(steamid: str = Depends(get_current_steamid)) -> ApiTokensResponse:
    with Session(get_engine()) as s:
        rows = (
            s.execute(
                select(ApiToken)
                .where(ApiToken.steamid == steamid)
                .order_by(ApiToken.created_at.desc())
            )
            .scalars()
            .all()
        )
        return ApiTokensResponse(
            tokens=[
                ApiTokenOut(
                    id=r.id,
                    name=r.name,
                    token_prefix=r.token_prefix,
                    created_at=r.created_at,
                    last_used_at=r.last_used_at,
                    revoked_at=r.revoked_at,
                )
                for r in rows
            ]
        )


@router.post("", response_model=ApiTokenCreatedOut)
def create_token_endpoint(
    body: ApiTokenCreateIn, steamid: str = Depends(get_current_steamid)
) -> ApiTokenCreatedOut:
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "el token necesita un nombre")
    with Session(get_engine()) as s:
        active = (
            s.execute(
                select(ApiToken).where(ApiToken.steamid == steamid, ApiToken.revoked_at.is_(None))
            )
            .scalars()
            .all()
        )
        if len(active) >= MAX_TOKENS_PER_USER:
            raise HTTPException(409, f"máximo {MAX_TOKENS_PER_USER} tokens activos")

    row, raw = create_token(steamid, name)
    return ApiTokenCreatedOut(
        id=row.id,
        name=row.name,
        token=raw,
        token_prefix=row.token_prefix,
        created_at=row.created_at,
    )


@router.delete("/{token_id}", response_model=ApiTokensResponse)
def revoke_token(token_id: int, steamid: str = Depends(get_current_steamid)) -> ApiTokensResponse:
    with Session(get_engine()) as s:
        row = s.get(ApiToken, token_id)
        if row is None or row.steamid != steamid:
            raise HTTPException(404, "token no encontrado")
        if row.revoked_at is None:
            row.revoked_at = datetime.now(UTC).isoformat()
            s.commit()
    return list_tokens(steamid)
