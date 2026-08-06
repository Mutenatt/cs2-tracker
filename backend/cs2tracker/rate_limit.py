"""
Rate limiting y lockout de cuenta, en DB (rate_limit_buckets) -- sin infra
externa nueva (Redis/memoria de proceso), consistente con el resto del
proyecto (cache tables reconstruibles, sin cron externo).

Ventana fija (fixed window), no sliding window/token-bucket: más simple, con
el trade-off aceptado de poder admitir algo más de tráfico que max_count
justo en el borde de una ventana -- el lockout de cuenta (record_login_failure
/is_locked) es el backstop real contra ataques de credenciales, este módulo
solo necesita frenar el volumen general.

check_and_increment hace el incremento con un único UPSERT atómico
(ON CONFLICT DO UPDATE), no un read-then-write -- así es seguro bajo
requests concurrentes sin necesitar un lock explícito.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import delete
from sqlalchemy.orm import Session

from cs2tracker.db.models import AccountSignup, RateLimitBucket, User

# Cuenta se bloquea tras esta cantidad de intentos fallidos consecutivos.
LOGIN_MAX_FAILURES = 5
# Duración del bloqueo.
LOGIN_LOCKOUT = timedelta(minutes=15)

# Probabilidad de disparar la limpieza de buckets viejos en cada llamada
# (1/200) -- barato, sin necesitar un proceso de limpieza aparte.
_CLEANUP_PROBABILITY = 1 / 200
_CLEANUP_MAX_AGE = timedelta(hours=24)


def _window_start(now: datetime, window_seconds: int) -> str:
    epoch = int(now.timestamp())
    floored = epoch - (epoch % window_seconds)
    return datetime.fromtimestamp(floored, tz=UTC).isoformat()


def _maybe_cleanup(session: Session) -> None:
    if random.random() >= _CLEANUP_PROBABILITY:
        return
    cutoff = (datetime.now(UTC) - _CLEANUP_MAX_AGE).isoformat()
    session.execute(delete(RateLimitBucket).where(RateLimitBucket.window_start < cutoff))


def check_and_increment(
    session: Session, scope: str, key: str, window_seconds: int, max_count: int
) -> bool:
    """Incrementa el contador de (scope, key, ventana-actual) atómicamente y
    devuelve si el conteo resultante sigue dentro de max_count."""
    now = datetime.now(UTC)
    window_start = _window_start(now, window_seconds)

    dialect = session.bind.dialect.name if session.bind is not None else "sqlite"
    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        stmt = pg_insert(RateLimitBucket).values(
            scope=scope, key=key, window_start=window_start, count=1
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=[
                RateLimitBucket.scope,
                RateLimitBucket.key,
                RateLimitBucket.window_start,
            ],
            set_={"count": RateLimitBucket.count + 1},
        ).returning(RateLimitBucket.count)
    else:
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        stmt = sqlite_insert(RateLimitBucket).values(
            scope=scope, key=key, window_start=window_start, count=1
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["scope", "key", "window_start"],
            set_={"count": RateLimitBucket.count + 1},
        ).returning(RateLimitBucket.count)

    count = session.execute(stmt).scalar_one()
    session.commit()

    _maybe_cleanup(session)
    session.commit()

    return count <= max_count


def enforce_rate_limit(
    session: Session, scope: str, key: str, window_seconds: int, max_count: int
) -> None:
    if not check_and_increment(session, scope, key, window_seconds, max_count):
        raise HTTPException(
            429,
            "demasiados intentos, probá de nuevo en un rato",
            headers={"Retry-After": str(window_seconds)},
        )


def is_locked(account: User | AccountSignup) -> bool:
    if account.locked_until is None:
        return False
    try:
        locked_until = datetime.fromisoformat(account.locked_until)
    except ValueError:
        return False
    return datetime.now(UTC) < locked_until


def record_login_failure(account: User | AccountSignup) -> None:
    account.failed_login_attempts += 1
    if account.failed_login_attempts >= LOGIN_MAX_FAILURES:
        account.locked_until = (datetime.now(UTC) + LOGIN_LOCKOUT).isoformat()


def record_login_success(account: User | AccountSignup) -> None:
    account.failed_login_attempts = 0
    account.locked_until = None


# Contador separado del de login-password: un fallo de TOTP significa que
# el atacante YA tiene la password (amenaza distinta), así que no comparte
# ni afecta el umbral de is_locked/record_login_failure de arriba.
TOTP_MAX_FAILURES = 5
TOTP_LOCKOUT = timedelta(minutes=15)


def is_totp_locked(user: User) -> bool:
    if user.totp_locked_until is None:
        return False
    try:
        locked_until = datetime.fromisoformat(user.totp_locked_until)
    except ValueError:
        return False
    return datetime.now(UTC) < locked_until


def record_totp_failure(user: User) -> None:
    user.totp_failed_attempts += 1
    if user.totp_failed_attempts >= TOTP_MAX_FAILURES:
        user.totp_locked_until = (datetime.now(UTC) + TOTP_LOCKOUT).isoformat()


def record_totp_success(user: User) -> None:
    user.totp_failed_attempts = 0
    user.totp_locked_until = None
