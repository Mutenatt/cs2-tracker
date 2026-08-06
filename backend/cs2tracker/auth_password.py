"""
Login por email+contraseña, y el estado intermedio "pending" (cuenta creada,
Steam todavía no vinculado -- ver db/models.py::AccountSignup). Separado de
auth.py a propósito: ese módulo es Steam-only por diseño (ver su docstring,
"no usa contraseñas").

Tres tipos de token firmado (itsdangerous), cada uno con su propio salt
derivado del mismo CS2_SESSION_SECRET: un salt distinto deriva una clave de
firma HMAC distinta, así que un token de un tipo NUNCA puede pasar la
verificación como si fuera de otro tipo, aunque el payload sea compatible
(defensa en profundidad ante un futuro bug de código que lea el token
equivocado).
"""

from __future__ import annotations

import re
import secrets
from functools import cache

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import HTTPException, Request
from itsdangerous import BadSignature, URLSafeTimedSerializer

from cs2tracker.config import settings

PENDING_COOKIE_NAME = "cs2_pending_session"
PENDING_SESSION_MAX_AGE = 7 * 24 * 3600  # 7 días: tiempo de sobra para verificar+vincular Steam

RELINK_COOKIE_NAME = "cs2_steam_relink_pending"
RELINK_MAX_AGE = 10 * 60  # 10 min: acción sensible, ventana corta a propósito

MFA_PENDING_COOKIE_NAME = "cs2_mfa_pending"
MFA_PENDING_MAX_AGE = 10 * 60  # 10 min para completar el segundo paso (código TOTP)

EMAIL_VERIFY_MAX_AGE = 48 * 3600  # 48h
PASSWORD_RESET_MAX_AGE = 3600  # 1h: acción sensible, vida corta a propósito

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# Mismo criterio que auth.py: sin CS2_SESSION_SECRET, se genera uno al
# arrancar el proceso (invalida sesiones existentes en cada restart, nunca
# hay un secreto débil hardcodeado).
_session_secret = settings.session_secret or secrets.token_hex(32)

_ph = PasswordHasher()


@cache
def _serializer(salt: str) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(_session_secret, salt=salt)


def normalize_email(email: str) -> str:
    return email.strip().lower()


def is_valid_email(email: str) -> bool:
    return bool(_EMAIL_RE.match(email))


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _ph.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def create_pending_cookie(pending_id: int) -> str:
    return _serializer("cs2tracker-pending-session").dumps({"pending_id": pending_id})


def read_pending_cookie(value: str | None) -> int | None:
    if not value:
        return None
    try:
        data = _serializer("cs2tracker-pending-session").loads(
            value, max_age=PENDING_SESSION_MAX_AGE
        )
    except BadSignature:
        return None
    return data.get("pending_id")


def get_current_pending_id(request: Request) -> int:
    pending_id = read_pending_cookie(request.cookies.get(PENDING_COOKIE_NAME))
    if pending_id is None:
        raise HTTPException(401, "no hay una sesión pendiente activa")
    return pending_id


def get_current_pending_id_optional(request: Request) -> int | None:
    return read_pending_cookie(request.cookies.get(PENDING_COOKIE_NAME))


def create_relink_cookie(old_steamid: str) -> str:
    """Guarda el steamid ACTUAL mientras se autentica el steamid nuevo vía
    Steam OpenID (ver api/account.py::auth_steam_relink_start/callback)."""
    return _serializer("cs2tracker-steam-relink").dumps({"old_steamid": old_steamid})


def read_relink_cookie(value: str | None) -> str | None:
    if not value:
        return None
    try:
        data = _serializer("cs2tracker-steam-relink").loads(value, max_age=RELINK_MAX_AGE)
    except BadSignature:
        return None
    return data.get("old_steamid")


def create_mfa_pending_cookie(steamid: str) -> str:
    """Emitida por /auth/login en vez de la cookie real cuando la cuenta
    tiene 2FA activo -- solo alcanza para llegar a /auth/login/totp, no
    para acceder a ningún endpoint autenticado (get_current_steamid lee la
    cookie REAL, cs2_session, nunca esta)."""
    return _serializer("cs2tracker-mfa-pending").dumps({"steamid": steamid})


def read_mfa_pending_cookie(value: str | None) -> str | None:
    if not value:
        return None
    try:
        data = _serializer("cs2tracker-mfa-pending").loads(value, max_age=MFA_PENDING_MAX_AGE)
    except BadSignature:
        return None
    return data.get("steamid")


def create_email_verify_token(pending_id: int) -> str:
    return _serializer("cs2tracker-email-verify").dumps({"pending_id": pending_id})


def read_email_verify_token(token: str) -> int | None:
    try:
        data = _serializer("cs2tracker-email-verify").loads(token, max_age=EMAIL_VERIFY_MAX_AGE)
    except BadSignature:
        return None
    return data.get("pending_id")


def create_password_reset_token(kind: str, id_: str) -> str:
    """kind: "user" (steamid) o "pending" (id de AccountSignup)."""
    return _serializer("cs2tracker-password-reset").dumps({"kind": kind, "id": id_})


def read_password_reset_token(token: str) -> tuple[str, str] | None:
    try:
        data = _serializer("cs2tracker-password-reset").loads(token, max_age=PASSWORD_RESET_MAX_AGE)
    except BadSignature:
        return None
    kind, id_ = data.get("kind"), data.get("id")
    if kind is None or id_ is None:
        return None
    return kind, id_


def create_email_change_token(steamid: str, new_email: str) -> str:
    return _serializer("cs2tracker-email-change").dumps(
        {"steamid": steamid, "new_email": new_email}
    )


def read_email_change_token(token: str) -> tuple[str, str] | None:
    try:
        data = _serializer("cs2tracker-email-change").loads(token, max_age=EMAIL_VERIFY_MAX_AGE)
    except BadSignature:
        return None
    steamid, new_email = data.get("steamid"), data.get("new_email")
    if steamid is None or new_email is None:
        return None
    return steamid, new_email
