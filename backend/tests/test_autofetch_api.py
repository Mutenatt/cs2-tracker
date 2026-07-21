"""Endpoints de vinculación del auto-fetch (link/unlink/status)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from cs2tracker.api import autofetch
from cs2tracker.api.main import app
from cs2tracker.auth import COOKIE_NAME, create_session_cookie
from cs2tracker.db import Player, User
from cs2tracker.db.session import init_db

STEAMID = "76561198000000000"
SHARECODE = "CSGO-GADqf-jjyJ8-cSP2r-smZRo-TO2xK"
AUTH_CODE = "AAAA-AAAAA-AAAA"


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = init_db(f"sqlite:///{tmp_path}/t.sqlite")
    with Session(engine) as s:
        s.add(Player(steamid=STEAMID, name="Ana"))
        s.add(User(steamid=STEAMID, display_name="Ana", avatar_url=None))
        s.commit()
    monkeypatch.setattr(autofetch.settings, "steam_api_key", "clave-de-test")
    c = TestClient(app)
    c.cookies.set(COOKIE_NAME, create_session_cookie(STEAMID))
    return c


def test_sin_sesion_401(client):
    client.cookies.delete(COOKIE_NAME)
    assert client.get("/autofetch/status").status_code == 401
    assert (
        client.post("/autofetch/link", json={"auth_code": "x", "sharecode": "y"}).status_code == 401
    )


def test_status_inicial_no_vinculado(client):
    r = client.get("/autofetch/status")
    assert r.status_code == 200
    assert r.json()["linked"] is False


def test_link_ok(client, monkeypatch):
    monkeypatch.setattr(autofetch, "get_next_sharecode", lambda *a, **kw: None)
    r = client.post("/autofetch/link", json={"auth_code": AUTH_CODE, "sharecode": SHARECODE})
    assert r.status_code == 200
    body = r.json()
    assert body["linked"] is True
    assert body["status"] == "active"
    assert body["last_sharecode"] == SHARECODE

    r2 = client.get("/autofetch/status")
    assert r2.json()["linked"] is True


def test_link_acepta_url_steam_entera(client, monkeypatch):
    monkeypatch.setattr(autofetch, "get_next_sharecode", lambda *a, **kw: None)
    url = f"steam://rungame/730/765611985248/+csgo_download_match%20{SHARECODE}"
    r = client.post("/autofetch/link", json={"auth_code": AUTH_CODE, "sharecode": url})
    assert r.status_code == 200
    assert r.json()["last_sharecode"] == SHARECODE


def test_link_auth_code_formato_invalido(client):
    r = client.post("/autofetch/link", json={"auth_code": "no-es", "sharecode": SHARECODE})
    assert r.status_code == 400


def test_link_sharecode_invalido(client):
    r = client.post("/autofetch/link", json={"auth_code": AUTH_CODE, "sharecode": "CSGO-nop"})
    assert r.status_code == 400


def test_link_steam_rechaza_auth_code(client, monkeypatch):
    def _raise(*a, **kw):
        raise autofetch.AuthCodeInvalid("403")

    monkeypatch.setattr(autofetch, "get_next_sharecode", _raise)
    r = client.post("/autofetch/link", json={"auth_code": AUTH_CODE, "sharecode": SHARECODE})
    assert r.status_code == 400


def test_link_sin_api_key_global_503(client, monkeypatch):
    monkeypatch.setattr(autofetch.settings, "steam_api_key", None)
    r = client.post("/autofetch/link", json={"auth_code": AUTH_CODE, "sharecode": SHARECODE})
    assert r.status_code == 503


def test_unlink_conserva_last_sharecode(client, monkeypatch):
    monkeypatch.setattr(autofetch, "get_next_sharecode", lambda *a, **kw: None)
    client.post("/autofetch/link", json={"auth_code": AUTH_CODE, "sharecode": SHARECODE})

    r = client.delete("/autofetch/link")
    assert r.status_code == 200
    body = r.json()
    assert body["linked"] is False
    assert body["status"] is None
    # La posición en la cadena se conserva para re-vincular sin huecos.
    assert body["last_sharecode"] == SHARECODE
