"""Test de 2FA/TOTP: enroll -> activate -> login con segundo factor,
backup codes de un solo uso, disable, lockout. pyotp es determinista dado
secret+tiempo, así que se generan códigos reales en vez de mockear."""

from __future__ import annotations

from datetime import UTC, datetime

import pyotp
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from cs2tracker.api.main import app
from cs2tracker.auth import COOKIE_NAME, create_session_cookie
from cs2tracker.auth_password import hash_password
from cs2tracker.db import Player, User
from cs2tracker.db.session import init_db


@pytest.fixture()
def engine(tmp_path):
    return init_db(f"sqlite:///{tmp_path}/t.sqlite")


@pytest.fixture()
def client(engine):
    return TestClient(app)


def _make_user(
    engine, *, steamid="76561198000000200", email="totp@test.local", password="password123"
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


def _authed_client(client, steamid):
    client.cookies.set(COOKIE_NAME, create_session_cookie(steamid, epoch=0))
    return client


def _enroll_and_activate(client, engine, steamid):
    """Helper: hace el enroll y activate reales, devuelve (secret, backup_codes)."""
    r = client.post("/auth/totp/enroll")
    assert r.status_code == 200
    secret = r.json()["secret"]

    code = pyotp.TOTP(secret).now()
    r2 = client.post("/auth/totp/activate", json={"code": code})
    assert r2.status_code == 200
    return secret, r2.json()["backup_codes"]


def test_totp_enroll_requiere_sesion(client):
    r = client.post("/auth/totp/enroll")
    assert r.status_code == 401


def test_totp_enroll_devuelve_secret_y_qr(client, engine):
    steamid = _make_user(engine)
    _authed_client(client, steamid)
    r = client.post("/auth/totp/enroll")
    assert r.status_code == 200
    body = r.json()
    assert len(body["secret"]) >= 16
    assert body["otpauth_uri"].startswith("otpauth://totp/")
    assert len(body["qr_png_base64"]) > 0

    with Session(engine) as s:
        user = s.get(User, steamid)
        assert user.totp_secret == body["secret"]
        assert user.totp_enabled_at is None  # todavía no activado


def test_totp_activate_codigo_invalido_401(client, engine):
    steamid = _make_user(engine)
    _authed_client(client, steamid)
    client.post("/auth/totp/enroll")
    r = client.post("/auth/totp/activate", json={"code": "000000"})
    assert r.status_code == 401

    with Session(engine) as s:
        user = s.get(User, steamid)
        assert user.totp_enabled_at is None


def test_totp_activate_feliz_devuelve_10_backup_codes(client, engine):
    steamid = _make_user(engine)
    _authed_client(client, steamid)
    _, backup_codes = _enroll_and_activate(client, engine, steamid)
    assert len(backup_codes) == 10
    assert len(set(backup_codes)) == 10  # todos distintos

    with Session(engine) as s:
        user = s.get(User, steamid)
        assert user.totp_enabled_at is not None


def test_login_con_2fa_activo_no_emite_cookie_real(client, engine):
    steamid = _make_user(engine, email="mfa@test.local", password="password123")
    _authed_client(client, steamid)
    _enroll_and_activate(client, engine, steamid)
    client.cookies.delete(COOKIE_NAME)

    r = client.post("/auth/login", json={"email": "mfa@test.local", "password": "password123"})
    assert r.status_code == 200
    body = r.json()
    assert body["mfa_required"] is True
    assert body["me"] is None
    assert COOKIE_NAME not in r.cookies

    # sin haber completado el segundo paso, /auth/me sigue sin sesión
    assert client.get("/auth/me").status_code == 401


def test_login_totp_codigo_correcto_completa_el_login(client, engine):
    steamid = _make_user(engine, email="mfa2@test.local", password="password123")
    _authed_client(client, steamid)
    secret, _ = _enroll_and_activate(client, engine, steamid)
    client.cookies.delete(COOKIE_NAME)

    client.post("/auth/login", json={"email": "mfa2@test.local", "password": "password123"})
    code = pyotp.TOTP(secret).now()
    r = client.post("/auth/login/totp", json={"code": code})
    assert r.status_code == 200
    assert r.json()["steamid"] == steamid
    assert COOKIE_NAME in r.cookies

    assert client.get("/auth/me").status_code == 200


def test_login_totp_codigo_incorrecto_401(client, engine):
    steamid = _make_user(engine, email="mfa3@test.local", password="password123")
    _authed_client(client, steamid)
    _enroll_and_activate(client, engine, steamid)
    client.cookies.delete(COOKIE_NAME)

    client.post("/auth/login", json={"email": "mfa3@test.local", "password": "password123"})
    r = client.post("/auth/login/totp", json={"code": "000000"})
    assert r.status_code == 401


def test_login_totp_bloquea_tras_5_fallos(client, engine):
    steamid = _make_user(engine, email="mfa4@test.local", password="password123")
    _authed_client(client, steamid)
    _enroll_and_activate(client, engine, steamid)
    client.cookies.delete(COOKIE_NAME)

    client.post("/auth/login", json={"email": "mfa4@test.local", "password": "password123"})
    for _ in range(5):
        client.post("/auth/login/totp", json={"code": "000000"})
    r = client.post("/auth/login/totp", json={"code": "000000"})
    assert r.status_code == 423


def test_login_totp_backup_code_de_un_solo_uso(client, engine):
    steamid = _make_user(engine, email="mfa5@test.local", password="password123")
    _authed_client(client, steamid)
    _, backup_codes = _enroll_and_activate(client, engine, steamid)
    client.cookies.delete(COOKIE_NAME)

    client.post("/auth/login", json={"email": "mfa5@test.local", "password": "password123"})
    r = client.post("/auth/login/totp", json={"code": backup_codes[0]})
    assert r.status_code == 200

    # el mismo backup code no puede reusarse
    client.cookies.delete(COOKIE_NAME)
    client.post("/auth/login", json={"email": "mfa5@test.local", "password": "password123"})
    r2 = client.post("/auth/login/totp", json={"code": backup_codes[0]})
    assert r2.status_code == 401


def test_totp_disable_requiere_password_y_bumpea_epoch(client, engine):
    steamid = _make_user(engine, email="mfa6@test.local", password="password123")
    _authed_client(client, steamid)
    _enroll_and_activate(client, engine, steamid)

    other_client = TestClient(app)
    other_client.cookies.set(COOKIE_NAME, create_session_cookie(steamid, epoch=0))
    assert other_client.get("/auth/me").status_code == 200

    r = client.post("/auth/totp/disable", json={"password": "incorrecta"})
    assert r.status_code == 401

    r2 = client.post("/auth/totp/disable", json={"password": "password123"})
    assert r2.status_code == 200
    assert r2.json()["totp_enabled"] is False

    # la sesión desde otro dispositivo quedó invalidada (epoch bump)
    assert other_client.get("/auth/me").status_code == 401

    with Session(engine) as s:
        user = s.get(User, steamid)
        assert user.totp_secret is None
        assert user.totp_enabled_at is None

    # login ya no pide 2FA
    r3 = client.post("/auth/login", json={"email": "mfa6@test.local", "password": "password123"})
    assert r3.json()["mfa_required"] is False
