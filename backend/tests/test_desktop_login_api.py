"""Test de POST /auth/desktop-login: login del overlay de escritorio (ver
app/) con el mismo email+password de la cuenta monkeyStats, pero devolviendo
un token de API (ver api_tokens.py) en vez de cookie de sesión."""

from __future__ import annotations

from datetime import UTC, datetime

import pyotp
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from cs2tracker.api.main import app
from cs2tracker.api_tokens import create_token
from cs2tracker.auth_password import hash_password
from cs2tracker.db import AccountSignup, Player, User
from cs2tracker.db.session import init_db


@pytest.fixture()
def engine(tmp_path):
    return init_db(f"sqlite:///{tmp_path}/t.sqlite")


@pytest.fixture()
def client(engine):
    return TestClient(app)


def _make_user(
    engine, *, steamid="76561198000000300", email="user@test.local", password="password123"
):
    with Session(engine) as s:
        s.add(Player(steamid=steamid, name="Ana"))
        s.add(
            User(
                steamid=steamid,
                display_name="Ana",
                email=email,
                password_hash=hash_password(password),
                email_verified_at=datetime.now(UTC).isoformat(),
            )
        )
        s.commit()
    return steamid


def _make_pending(engine, *, email="pendiente@test.local", password="password123"):
    with Session(engine) as s:
        s.add(
            AccountSignup(
                email=email,
                password_hash=hash_password(password),
                email_verified_at=datetime.now(UTC).isoformat(),
                created_at=datetime.now(UTC).isoformat(),
            )
        )
        s.commit()


def test_desktop_login_feliz_devuelve_token_utilizable(client, engine):
    _make_user(engine, email="user@test.local", password="password123")
    r = client.post(
        "/auth/desktop-login", json={"email": "user@test.local", "password": "password123"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["mfa_required"] is False
    assert body["token"].startswith("cst_")

    # El token devuelto debe servir de verdad como Bearer contra la API
    # (get_current_actor, a diferencia de get_current_steamid que es
    # cookie-only -- ver auth.py).
    r2 = client.get("/lineups/maps", headers={"Authorization": f"Bearer {body['token']}"})
    assert r2.status_code == 200


def test_desktop_login_password_incorrecta_401(client, engine):
    _make_user(engine, email="user@test.local", password="password123")
    r = client.post(
        "/auth/desktop-login", json={"email": "user@test.local", "password": "incorrecta"}
    )
    assert r.status_code == 401


def test_desktop_login_email_inexistente_401(client, engine):
    r = client.post(
        "/auth/desktop-login", json={"email": "no-existe@test.local", "password": "cualquiera"}
    )
    assert r.status_code == 401


def test_desktop_login_pending_sin_vincular_401(client, engine):
    """Un signup que todavía no vinculó Steam no tiene steamid -- no puede
    tener token, a diferencia de /auth/login que sí acepta pending."""
    _make_pending(engine, email="pendiente@test.local", password="password123")
    r = client.post(
        "/auth/desktop-login", json={"email": "pendiente@test.local", "password": "password123"}
    )
    assert r.status_code == 401


def test_desktop_login_con_totp_pide_codigo_y_no_da_token(client, engine):
    steamid = _make_user(engine, email="totp@test.local", password="password123")
    with Session(engine) as s:
        user = s.get(User, steamid)
        secret = pyotp.random_base32()
        user.totp_secret = secret
        user.totp_enabled_at = datetime.now(UTC).isoformat()
        s.commit()

    r = client.post(
        "/auth/desktop-login", json={"email": "totp@test.local", "password": "password123"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["mfa_required"] is True
    assert body["token"] is None

    code = pyotp.TOTP(secret).now()
    r2 = client.post(
        "/auth/desktop-login",
        json={"email": "totp@test.local", "password": "password123", "totp_code": code},
    )
    assert r2.status_code == 200
    body2 = r2.json()
    assert body2["mfa_required"] is False
    assert body2["token"].startswith("cst_")


def test_desktop_login_con_totp_codigo_incorrecto_401(client, engine):
    steamid = _make_user(engine, email="totp2@test.local", password="password123")
    with Session(engine) as s:
        user = s.get(User, steamid)
        user.totp_secret = pyotp.random_base32()
        user.totp_enabled_at = datetime.now(UTC).isoformat()
        s.commit()

    r = client.post(
        "/auth/desktop-login",
        json={"email": "totp2@test.local", "password": "password123", "totp_code": "000000"},
    )
    assert r.status_code == 401


def test_desktop_login_maximo_tokens_activos_409(client, engine):
    steamid = _make_user(engine, email="lleno@test.local", password="password123")
    for i in range(10):
        create_token(steamid, f"token {i}")

    r = client.post(
        "/auth/desktop-login", json={"email": "lleno@test.local", "password": "password123"}
    )
    assert r.status_code == 409
