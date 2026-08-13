"""Tokens personales (/account/tokens) y su uso vía Authorization: Bearer
en endpoints normales (ver auth.get_current_actor) -- lo que usa el overlay
de escritorio para autenticarse sin la cookie de sesión del navegador."""

import pytest
from fastapi.testclient import TestClient

from cs2tracker.api.main import app
from cs2tracker.api.tokens import MAX_TOKENS_PER_USER
from cs2tracker.auth import COOKIE_NAME, create_session_cookie
from cs2tracker.db import Lineup, Player, User
from cs2tracker.db.session import init_db

STEAMID = "76561198000000000"
OTHER_STEAMID = "76561198000000001"


@pytest.fixture()
def client(tmp_path):
    from sqlalchemy.orm import Session

    engine = init_db(f"sqlite:///{tmp_path}/t.sqlite")
    with Session(engine) as s:
        for sid in (STEAMID, OTHER_STEAMID):
            s.add(Player(steamid=sid, name="Ana"))
            s.add(
                User(
                    steamid=sid,
                    email=f"{sid}@test.local",
                    password_hash="x",
                    email_verified_at="2026-01-01T00:00:00",
                )
            )
        s.add(
            Lineup(
                map="de_mirage",
                category="smoke",
                team="T",
                label="Jungle",
                x=0.17,
                y=0.56,
                video_url="/lineups/de_mirage/t/smoke-jungle.mp4",
                created_at="2026-01-01T00:00:00",
            )
        )
        s.commit()
    c = TestClient(app)
    c.cookies.set(COOKIE_NAME, create_session_cookie(STEAMID))
    return c


def test_crear_token_devuelve_secreto_una_vez(client):
    r = client.post("/account/tokens", json={"name": "Overlay"})
    assert r.status_code == 200
    body = r.json()
    assert body["token"].startswith("cst_")
    assert body["token_prefix"] == body["token"][:10]
    assert body["name"] == "Overlay"


def test_nombre_vacio_400(client):
    assert client.post("/account/tokens", json={"name": "  "}).status_code == 400


def test_listar_no_expone_el_secreto(client):
    client.post("/account/tokens", json={"name": "Overlay"})
    body = client.get("/account/tokens").json()
    assert len(body["tokens"]) == 1
    assert "token" not in body["tokens"][0]
    assert body["tokens"][0]["revoked_at"] is None


def test_limite_de_tokens_activos(client):
    for i in range(MAX_TOKENS_PER_USER):
        assert client.post("/account/tokens", json={"name": f"t{i}"}).status_code == 200
    assert client.post("/account/tokens", json={"name": "uno de más"}).status_code == 409


def test_token_sirve_para_autenticar_lineups(client):
    token = client.post("/account/tokens", json={"name": "Overlay"}).json()["token"]

    # Sin cookie, solo el header Authorization.
    anon = TestClient(app)
    r = anon.get("/lineups", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert len(r.json()) == 1

    # Sin ningún credential -> 401.
    assert anon.get("/lineups").status_code == 401
    # Bearer con basura -> 401, no 500.
    assert anon.get("/lineups", headers={"Authorization": "Bearer basura"}).status_code == 401


def test_revocar_token_lo_invalida(client):
    created = client.post("/account/tokens", json={"name": "Overlay"}).json()
    token, token_id = created["token"], created["id"]

    revoke = client.delete(f"/account/tokens/{token_id}")
    assert revoke.status_code == 200
    assert revoke.json()["tokens"][0]["revoked_at"] is not None

    anon = TestClient(app)
    r = anon.get("/lineups", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_no_se_puede_revocar_token_ajeno(client):
    created = client.post("/account/tokens", json={"name": "Overlay"}).json()

    other = TestClient(app)
    other.cookies.set(COOKIE_NAME, create_session_cookie(OTHER_STEAMID))
    assert other.delete(f"/account/tokens/{created['id']}").status_code == 404


def test_logout_all_revoca_tokens_de_api(client):
    """logout-all bumpea session_epoch (invalida cookies) pero un token de
    API no trae epoch -- sin revocarlo explícitamente seguiría autenticando
    después de un "cerrar sesión en todos lados"."""
    token = client.post("/account/tokens", json={"name": "Overlay"}).json()["token"]

    anon = TestClient(app)
    assert anon.get("/lineups", headers={"Authorization": f"Bearer {token}"}).status_code == 200

    assert client.post("/auth/logout-all").status_code == 200

    r = anon.get("/lineups", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401


def test_crear_token_requiere_cookie_no_alcanza_con_otro_token(client):
    token = client.post("/account/tokens", json={"name": "Overlay"}).json()["token"]

    anon = TestClient(app)
    r = anon.post(
        "/account/tokens", json={"name": "otro"}, headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 401
