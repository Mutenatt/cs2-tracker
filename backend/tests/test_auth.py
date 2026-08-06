"""Test de auth: login con Steam OpenID + sesión por cookie firmada.

verify_callback/fetch_profile hablan con steamcommunity.com/api.steampowered.com
-- se mockea httpx.AsyncClient en vez de pegarle a la red real.
"""

import asyncio
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from cs2tracker.api.main import app
from cs2tracker.auth import (
    COOKIE_NAME,
    build_login_url,
    create_session_cookie,
    parse_profile_background_url,
    read_session_cookie,
    verify_callback,
)
from cs2tracker.auth_password import PENDING_COOKIE_NAME, create_pending_cookie
from cs2tracker.db import AccountSignup, User
from cs2tracker.db.session import init_db

VALID_CLAIMED_ID = "https://steamcommunity.com/openid/id/76561198000000000"


class _FakeResponse:
    def __init__(self, text: str, status_code: int = 200):
        self.text = text
        self.status_code = status_code


class _FakeAsyncClient:
    def __init__(self, is_valid: bool):
        self._is_valid = is_valid

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, data=None):
        return _FakeResponse(f"is_valid:{'true' if self._is_valid else 'false'}\n")


def test_build_login_url_apunta_a_steam_con_return_to():
    url = build_login_url()
    parsed = urlparse(url)
    assert parsed.netloc == "steamcommunity.com"
    qs = parse_qs(parsed.query)
    assert qs["openid.mode"] == ["checkid_setup"]
    assert qs["openid.return_to"][0].endswith("/auth/callback")


def test_verify_callback_claimed_id_invalido_no_llama_a_steam():
    steamid = asyncio.run(verify_callback({"openid.claimed_id": "no-es-una-url-de-steam"}))
    assert steamid is None


def test_verify_callback_valido(monkeypatch):
    monkeypatch.setattr(
        "cs2tracker.auth.httpx.AsyncClient", lambda **kw: _FakeAsyncClient(is_valid=True)
    )
    steamid = asyncio.run(verify_callback({"openid.claimed_id": VALID_CLAIMED_ID}))
    assert steamid == "76561198000000000"


def test_verify_callback_rechazado_por_steam(monkeypatch):
    monkeypatch.setattr(
        "cs2tracker.auth.httpx.AsyncClient", lambda **kw: _FakeAsyncClient(is_valid=False)
    )
    steamid = asyncio.run(verify_callback({"openid.claimed_id": VALID_CLAIMED_ID}))
    assert steamid is None


def test_parse_profile_background_url_extrae_url_de_html():
    html = (
        '<html><head><script>g_rgProfileData={"steamid":"76561198000000000"}</script></head>'
        '<body><div class="profile_background" style="background-image:url(https://steamcommunity-a.akamaihd.net/steamcommunity/public/images/profile_backgrounds/abc123.jpg)"></div></body></html>'
    )
    assert parse_profile_background_url(html) == (
        "https://steamcommunity-a.akamaihd.net/steamcommunity/public/images/profile_backgrounds/abc123.jpg"
    )


def test_parse_profile_background_url_acepta_background_shorthand_y_url_relativa():
    html = (
        "<style>.profile_page_background { background: url('//steamcommunity-a.akamaihd.net/"
        "steamcommunity/public/images/profile_backgrounds/abc123.jpg') center / cover; }</style>"
    )
    assert parse_profile_background_url(html) == (
        "https://steamcommunity-a.akamaihd.net/steamcommunity/public/images/profile_backgrounds/abc123.jpg"
    )


def test_session_cookie_roundtrip():
    cookie = create_session_cookie("76561198000000000", epoch=3)
    assert read_session_cookie(cookie) == ("76561198000000000", 3)


def test_session_cookie_sin_epoch_en_payload_se_interpreta_como_0():
    """Cookie firmada antes de que existiera el campo "epoch" en el payload
    (formato pre-deploy de session_epoch) -- no debe romper, se lee como
    epoch=0, que es también el default de users.session_epoch."""
    from itsdangerous import URLSafeTimedSerializer

    from cs2tracker.auth import _session_secret

    legacy_serializer = URLSafeTimedSerializer(_session_secret, salt="cs2tracker-session")
    legacy_cookie = legacy_serializer.dumps({"steamid": "76561198000000000"})
    assert read_session_cookie(legacy_cookie) == ("76561198000000000", 0)


def test_session_cookie_invalida():
    assert read_session_cookie("esto-no-es-una-cookie-valida") is None
    assert read_session_cookie(None) is None


@pytest.fixture()
def client(tmp_path):
    engine = init_db(f"sqlite:///{tmp_path}/t.sqlite")
    with Session(engine) as s:
        from cs2tracker.db import Player

        s.add(Player(steamid="76561198000000000", name="Ana"))
        s.add(
            User(
                steamid="76561198000000000",
                display_name="Ana",
                avatar_url=None,
                email="ana@test.local",
                password_hash="x",
                email_verified_at="2026-01-01T00:00:00",
                # "Recién sincronizado" -- sin esto, /auth/me lo considera
                # stale y dispara un fetch_profile real (ver
                # test_auth_me_refresca_steam_profile_stale para ese caso,
                # mockeado).
                steam_profile_synced_at=datetime.now(UTC).isoformat(),
            )
        )
        s.commit()
    return TestClient(app)


def test_steam_link_requiere_sesion_pending(client):
    assert client.get("/auth/steam/link").status_code == 401


def test_steam_link_redirige_a_steam_con_email_verificado(client, tmp_path):
    engine = init_db(f"sqlite:///{tmp_path}/t.sqlite")
    with Session(engine) as s:
        pending = AccountSignup(
            email="nueva@test.local",
            password_hash="x",
            email_verified_at="2026-01-01T00:00:00",
            created_at="2026-01-01T00:00:00",
        )
        s.add(pending)
        s.commit()
        s.refresh(pending)
        pending_id = pending.id
    client.cookies.set(PENDING_COOKIE_NAME, create_pending_cookie(pending_id))
    r = client.get("/auth/steam/link", follow_redirects=False)
    assert r.status_code in (302, 307)
    assert "steamcommunity.com" in r.headers["location"]


def test_auth_me_sin_sesion_401(client):
    assert client.get("/auth/me").status_code == 401


def test_auth_me_con_sesion(client):
    client.cookies.set(COOKIE_NAME, create_session_cookie("76561198000000000"))
    r = client.get("/auth/me")
    assert r.status_code == 200
    assert r.json()["steamid"] == "76561198000000000"
    assert r.json()["display_name"] == "Ana"


def test_auth_me_refresca_steam_profile_stale(client, monkeypatch, tmp_path):
    """Sin sync previo (steam_profile_synced_at None), /auth/me re-scrapea el
    perfil y persiste el background nuevo -- este es el fix a "cambié el
    fondo en Steam y acá sigue siendo el mismo": ya no hace falta
    desvincular/re-vincular la cuenta para que se note."""
    engine = init_db(f"sqlite:///{tmp_path}/t.sqlite")
    with Session(engine) as s:
        user = s.get(User, "76561198000000000")
        user.steam_profile_synced_at = None
        s.commit()

    async def fake_fetch_profile(steamid):
        return (
            "Ana Nueva",
            "https://example.com/avatar.jpg",
            "https://example.com/nuevo-fondo.jpg",
        )

    monkeypatch.setattr("cs2tracker.api.account.fetch_profile", fake_fetch_profile)

    client.cookies.set(COOKIE_NAME, create_session_cookie("76561198000000000"))
    r = client.get("/auth/me")
    assert r.status_code == 200
    body = r.json()
    assert body["display_name"] == "Ana Nueva"
    assert body["steam_background_url"] == "https://example.com/nuevo-fondo.jpg"

    with Session(engine) as s:
        user = s.get(User, "76561198000000000")
        assert user.steam_background_url == "https://example.com/nuevo-fondo.jpg"
        assert user.steam_profile_synced_at is not None


def test_auth_me_no_refresca_si_ya_esta_sincronizado(client, monkeypatch):
    """Con steam_profile_synced_at reciente (fixture client), /auth/me NO
    llama a Steam -- el throttle existe para no pegarle a
    steamcommunity.com en cada carga de página."""

    async def boom(steamid):
        raise AssertionError("no debería llamar a fetch_profile todavía")

    monkeypatch.setattr("cs2tracker.api.account.fetch_profile", boom)

    client.cookies.set(COOKIE_NAME, create_session_cookie("76561198000000000"))
    r = client.get("/auth/me")
    assert r.status_code == 200
    assert r.json()["display_name"] == "Ana"


def test_auth_me_epoch_obsoleto_401(client, tmp_path):
    """Una cookie firmada con un epoch viejo (ver users.session_epoch) deja
    de ser válida en cuanto la DB bumpea el epoch del usuario -- este es el
    mecanismo de "logout en todos los dispositivos"."""
    engine = init_db(f"sqlite:///{tmp_path}/t.sqlite")
    client.cookies.set(COOKIE_NAME, create_session_cookie("76561198000000000", epoch=0))
    assert client.get("/auth/me").status_code == 200

    with Session(engine) as s:
        user = s.get(User, "76561198000000000")
        user.session_epoch = 1
        s.commit()

    assert client.get("/auth/me").status_code == 401

    client.cookies.set(COOKIE_NAME, create_session_cookie("76561198000000000", epoch=1))
    assert client.get("/auth/me").status_code == 200


def test_auth_logout_borra_la_sesion(client):
    # client.cookies.set(...) inyecta la cookie fuera del flujo normal de
    # Set-Cookie; el jar de httpx no la sobreescribe de forma confiable con
    # la respuesta de logout (a diferencia de un navegador real). Se verifica
    # directamente el contrato real: el header Set-Cookie de /auth/logout
    # instruye borrarla (Max-Age=0).
    client.cookies.set(COOKIE_NAME, create_session_cookie("76561198000000000"))
    assert client.get("/auth/me").status_code == 200
    r = client.post("/auth/logout")
    set_cookie = r.headers.get("set-cookie", "")
    assert COOKIE_NAME in set_cookie
    assert "max-age=0" in set_cookie.lower()
