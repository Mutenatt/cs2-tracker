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

import base64
import io
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pyotp
import qrcode
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from cs2tracker.api.schemas import (
    ChangeEmailIn,
    ChangePasswordIn,
    DeleteAccountIn,
    DesktopLoginIn,
    DesktopLoginOut,
    ForgotPasswordIn,
    LoginHistoryEntry,
    LoginHistoryResponse,
    LoginIn,
    LoginOut,
    LoginTotpIn,
    MeOut,
    RegisterIn,
    ResetPasswordIn,
    SteamRelinkStartIn,
    SteamRelinkStartOut,
    TotpActivateIn,
    TotpActivateOut,
    TotpDisableIn,
    TotpEnrollOut,
)
from cs2tracker.api.tokens import MAX_TOKENS_PER_USER
from cs2tracker.auth import (
    COOKIE_NAME as REAL_COOKIE_NAME,
)
from cs2tracker.auth import (
    SESSION_MAX_AGE as REAL_SESSION_MAX_AGE,
)
from cs2tracker.auth import (
    build_login_url,
    build_relink_login_url,
    create_session_cookie,
    fetch_profile,
    get_current_steamid,
    get_current_steamid_optional,
    require_same_origin,
    steam_profile_is_stale,
    verify_callback,
)
from cs2tracker.auth_password import (
    MFA_PENDING_COOKIE_NAME,
    MFA_PENDING_MAX_AGE,
    PENDING_COOKIE_NAME,
    PENDING_SESSION_MAX_AGE,
    RELINK_COOKIE_NAME,
    create_email_change_token,
    create_email_verify_token,
    create_mfa_pending_cookie,
    create_password_reset_token,
    create_pending_cookie,
    create_relink_cookie,
    get_current_pending_id,
    get_current_pending_id_optional,
    hash_password,
    is_valid_email,
    normalize_email,
    read_email_change_token,
    read_email_verify_token,
    read_mfa_pending_cookie,
    read_password_reset_token,
    read_relink_cookie,
    verify_password,
)
from cs2tracker.api_tokens import create_token
from cs2tracker.config import settings
from cs2tracker.db import AccountSignup, ApiToken, ClipJob, LoginEvent, Player, TotpBackupCode, User
from cs2tracker.db.session import get_engine
from cs2tracker.infra.mail import send_email
from cs2tracker.rate_limit import (
    enforce_rate_limit,
    is_locked,
    is_totp_locked,
    record_login_failure,
    record_login_success,
    record_totp_failure,
    record_totp_success,
)

router = APIRouter(prefix="/auth", tags=["auth"])


# request.client puede ser None en algunos test clients / contextos sin
# socket real (nunca en producción detrás de uvicorn) -- se usa como key de
# rate limit igual, agrupando esos casos bajo una clave fija.
def _client_ip(request: Request) -> str:
    return request.client.host if request.client is not None else "unknown"


# Hash fijo precomputado para emparejar el tiempo de respuesta de
# /auth/login cuando el email no existe (si no, un email inexistente
# responde más rápido que uno con password incorrecta, porque Argon2 es
# deliberadamente costoso -- eso filtra qué emails están registrados).
_DUMMY_HASH = hash_password(secrets.token_hex(16))

_ACCOUNT_LOCKED_MSG = (
    "cuenta bloqueada temporalmente por intentos fallidos, probá de nuevo en unos minutos"
)


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
        totp_enabled=user.totp_enabled_at is not None,
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


# Ventana de "IP ya vista" para la notificación de login nuevo -- no
# "siempre notificar" (spam para logins frecuentes desde la misma IP), ni
# fingerprinting de dispositivo (no hay esa infra hoy, User-Agent solo es
# débil/spoofeable). Trade-off aceptado: una IP compartida/NAT puede
# enmascarar un dispositivo genuinamente nuevo.
_NEW_LOGIN_NOTICE_WINDOW_DAYS = 90


def _log_login_event(
    session: Session,
    *,
    steamid: str | None,
    email: str | None,
    request: Request,
    success: bool,
    reason: str,
) -> None:
    session.add(
        LoginEvent(
            occurred_at=datetime.now(UTC).isoformat(),
            steamid=steamid,
            email=email,
            ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
            success=success,
            reason=reason,
        )
    )
    session.commit()


def _maybe_notify_new_login(session: Session, user: User, request: Request) -> None:
    """Manda un aviso por email si esta IP no tenía un login exitoso
    reciente para esta cuenta -- ver _NEW_LOGIN_NOTICE_WINDOW_DAYS."""
    ip = _client_ip(request)
    cutoff = (datetime.now(UTC) - timedelta(days=_NEW_LOGIN_NOTICE_WINDOW_DAYS)).isoformat()
    seen_before = (
        session.query(LoginEvent)
        .filter(
            LoginEvent.steamid == user.steamid,
            LoginEvent.ip == ip,
            LoginEvent.success.is_(True),
            LoginEvent.occurred_at >= cutoff,
            LoginEvent.occurred_at < datetime.now(UTC).isoformat(),
        )
        .first()
    )
    if seen_before is not None:
        return
    send_email(
        user.email,
        "Nuevo inicio de sesión en monkeyStats",
        f"Se inició sesión en tu cuenta desde una IP nueva ({ip}) el "
        f"{datetime.now(UTC).isoformat()}. Si no fuiste vos, cambiá tu contraseña.",
    )


@router.post("/register", status_code=201, response_model=MeOut)
def auth_register(body: RegisterIn, request: Request):
    email = normalize_email(body.email)
    if not is_valid_email(email):
        raise HTTPException(400, "email inválido")
    if len(body.password) < 8:
        raise HTTPException(400, "la contraseña tiene que tener al menos 8 caracteres")

    with Session(get_engine()) as s:
        enforce_rate_limit(s, "register", _client_ip(request), window_seconds=3600, max_count=5)

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
            "Verificá tu email en monkeyStats",
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
        enforce_rate_limit(
            s, "resend_verification", _client_ip(request), window_seconds=3600, max_count=10
        )
        enforce_rate_limit(
            s,
            "resend_verification_pending",
            str(pending_id),
            window_seconds=3600,
            max_count=3,
        )

        pending = s.get(AccountSignup, pending_id)
        if pending is None:
            raise HTTPException(401, "sesión pendiente inválida")
        if pending.email_verified_at is not None:
            return {"ok": True}
        token = create_email_verify_token(pending.id)
        verify_url = f"{settings.api_public_url}/auth/verify-email?token={token}"
        send_email(
            pending.email,
            "Verificá tu email en monkeyStats",
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

    with Session(get_engine()) as s:
        enforce_rate_limit(
            s, "steam_callback", _client_ip(request), window_seconds=3600, max_count=20
        )

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

        _log_login_event(
            s, steamid=steamid, email=user.email, request=request, success=True, reason="ok"
        )

    resp = RedirectResponse(settings.frontend_url)
    resp.set_cookie(
        REAL_COOKIE_NAME,
        create_session_cookie(steamid, epoch=0),
        max_age=REAL_SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
    )
    resp.delete_cookie(PENDING_COOKIE_NAME)
    return resp


@router.post("/login", response_model=LoginOut)
def auth_login(body: LoginIn, request: Request):
    email = normalize_email(body.email)

    with Session(get_engine()) as s:
        enforce_rate_limit(s, "login", _client_ip(request), window_seconds=900, max_count=20)

        user = s.query(User).filter(User.email == email).first()
        if user is not None:
            if is_locked(user):
                # 423, sin correr Argon2: más rápido, y evita que el propio
                # chequeo de password sea el cuello de botella bajo un
                # bloqueo activo. La leak de "esta cuenta está bloqueada" es
                # aceptada a propósito (distinto del no-enumeración de
                # abajo) -- un usuario legítimo bloqueado necesita un
                # mensaje accionable.
                _log_login_event(
                    s,
                    steamid=user.steamid,
                    email=email,
                    request=request,
                    success=False,
                    reason="locked",
                )
                raise HTTPException(423, _ACCOUNT_LOCKED_MSG)
            if not verify_password(body.password, user.password_hash):
                record_login_failure(user)
                _log_login_event(
                    s,
                    steamid=user.steamid,
                    email=email,
                    request=request,
                    success=False,
                    reason="bad_password",
                )
                s.commit()
                raise HTTPException(401, "credenciales inválidas")
            record_login_success(user)

            if user.totp_enabled_at is not None:
                # Password correcta, pero falta el segundo factor: NO se
                # emite la cookie real todavía. Cookie de 10 min que solo
                # sirve para /auth/login/totp.
                _log_login_event(
                    s,
                    steamid=user.steamid,
                    email=email,
                    request=request,
                    success=False,
                    reason="totp_required",
                )
                s.commit()
                resp = Response(
                    content=LoginOut(mfa_required=True).model_dump_json(),
                    media_type="application/json",
                )
                resp.set_cookie(
                    MFA_PENDING_COOKIE_NAME,
                    create_mfa_pending_cookie(user.steamid),
                    max_age=MFA_PENDING_MAX_AGE,
                    httponly=True,
                    samesite="lax",
                )
                return resp

            _maybe_notify_new_login(s, user, request)
            _log_login_event(
                s, steamid=user.steamid, email=email, request=request, success=True, reason="ok"
            )
            s.commit()

            resp = Response(
                content=LoginOut(mfa_required=False, me=_me_out_for_user(user)).model_dump_json(),
                media_type="application/json",
            )
            resp.set_cookie(
                REAL_COOKIE_NAME,
                create_session_cookie(user.steamid, epoch=user.session_epoch),
                max_age=REAL_SESSION_MAX_AGE,
                httponly=True,
                samesite="lax",
            )
            return resp

        pending = s.query(AccountSignup).filter(AccountSignup.email == email).first()
        if pending is not None:
            if is_locked(pending):
                _log_login_event(
                    s, steamid=None, email=email, request=request, success=False, reason="locked"
                )
                raise HTTPException(423, _ACCOUNT_LOCKED_MSG)
            if not verify_password(body.password, pending.password_hash):
                record_login_failure(pending)
                _log_login_event(
                    s,
                    steamid=None,
                    email=email,
                    request=request,
                    success=False,
                    reason="bad_password",
                )
                s.commit()
                raise HTTPException(401, "credenciales inválidas")
            record_login_success(pending)
            _log_login_event(
                s,
                steamid=None,
                email=email,
                request=request,
                success=True,
                reason="pending_resumed",
            )
            s.commit()

            resp = Response(
                content=LoginOut(
                    mfa_required=False, me=_me_out_for_pending(pending)
                ).model_dump_json(),
                media_type="application/json",
            )
            _set_pending_cookie(resp, pending.id)
            return resp

        # Email inexistente: correr un verify_password dummy para emparejar
        # el tiempo de respuesta con el caso "password incorrecta" de arriba.
        verify_password(body.password, _DUMMY_HASH)
        _log_login_event(
            s,
            steamid=None,
            email=email,
            request=request,
            success=False,
            reason="no_such_account",
        )
        raise HTTPException(401, "credenciales inválidas")


@router.post("/forgot-password")
def auth_forgot_password(body: ForgotPasswordIn, request: Request):
    email = normalize_email(body.email)
    with Session(get_engine()) as s:
        enforce_rate_limit(
            s, "forgot_password", _client_ip(request), window_seconds=3600, max_count=5
        )
        enforce_rate_limit(s, "forgot_password_email", email, window_seconds=3600, max_count=3)

        user = s.query(User).filter(User.email == email).first()
        if user is not None:
            token = create_password_reset_token("user", user.steamid)
            reset_url = f"{settings.frontend_url}/reset-password?token={token}"
            send_email(
                email,
                "Restablecer tu contraseña en monkeyStats",
                f"Elegí una nueva:\n\n{reset_url}",
            )
        else:
            pending = s.query(AccountSignup).filter(AccountSignup.email == email).first()
            if pending is not None:
                token = create_password_reset_token("pending", str(pending.id))
                reset_url = f"{settings.frontend_url}/reset-password?token={token}"
                send_email(
                    email,
                    "Restablecer tu contraseña en monkeyStats",
                    f"Elegí una nueva:\n\n{reset_url}",
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


@router.post("/change-password", response_model=MeOut)
def auth_change_password(
    body: ChangePasswordIn,
    steamid: str = Depends(get_current_steamid),
    _origin: None = Depends(require_same_origin),
):
    """A diferencia de /auth/reset-password (vía email, para cuando no
    tenés la password actual), esto es el cambio in-place: requiere la
    password actual y bumpea session_epoch -- invalida todas las demás
    sesiones (ver auth.py::get_current_steamid), y reemite la cookie de
    ESTE request con el epoch nuevo para que el dispositivo que hizo el
    cambio no se desloguee a sí mismo."""
    if len(body.new_password) < 8:
        raise HTTPException(400, "la contraseña tiene que tener al menos 8 caracteres")

    with Session(get_engine()) as s:
        user = s.get(User, steamid)
        if user is None:
            raise HTTPException(401, "no autenticado")
        if not verify_password(body.current_password, user.password_hash):
            raise HTTPException(401, "contraseña actual incorrecta")

        user.password_hash = hash_password(body.new_password)
        user.session_epoch += 1
        s.commit()

        resp = Response(
            content=_me_out_for_user(user).model_dump_json(), media_type="application/json"
        )
        resp.set_cookie(
            REAL_COOKIE_NAME,
            create_session_cookie(steamid, epoch=user.session_epoch),
            max_age=REAL_SESSION_MAX_AGE,
            httponly=True,
            samesite="lax",
        )
        return resp


@router.post("/change-email")
def auth_change_email(
    body: ChangeEmailIn,
    steamid: str = Depends(get_current_steamid),
    _origin: None = Depends(require_same_origin),
):
    """El email NO cambia acá -- se guarda en pending_email y se manda un
    link de confirmación a la dirección NUEVA (no a la vieja). El cambio
    real ocurre recién en /auth/verify-email-change, cuando el click en ese
    link prueba que el usuario controla la casilla nueva."""
    new_email = normalize_email(body.new_email)
    if not is_valid_email(new_email):
        raise HTTPException(400, "email inválido")

    with Session(get_engine()) as s:
        user = s.get(User, steamid)
        if user is None:
            raise HTTPException(401, "no autenticado")
        if not verify_password(body.password, user.password_hash):
            raise HTTPException(401, "contraseña incorrecta")
        if s.query(User).filter(User.email == new_email).first() is not None:
            raise HTTPException(409, "ya existe una cuenta con ese email")
        if s.query(AccountSignup).filter(AccountSignup.email == new_email).first() is not None:
            raise HTTPException(409, "ya existe una cuenta con ese email")

        user.pending_email = new_email
        s.commit()

        token = create_email_change_token(steamid, new_email)
        verify_url = f"{settings.api_public_url}/auth/verify-email-change?token={token}"
        send_email(
            new_email,
            "Confirmá tu nuevo email en monkeyStats",
            f"Confirmá el cambio de email de tu cuenta:\n\n{verify_url}",
        )
    return {"ok": True}


@router.get("/verify-email-change")
def auth_verify_email_change(token: str):
    decoded = read_email_change_token(token)
    if decoded is None:
        return RedirectResponse(
            f"{settings.frontend_url}/settings?email_change_error=invalid_or_expired"
        )
    steamid, new_email = decoded

    with Session(get_engine()) as s:
        user = s.get(User, steamid)
        if user is None:
            return RedirectResponse(
                f"{settings.frontend_url}/settings?email_change_error=invalid_or_expired"
            )
        # El usuario puede haber pedido OTRO cambio de email desde que se
        # mandó este link -- un token viejo no debe poder "resucitar" un
        # cambio que ya no es el vigente.
        if user.pending_email != new_email:
            return RedirectResponse(
                f"{settings.frontend_url}/settings?email_change_error=invalid_or_expired"
            )

        user.email = new_email
        user.pending_email = None
        user.email_verified_at = datetime.now(UTC).isoformat()
        try:
            s.commit()
        except IntegrityError:
            s.rollback()
            return RedirectResponse(
                f"{settings.frontend_url}/settings?email_change_error=already_taken"
            )

    return RedirectResponse(f"{settings.frontend_url}/settings?email_changed=1")


@router.post("/delete-account")
def auth_delete_account(
    body: DeleteAccountIn,
    steamid: str = Depends(get_current_steamid),
    _origin: None = Depends(require_same_origin),
):
    """Borra la cuenta (fila users) y su contenido propio (clips, backup
    codes de 2FA). NO borra la fila players ni el historial de partidas
    (matches/match_players/kills/etc.) -- esas tablas FK a players.steamid,
    no a users.steamid, y compañeros de partidas compartidas siguen
    necesitando resolver este steamid (visibilidad es por pertenencia a
    match_players, no por ownership de la cuenta -- ver CLAUDE.md).
    login_events tampoco se borra (FK a players.steamid): es el audit
    trail de seguridad, tiene que sobrevivir al borrado de la cuenta que
    audita. totp_backup_codes se borra explícitamente en código, no vía
    ondelete=CASCADE -- ver TotpBackupCode, SQLite no aplica FK cascades."""
    with Session(get_engine()) as s:
        user = s.get(User, steamid)
        if user is None:
            raise HTTPException(401, "no autenticado")
        if not verify_password(body.password, user.password_hash):
            raise HTTPException(401, "contraseña incorrecta")

        s.query(TotpBackupCode).filter(TotpBackupCode.steamid == steamid).delete()

        clip_jobs = s.query(ClipJob).filter(ClipJob.steamid == steamid).all()
        for job in clip_jobs:
            if job.file_path:
                try:
                    Path(job.file_path).unlink(missing_ok=True)
                except OSError as exc:  # noqa: BLE001 -- best-effort, no bloquea el borrado
                    print(f"[auth_delete_account] no se pudo borrar {job.file_path}: {exc!r}")
            s.delete(job)

        s.delete(user)
        s.commit()

    resp = Response(content='{"ok": true}', media_type="application/json")
    resp.delete_cookie(REAL_COOKIE_NAME)
    resp.delete_cookie(PENDING_COOKIE_NAME)
    return resp


@router.post("/steam/relink/start", response_model=SteamRelinkStartOut)
def auth_steam_relink_start(
    body: SteamRelinkStartIn,
    steamid: str = Depends(get_current_steamid),
    _origin: None = Depends(require_same_origin),
):
    """No existe "desvincular Steam" -- users.steamid es PK NOT NULL y el
    invariante de la tabla es que todo User tiene un Steam vinculado. Lo
    que sí existe es "cambiar a otra cuenta de Steam": este endpoint arranca
    el login OpenID de la cuenta NUEVA; auth_steam_relink_callback hace la
    migración real una vez que Steam confirma esa cuenta nueva."""
    with Session(get_engine()) as s:
        user = s.get(User, steamid)
        if user is None:
            raise HTTPException(401, "no autenticado")
        if not verify_password(body.password, user.password_hash):
            raise HTTPException(401, "contraseña incorrecta")

    resp = SteamRelinkStartOut(redirect_url=build_relink_login_url())
    response = Response(content=resp.model_dump_json(), media_type="application/json")
    response.set_cookie(
        RELINK_COOKIE_NAME,
        create_relink_cookie(steamid),
        max_age=600,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/steam/relink/callback")
async def auth_steam_relink_callback(request: Request):
    old_steamid = read_relink_cookie(request.cookies.get(RELINK_COOKIE_NAME))
    if old_steamid is None:
        return RedirectResponse(f"{settings.frontend_url}/settings?relink_error=session_expired")

    new_steamid = await verify_callback(dict(request.query_params))
    if new_steamid is None:
        raise HTTPException(400, "login de Steam inválido")

    if new_steamid == old_steamid:
        resp = RedirectResponse(f"{settings.frontend_url}/settings?relink_noop=1")
        resp.delete_cookie(RELINK_COOKIE_NAME)
        return resp

    with Session(get_engine()) as s:
        old_user = s.get(User, old_steamid)
        if old_user is None:
            return RedirectResponse(
                f"{settings.frontend_url}/settings?relink_error=session_expired"
            )
        if s.get(User, new_steamid) is not None:
            return RedirectResponse(
                f"{settings.frontend_url}/settings?relink_error=steam_already_linked_elsewhere"
            )

        display_name, avatar_url, steam_background_url = await fetch_profile(new_steamid)
        now = datetime.now(UTC).isoformat()
        if s.get(Player, new_steamid) is None:
            s.add(Player(steamid=new_steamid, name=display_name))

        # Campos que sobreviven al cambio, capturados ANTES de borrar
        # old_user (el objeto queda expirado tras el delete+flush).
        real_email = old_user.email
        account_fields = {
            # Placeholder único mientras old_user (mismo email real) sigue
            # existiendo -- users.email tiene UNIQUE, así que no puede
            # haber dos filas con el mismo valor simultáneamente. Se
            # corrige al valor real más abajo, después de borrar old_user.
            "email": f"relink-pending-{new_steamid}@internal.invalid",
            "password_hash": old_user.password_hash,
            "email_verified_at": old_user.email_verified_at,
            "onboarding_completed_at": old_user.onboarding_completed_at,
            "age_bucket": old_user.age_bucket,
            "country": old_user.country,
            "acquisition_channel": old_user.acquisition_channel,
            "primary_goal": old_user.primary_goal,
            # 2FA es una propiedad de la CUENTA, no del Steam vinculado --
            # sobrevive al cambio de Steam igual que password/email.
            "totp_secret": old_user.totp_secret,
            "totp_enabled_at": old_user.totp_enabled_at,
            # session_epoch arranca en old+1 (no 0): fuerza logout de
            # cualquier cookie vieja igual, aunque de todos modos el
            # steamid de esa cookie ya no tiene fila User -- doble seguro.
            "session_epoch": old_user.session_epoch + 1,
        }

        new_user = User(
            steamid=new_steamid,
            display_name=display_name,
            avatar_url=avatar_url,
            steam_background_url=steam_background_url,
            steam_profile_synced_at=now,
            last_login_at=now,
            # Campos ESPECÍFICOS del Steam vinculado: NO se copian, el
            # steamid nuevo tiene su propio historial de autofetch/premier/
            # bot-friend, ninguno relacionado al steamid viejo.
            **account_fields,
        )
        # Orden importa por dos constraints en tensión: (a) users.email es
        # UNIQUE, así que new_user (con el email real) no puede insertarse
        # mientras old_user siga existiendo -- de ahí el placeholder de
        # arriba; (b) totp_backup_codes.steamid FK a users.steamid con
        # ondelete=CASCADE, así que re-asignarlos al steamid nuevo tiene
        # que pasar DESPUÉS de que exista new_user pero ANTES de borrar
        # old_user (si no, el cascade del delete se los lleva puestos en
        # Postgres, donde sí se aplica el FK).
        s.add(new_user)
        s.flush()
        s.query(TotpBackupCode).filter(TotpBackupCode.steamid == old_steamid).update(
            {"steamid": new_steamid}
        )
        s.delete(old_user)
        s.flush()
        new_user.email = real_email
        try:
            s.commit()
        except IntegrityError:
            s.rollback()
            return RedirectResponse(f"{settings.frontend_url}/settings?relink_error=unexpected")
        # Capturado ANTES de salir del bloque `with` -- después de
        # s.commit() (expire_on_commit=True por default) y del cierre de
        # la sesión, leer un atributo de new_user dispara un reload contra
        # una sesión ya cerrada (DetachedInstanceError).
        new_epoch = account_fields["session_epoch"]

    resp = RedirectResponse(f"{settings.frontend_url}/settings?relinked=1")
    resp.set_cookie(
        REAL_COOKIE_NAME,
        create_session_cookie(new_steamid, epoch=new_epoch),
        max_age=REAL_SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
    )
    resp.delete_cookie(RELINK_COOKIE_NAME)
    return resp


# Cantidad de códigos de respaldo generados en la activación -- cada uno de
# un solo uso (ver auth_login_totp: se marca used_at al consumirse).
_TOTP_BACKUP_CODE_COUNT = 10


def _generate_backup_code() -> str:
    """Formato humano-tipeable xxxx-xxxx (hex, no ambigüedad O/0 etc. no
    es crítico acá porque el usuario copia/pega, no transcribe a mano)."""
    raw = secrets.token_hex(4)
    return f"{raw[:4]}-{raw[4:]}"


@router.post("/totp/enroll", response_model=TotpEnrollOut)
def auth_totp_enroll(steamid: str = Depends(get_current_steamid)):
    """Fase 1 de 2 del enrollment: genera el secret y lo guarda SIN
    activar (totp_enabled_at sigue None) -- recién se activa en
    /auth/totp/activate, tras probar un código válido. Este two-phase
    evita que un enrollment interrumpido (usuario cierra la pestaña antes
    de escanear el QR) deje la cuenta en un estado roto."""
    with Session(get_engine()) as s:
        user = s.get(User, steamid)
        if user is None:
            raise HTTPException(401, "no autenticado")

        secret = pyotp.random_base32()
        user.totp_secret = secret
        s.commit()

        otpauth_uri = pyotp.TOTP(secret).provisioning_uri(
            name=user.email, issuer_name="monkeyStats"
        )

        qr_img = qrcode.make(otpauth_uri)
        buf = io.BytesIO()
        qr_img.save(buf, format="PNG")
        qr_png_base64 = base64.b64encode(buf.getvalue()).decode("ascii")

    return TotpEnrollOut(secret=secret, otpauth_uri=otpauth_uri, qr_png_base64=qr_png_base64)


@router.post("/totp/activate", response_model=TotpActivateOut)
def auth_totp_activate(
    body: TotpActivateIn,
    steamid: str = Depends(get_current_steamid),
    _origin: None = Depends(require_same_origin),
):
    with Session(get_engine()) as s:
        user = s.get(User, steamid)
        if user is None:
            raise HTTPException(401, "no autenticado")
        if user.totp_secret is None:
            raise HTTPException(400, "no hay un enrollment de 2FA en curso")
        if is_totp_locked(user):
            raise HTTPException(423, _ACCOUNT_LOCKED_MSG)

        if not pyotp.TOTP(user.totp_secret).verify(body.code, valid_window=1):
            record_totp_failure(user)
            s.commit()
            raise HTTPException(401, "código inválido")

        record_totp_success(user)
        user.totp_enabled_at = datetime.now(UTC).isoformat()

        plaintext_codes = [_generate_backup_code() for _ in range(_TOTP_BACKUP_CODE_COUNT)]
        now = datetime.now(UTC).isoformat()
        for code in plaintext_codes:
            s.add(
                TotpBackupCode(
                    steamid=steamid, code_hash=hash_password(code), used_at=None, created_at=now
                )
            )
        s.commit()

    # Los códigos en texto plano se devuelven UNA sola vez -- después solo
    # existen hasheados, no hay forma de recuperarlos.
    return TotpActivateOut(backup_codes=plaintext_codes)


@router.post("/totp/disable")
def auth_totp_disable(
    body: TotpDisableIn,
    steamid: str = Depends(get_current_steamid),
    _origin: None = Depends(require_same_origin),
):
    with Session(get_engine()) as s:
        user = s.get(User, steamid)
        if user is None:
            raise HTTPException(401, "no autenticado")
        if not verify_password(body.password, user.password_hash):
            raise HTTPException(401, "contraseña incorrecta")

        s.query(TotpBackupCode).filter(TotpBackupCode.steamid == steamid).delete()
        user.totp_secret = None
        user.totp_enabled_at = None
        user.totp_failed_attempts = 0
        user.totp_locked_until = None
        # Desactivar 2FA es un downgrade de seguridad -- invalida otras
        # sesiones igual que change-password/change-email de arriba.
        user.session_epoch += 1
        s.commit()

        resp = Response(
            content=_me_out_for_user(user).model_dump_json(), media_type="application/json"
        )
        resp.set_cookie(
            REAL_COOKIE_NAME,
            create_session_cookie(steamid, epoch=user.session_epoch),
            max_age=REAL_SESSION_MAX_AGE,
            httponly=True,
            samesite="lax",
        )
        return resp


def _totp_code_matches(session: Session, user: User, code: str) -> bool:
    """Chequeo puro (sin lockout/logging, eso lo maneja el caller): código
    TOTP actual, o -- si no matchea -- un backup code sin usar (y lo marca
    usado)."""
    if pyotp.TOTP(user.totp_secret).verify(code, valid_window=1):
        return True
    backup_codes = (
        session.query(TotpBackupCode)
        .filter(TotpBackupCode.steamid == user.steamid, TotpBackupCode.used_at.is_(None))
        .all()
    )
    for backup in backup_codes:
        if verify_password(code, backup.code_hash):
            backup.used_at = datetime.now(UTC).isoformat()
            return True
    return False


@router.post("/login/totp", response_model=MeOut)
def auth_login_totp(body: LoginTotpIn, request: Request):
    with Session(get_engine()) as s:
        enforce_rate_limit(s, "totp_login", _client_ip(request), window_seconds=900, max_count=20)

        steamid = read_mfa_pending_cookie(request.cookies.get(MFA_PENDING_COOKIE_NAME))
        if steamid is None:
            raise HTTPException(401, "no hay un login pendiente de segundo factor")

        user = s.get(User, steamid)
        if user is None or user.totp_enabled_at is None or user.totp_secret is None:
            raise HTTPException(401, "no autenticado")
        if is_totp_locked(user):
            _log_login_event(
                s,
                steamid=steamid,
                email=user.email,
                request=request,
                success=False,
                reason="locked",
            )
            raise HTTPException(423, _ACCOUNT_LOCKED_MSG)

        valid = _totp_code_matches(s, user, body.code)

        if not valid:
            record_totp_failure(user)
            _log_login_event(
                s,
                steamid=steamid,
                email=user.email,
                request=request,
                success=False,
                reason="totp_bad_code",
            )
            s.commit()
            raise HTTPException(401, "código inválido")

        record_totp_success(user)
        _maybe_notify_new_login(s, user, request)
        _log_login_event(
            s, steamid=steamid, email=user.email, request=request, success=True, reason="ok"
        )
        s.commit()

        resp = Response(
            content=_me_out_for_user(user).model_dump_json(), media_type="application/json"
        )
        resp.set_cookie(
            REAL_COOKIE_NAME,
            create_session_cookie(steamid, epoch=user.session_epoch),
            max_age=REAL_SESSION_MAX_AGE,
            httponly=True,
            samesite="lax",
        )
        resp.delete_cookie(MFA_PENDING_COOKIE_NAME)
        return resp


@router.post("/desktop-login", response_model=DesktopLoginOut)
def auth_desktop_login(body: DesktopLoginIn, request: Request) -> DesktopLoginOut:
    """Login para el overlay de escritorio (ver app/): mismo email+password
    que la web, pero en vez de cookie de sesión devuelve un token de API
    (ver api_tokens.py) -- el overlay es un proceso aparte, no puede
    sostener la cookie de sesión del navegador. Sin cookie pending
    intermedia para el segundo factor (a diferencia de /auth/login +
    /auth/login/totp): acá el código, si hace falta, se manda en el mismo
    request que la password."""
    email = normalize_email(body.email)

    with Session(get_engine()) as s:
        enforce_rate_limit(s, "desktop_login", _client_ip(request), window_seconds=900, max_count=20)

        user = s.query(User).filter(User.email == email).first()
        if user is None:
            # Cubre tanto "no existe" como "todavía es un pending sin
            # vincular Steam" (ese caso no tiene steamid, no puede tener
            # token) -- mismo mensaje que un login con password incorrecta,
            # para no filtrar cuál de los dos es.
            raise HTTPException(401, "credenciales inválidas")

        if is_locked(user):
            _log_login_event(
                s, steamid=user.steamid, email=email, request=request, success=False, reason="locked"
            )
            raise HTTPException(423, _ACCOUNT_LOCKED_MSG)

        if not verify_password(body.password, user.password_hash):
            record_login_failure(user)
            _log_login_event(
                s,
                steamid=user.steamid,
                email=email,
                request=request,
                success=False,
                reason="bad_password",
            )
            s.commit()
            raise HTTPException(401, "credenciales inválidas")
        record_login_success(user)

        if user.totp_enabled_at is not None:
            if not body.totp_code:
                s.commit()
                return DesktopLoginOut(mfa_required=True)

            if is_totp_locked(user):
                _log_login_event(
                    s,
                    steamid=user.steamid,
                    email=email,
                    request=request,
                    success=False,
                    reason="locked",
                )
                raise HTTPException(423, _ACCOUNT_LOCKED_MSG)

            if not _totp_code_matches(s, user, body.totp_code):
                record_totp_failure(user)
                _log_login_event(
                    s,
                    steamid=user.steamid,
                    email=email,
                    request=request,
                    success=False,
                    reason="totp_bad_code",
                )
                s.commit()
                raise HTTPException(401, "código inválido")
            record_totp_success(user)

        active_tokens = (
            s.query(ApiToken)
            .filter(ApiToken.steamid == user.steamid, ApiToken.revoked_at.is_(None))
            .count()
        )
        if active_tokens >= MAX_TOKENS_PER_USER:
            raise HTTPException(
                409,
                f"máximo {MAX_TOKENS_PER_USER} tokens activos -- revocá alguno viejo desde "
                "monkeyStats → Configuración → App de escritorio",
            )

        _maybe_notify_new_login(s, user, request)
        _log_login_event(
            s, steamid=user.steamid, email=email, request=request, success=True, reason="desktop"
        )
        s.commit()

        row, raw = create_token(user.steamid, "Overlay de escritorio")
        return DesktopLoginOut(mfa_required=False, token=raw, token_prefix=row.token_prefix)


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


@router.get("/login-history", response_model=LoginHistoryResponse)
def auth_login_history(steamid: str = Depends(get_current_steamid)):
    with Session(get_engine()) as s:
        events = (
            s.query(LoginEvent)
            .filter(LoginEvent.steamid == steamid)
            .order_by(LoginEvent.occurred_at.desc())
            .limit(20)
            .all()
        )
        return LoginHistoryResponse(
            events=[
                LoginHistoryEntry(
                    occurred_at=e.occurred_at,
                    ip=e.ip,
                    user_agent=e.user_agent,
                    success=e.success,
                    reason=e.reason,
                )
                for e in events
            ]
        )


@router.post("/logout")
def auth_logout():

    resp = Response(content='{"ok": true}', media_type="application/json")
    resp.delete_cookie(REAL_COOKIE_NAME)
    resp.delete_cookie(PENDING_COOKIE_NAME)
    return resp


@router.post("/logout-all")
def auth_logout_all(steamid: str = Depends(get_current_steamid)):
    """Invalida todas las cookies de sesión emitidas hasta ahora (bumpea
    users.session_epoch) y reemite una cookie nueva para el dispositivo que
    ejecuta la acción -- así ese dispositivo no se desloguea a sí mismo,
    solo los demás."""
    with Session(get_engine()) as s:
        user = s.get(User, steamid)
        if user is None:
            raise HTTPException(401, "no autenticado")
        user.session_epoch += 1
        s.commit()
        new_epoch = user.session_epoch

    resp = Response(content='{"ok": true}', media_type="application/json")
    resp.set_cookie(
        REAL_COOKIE_NAME,
        create_session_cookie(steamid, epoch=new_epoch),
        max_age=REAL_SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
    )
    return resp
