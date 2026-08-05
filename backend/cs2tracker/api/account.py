"""
Auth: alta de cuenta por email+contraseña, verificación de email, link a
Steam, login, logout, y recuperación de contraseña. Todas las rutas /auth/*
viven acá (antes algunas estaban sueltas en api/main.py).

Orden del flujo: POST /auth/register (crea AccountSignup, cookie pending) ->
click en el link del mail -> GET /auth/verify-email -> GET /auth/steam/link
(requiere email verificado) -> GET /auth/callback (crea el User real, borra
el pending, cookie real). POST /auth/login sirve tanto para cuentas ya
vinculadas (cookie real) como para retomar un pending sin verificar/vincular
todavía (cookie pending).
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from cs2tracker.api.schemas import (
    ForgotPasswordIn,
    LoginIn,
    MeOut,
    RegisterIn,
    ResetPasswordIn,
)
from cs2tracker.auth import (
    COOKIE_NAME as REAL_COOKIE_NAME,
)
from cs2tracker.auth import (
    SESSION_MAX_AGE as REAL_SESSION_MAX_AGE,
)
from cs2tracker.auth import (
    build_login_url,
    create_session_cookie,
    fetch_profile,
    get_current_steamid_optional,
    steam_profile_is_stale,
    verify_callback,
)
from cs2tracker.auth_password import (
    PENDING_COOKIE_NAME,
    PENDING_SESSION_MAX_AGE,
    create_email_verify_token,
    create_password_reset_token,
    create_pending_cookie,
    get_current_pending_id,
    get_current_pending_id_optional,
    hash_password,
    is_valid_email,
    normalize_email,
    read_email_verify_token,
    read_password_reset_token,
    verify_password,
)
from cs2tracker.config import settings
from cs2tracker.db import AccountSignup, Player, User
from cs2tracker.db.session import get_engine
from cs2tracker.infra.mail import send_email

router = APIRouter(prefix="/auth", tags=["auth"])

# Hash fijo precomputado para emparejar el tiempo de respuesta de
# /auth/login cuando el email no existe (si no, un email inexistente
# responde más rápido que uno con password incorrecta, porque Argon2 es
# deliberadamente costoso -- eso filtra qué emails están registrados).
_DUMMY_HASH = hash_password(secrets.token_hex(16))


def _me_out_for_user(user: User) -> MeOut:
    return MeOut(
        pending=False,
        steamid=user.steamid,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        steam_background_url=user.steam_background_url,
        email=user.email,
        email_verified_at=user.email_verified_at,
        onboarding_completed_at=user.onboarding_completed_at,
    )


async def _maybe_refresh_steam_profile(session: Session, user: User) -> None:
    """Re-scrapea display_name/avatar/background de Steam si pasó
    STEAM_PROFILE_REFRESH_INTERVAL desde el último sync -- ver
    auth.steam_profile_is_stale. Es lo que hace que un cambio de fondo hecho
    en Steam se refleje solo, sin tener que desvincular/re-vincular la
    cuenta."""
    if not steam_profile_is_stale(user.steam_profile_synced_at):
        return

    display_name, avatar_url, steam_background_url = await fetch_profile(user.steamid)
    # display_name/avatar_url: la Web API de Steam es confiable, así que None
    # acá solo pasa si el fetch entero falló -- no pisar lo ya guardado.
    if display_name is not None:
        user.display_name = display_name
    if avatar_url is not None:
        user.avatar_url = avatar_url
    # steam_background_url en cambio puede ser None tanto porque el usuario
    # de verdad no tiene background como por un scraping fallido/rate-limited
    # (ver auth.fetch_profiles) -- mismo ambiguity que ya aceptaba el alta de
    # cuenta. Para el refresco periódico, de mínima, no pisamos un background
    # que ya funcionaba con un None que bien puede ser un 429 transitorio.
    if steam_background_url is not None:
        user.steam_background_url = steam_background_url
    user.steam_profile_synced_at = datetime.now(UTC).isoformat()
    session.commit()


def _me_out_for_pending(pending: AccountSignup) -> MeOut:
    return MeOut(
        pending=True,
        steamid=None,
        display_name=None,
        avatar_url=None,
        email=pending.email,
        email_verified_at=pending.email_verified_at,
        onboarding_completed_at=None,
    )


def _set_pending_cookie(resp: RedirectResponse, pending_id: int) -> None:
    resp.set_cookie(
        PENDING_COOKIE_NAME,
        create_pending_cookie(pending_id),
        max_age=PENDING_SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
    )


@router.post("/register", status_code=201, response_model=MeOut)
def auth_register(body: RegisterIn):
    email = normalize_email(body.email)
    if not is_valid_email(email):
        raise HTTPException(400, "email inválido")
    if len(body.password) < 8:
        raise HTTPException(400, "la contraseña tiene que tener al menos 8 caracteres")

    with Session(get_engine()) as s:
        if s.query(User).filter(User.email == email).first() is not None:
            raise HTTPException(409, "ya existe una cuenta con ese email")
        if s.query(AccountSignup).filter(AccountSignup.email == email).first() is not None:
            raise HTTPException(409, "ya existe una cuenta con ese email")

        pending = AccountSignup(
            email=email,
            password_hash=hash_password(body.password),
            email_verified_at=None,
            created_at=datetime.now(UTC).isoformat(),
        )
        s.add(pending)
        s.commit()
        s.refresh(pending)

        token = create_email_verify_token(pending.id)
        verify_url = f"{settings.api_public_url}/auth/verify-email?token={token}"
        send_email(
            email,
            "Verificá tu email en cStats",
            f"Confirmá tu cuenta para seguir con el registro:\n\n{verify_url}",
        )

        resp_body = _me_out_for_pending(pending)

    resp = Response(
        content=resp_body.model_dump_json(), media_type="application/json", status_code=201
    )
    _set_pending_cookie(resp, pending.id)
    return resp


@router.get("/verify-email")
def auth_verify_email(token: str):
    pending_id = read_email_verify_token(token)
    if pending_id is None:
        return RedirectResponse(f"{settings.frontend_url}/?verify_error=invalid_or_expired")

    with Session(get_engine()) as s:
        pending = s.get(AccountSignup, pending_id)
        if pending is None:
            return RedirectResponse(f"{settings.frontend_url}/?verify_error=invalid_or_expired")
        if pending.email_verified_at is None:
            pending.email_verified_at = datetime.now(UTC).isoformat()
            s.commit()
        pending_id_confirmed = pending.id

    # Re-emitir la cookie pending: el link se clickea típicamente desde otro
    # dispositivo/pestaña que nunca tuvo la cookie original -- sin esto el
    # usuario queda verificado pero sin sesión, y no puede seguir al link de Steam.
    resp = RedirectResponse(f"{settings.frontend_url}/?verified=1")
    _set_pending_cookie(resp, pending_id_confirmed)
    return resp


@router.post("/resend-verification")
def auth_resend_verification(request: Request):
    pending_id = get_current_pending_id(request)
    with Session(get_engine()) as s:
        pending = s.get(AccountSignup, pending_id)
        if pending is None:
            raise HTTPException(401, "sesión pendiente inválida")
        if pending.email_verified_at is not None:
            return {"ok": True}
        token = create_email_verify_token(pending.id)
        verify_url = f"{settings.api_public_url}/auth/verify-email?token={token}"
        send_email(
            pending.email,
            "Verificá tu email en cStats",
            f"Confirmá tu cuenta para seguir con el registro:\n\n{verify_url}",
        )
    return {"ok": True}


@router.get("/steam/link")
def auth_steam_link(request: Request):
    pending_id = get_current_pending_id(request)
    with Session(get_engine()) as s:
        pending = s.get(AccountSignup, pending_id)
        if pending is None:
            raise HTTPException(401, "sesión pendiente inválida")
        if pending.email_verified_at is None:
            raise HTTPException(403, "verificá tu email antes de vincular Steam")
    return RedirectResponse(build_login_url())


@router.get("/callback")
async def auth_callback(request: Request):
    pending_id = get_current_pending_id_optional(request)
    if pending_id is None:
        return RedirectResponse(f"{settings.frontend_url}/register?error=pending_session_expired")

    steamid = await verify_callback(dict(request.query_params))
    if steamid is None:
        raise HTTPException(400, "login de Steam inválido")

    with Session(get_engine()) as s:
        pending = s.get(AccountSignup, pending_id)
        if pending is None or pending.email_verified_at is None:
            return RedirectResponse(
                f"{settings.frontend_url}/register?error=pending_session_expired"
            )
        if s.get(User, steamid) is not None:
            return RedirectResponse(f"{settings.frontend_url}/register?error=steam_already_linked")

        display_name, avatar_url, steam_background_url = await fetch_profile(steamid)
        now = datetime.now(UTC).isoformat()
        if s.get(Player, steamid) is None:
            s.add(Player(steamid=steamid, name=display_name))

        user = User(
            steamid=steamid,
            display_name=display_name,
            avatar_url=avatar_url,
            steam_background_url=steam_background_url,
            steam_profile_synced_at=now,
            last_login_at=now,
            email=pending.email,
            password_hash=pending.password_hash,
            email_verified_at=pending.email_verified_at,
        )
        s.add(user)
        s.delete(pending)
        try:
            s.commit()
        except IntegrityError:
            s.rollback()
            return RedirectResponse(f"{settings.frontend_url}/register?error=steam_already_linked")

    resp = RedirectResponse(settings.frontend_url)
    resp.set_cookie(
        REAL_COOKIE_NAME,
        create_session_cookie(steamid),
        max_age=REAL_SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
    )
    resp.delete_cookie(PENDING_COOKIE_NAME)
    return resp


@router.post("/login", response_model=MeOut)
def auth_login(body: LoginIn):
    email = normalize_email(body.email)

    with Session(get_engine()) as s:
        user = s.query(User).filter(User.email == email).first()
        if user is not None:
            if not verify_password(body.password, user.password_hash):
                raise HTTPException(401, "credenciales inválidas")

            resp = Response(
                content=_me_out_for_user(user).model_dump_json(), media_type="application/json"
            )
            resp.set_cookie(
                REAL_COOKIE_NAME,
                create_session_cookie(user.steamid),
                max_age=REAL_SESSION_MAX_AGE,
                httponly=True,
                samesite="lax",
            )
            return resp

        pending = s.query(AccountSignup).filter(AccountSignup.email == email).first()
        if pending is not None:
            if not verify_password(body.password, pending.password_hash):
                raise HTTPException(401, "credenciales inválidas")

            resp = Response(
                content=_me_out_for_pending(pending).model_dump_json(),
                media_type="application/json",
            )
            _set_pending_cookie(resp, pending.id)
            return resp

        # Email inexistente: correr un verify_password dummy para emparejar
        # el tiempo de respuesta con el caso "password incorrecta" de arriba.
        verify_password(body.password, _DUMMY_HASH)
        raise HTTPException(401, "credenciales inválidas")


@router.post("/forgot-password")
def auth_forgot_password(body: ForgotPasswordIn):
    email = normalize_email(body.email)
    with Session(get_engine()) as s:
        user = s.query(User).filter(User.email == email).first()
        if user is not None:
            token = create_password_reset_token("user", user.steamid)
            reset_url = f"{settings.frontend_url}/reset-password?token={token}"
            send_email(
                email, "Restablecer tu contraseña en cStats", f"Elegí una nueva:\n\n{reset_url}"
            )
        else:
            pending = s.query(AccountSignup).filter(AccountSignup.email == email).first()
            if pending is not None:
                token = create_password_reset_token("pending", str(pending.id))
                reset_url = f"{settings.frontend_url}/reset-password?token={token}"
                send_email(
                    email, "Restablecer tu contraseña en cStats", f"Elegí una nueva:\n\n{reset_url}"
                )
    # Respuesta idéntica siempre, exista o no el email -- evita enumeración.
    return {"ok": True}


@router.post("/reset-password")
def auth_reset_password(body: ResetPasswordIn):
    decoded = read_password_reset_token(body.token)
    if decoded is None:
        raise HTTPException(400, "el link de reset es inválido o expiró")
    if len(body.new_password) < 8:
        raise HTTPException(400, "la contraseña tiene que tener al menos 8 caracteres")
    kind, id_ = decoded

    with Session(get_engine()) as s:
        if kind == "user":
            user = s.get(User, id_)
            if user is None:
                raise HTTPException(400, "cuenta no encontrada")
            user.password_hash = hash_password(body.new_password)
        elif kind == "pending":
            pending = s.get(AccountSignup, int(id_))
            if pending is None:
                raise HTTPException(400, "cuenta no encontrada")
            pending.password_hash = hash_password(body.new_password)
        else:
            raise HTTPException(400, "token inválido")
        s.commit()
    return {"ok": True}


@router.get("/me", response_model=MeOut)
async def auth_me(request: Request):
    real_steamid = get_current_steamid_optional(request)
    if real_steamid:
        with Session(get_engine()) as s:
            user = s.get(User, real_steamid)
            if user is not None:
                await _maybe_refresh_steam_profile(s, user)
                return _me_out_for_user(user)

    pending_id = get_current_pending_id_optional(request)
    if pending_id:
        with Session(get_engine()) as s:
            pending = s.get(AccountSignup, pending_id)
            if pending is not None:
                return _me_out_for_pending(pending)

    raise HTTPException(401, "no autenticado")


@router.post("/logout")
def auth_logout():

    resp = Response(content='{"ok": true}', media_type="application/json")
    resp.delete_cookie(REAL_COOKIE_NAME)
    resp.delete_cookie(PENDING_COOKIE_NAME)
    return resp
