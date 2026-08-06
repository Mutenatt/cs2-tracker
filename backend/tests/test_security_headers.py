"""Test de headers de seguridad (api/main.py::security_headers middleware)
y del backstop de CSRF por Origin (auth.py::require_same_origin)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from cs2tracker.api.main import app
from cs2tracker.auth import COOKIE_NAME, create_session_cookie
from cs2tracker.auth_password import hash_password
from cs2tracker.config import settings
from cs2tracker.db import Player, User
from cs2tracker.db.session import init_db


@pytest.fixture()
def engine(tmp_path):
    return init_db(f"sqlite:///{tmp_path}/t.sqlite")


@pytest.fixture()
def client(engine):
    return TestClient(app)


def test_headers_de_seguridad_presentes(client):
    r = client.get("/news/cs2")
    assert r.headers.get("Strict-Transport-Security") is not None
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert r.headers.get("Content-Security-Policy-Report-Only") is not None


def _authed(
    client, engine, steamid="76561198000000300", email="csrf@test.local", password="password123"
):
    with Session(engine) as s:
        s.add(Player(steamid=steamid, name="Ana"))
        s.add(
            User(
                steamid=steamid,
                email=email,
                password_hash=hash_password(password),
                email_verified_at=datetime.now(UTC).isoformat(),
            )
        )
        s.commit()
    client.cookies.set(COOKIE_NAME, create_session_cookie(steamid, epoch=0))
    return steamid


def test_change_password_rechaza_origin_forjado(client, engine):
    _authed(client, engine)
    r = client.post(
        "/auth/change-password",
        json={"current_password": "password123", "new_password": "nueva12345"},
        headers={"Origin": "https://evil.example.com"},
    )
    assert r.status_code == 403


def test_change_password_acepta_origin_del_frontend(client, engine):
    _authed(client, engine)
    r = client.post(
        "/auth/change-password",
        json={"current_password": "password123", "new_password": "nueva12345"},
        headers={"Origin": settings.frontend_url},
    )
    assert r.status_code == 200


def test_change_password_sin_origin_ni_referer_pasa(client, engine):
    """Sin ninguno de los dos headers (algunos clientes no-browser) no se
    bloquea acá -- limitación documentada, mitigada por SameSite=Lax."""
    _authed(client, engine)
    r = client.post(
        "/auth/change-password",
        json={"current_password": "password123", "new_password": "nueva12345"},
    )
    assert r.status_code == 200


def test_delete_account_rechaza_origin_forjado(client, engine):
    _authed(client, engine)
    r = client.post(
        "/auth/delete-account",
        json={"password": "password123"},
        headers={"Origin": "https://evil.example.com"},
    )
    assert r.status_code == 403
