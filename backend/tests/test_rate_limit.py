"""Test de rate_limit.py: ventana fija en DB (rate_limit_buckets), lockout
de cuenta. Solo se ejercita el dialecto SQLite (el único disponible en
dev/CI) -- la rama Postgres del upsert se verifica manualmente contra
Postgres real, ver Etapa 10 del plan."""

from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy.orm import Session

from cs2tracker.db import AccountSignup, Player, User
from cs2tracker.db.session import init_db
from cs2tracker.rate_limit import (
    check_and_increment,
    is_locked,
    record_login_failure,
    record_login_success,
)


@pytest.fixture()
def session(tmp_path):
    engine = init_db(f"sqlite:///{tmp_path}/t.sqlite")
    with Session(engine) as s:
        yield s


def test_check_and_increment_respeta_el_umbral(session):
    for _ in range(3):
        assert check_and_increment(session, "test_scope", "1.2.3.4", 60, max_count=3) is True
    assert check_and_increment(session, "test_scope", "1.2.3.4", 60, max_count=3) is False


def test_check_and_increment_scopes_distintos_no_interfieren(session):
    for _ in range(3):
        check_and_increment(session, "scope_a", "1.2.3.4", 60, max_count=3)
    # mismo key, scope distinto -> contador propio
    assert check_and_increment(session, "scope_b", "1.2.3.4", 60, max_count=3) is True


def test_check_and_increment_keys_distintos_no_interfieren(session):
    for _ in range(3):
        check_and_increment(session, "test_scope", "1.2.3.4", 60, max_count=3)
    assert check_and_increment(session, "test_scope", "5.6.7.8", 60, max_count=3) is True


def test_check_and_increment_rollover_de_ventana(session, monkeypatch):
    """Al saltar a la ventana siguiente el contador debe resetearse --
    monkeypatchea rate_limit.datetime.now() con una subclase congelada en
    vez de mockear el módulo datetime completo."""
    import cs2tracker.rate_limit as rl

    real_datetime = rl.datetime

    class Frozen(real_datetime):
        _now = real_datetime(2026, 1, 1, tzinfo=rl.UTC)

        @classmethod
        def now(cls, tz=None):
            return cls._now

    monkeypatch.setattr(rl, "datetime", Frozen)

    for _ in range(3):
        assert check_and_increment(session, "scope_roll", "9.9.9.9", 60, max_count=3) is True
    assert check_and_increment(session, "scope_roll", "9.9.9.9", 60, max_count=3) is False

    Frozen._now = Frozen._now + timedelta(seconds=61)
    assert check_and_increment(session, "scope_roll", "9.9.9.9", 60, max_count=3) is True


# --- lockout ---------------------------------------------------------------


def _make_user(session):
    session.add(Player(steamid="1", name="Ana"))
    user = User(
        steamid="1",
        email="ana@test.local",
        password_hash="x",
        email_verified_at="2026-01-01T00:00:00",
    )
    session.add(user)
    session.commit()
    return user


def test_record_login_failure_bloquea_tras_el_maximo(session):
    user = _make_user(session)
    for _ in range(4):
        record_login_failure(user)
        assert is_locked(user) is False
    record_login_failure(user)
    assert is_locked(user) is True


def test_record_login_success_resetea_el_contador(session):
    user = _make_user(session)
    for _ in range(4):
        record_login_failure(user)
    record_login_success(user)
    assert user.failed_login_attempts == 0
    assert user.locked_until is None
    assert is_locked(user) is False


def test_is_locked_funciona_tambien_para_pending(session):
    pending = AccountSignup(
        email="pending@test.local",
        password_hash="x",
        email_verified_at=None,
        created_at="2026-01-01T00:00:00",
    )
    session.add(pending)
    session.commit()
    for _ in range(5):
        record_login_failure(pending)
    assert is_locked(pending) is True
