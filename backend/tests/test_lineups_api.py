"""Endpoint /lineups (línea ups por mapa, fuente para la web y el overlay)."""

import pytest
from fastapi.testclient import TestClient

from cs2tracker.api.main import app
from cs2tracker.auth import COOKIE_NAME, create_session_cookie
from cs2tracker.db import Lineup, Player, User
from cs2tracker.db.session import init_db

STEAMID = "76561198000000000"


@pytest.fixture()
def client(tmp_path):
    from sqlalchemy.orm import Session

    engine = init_db(f"sqlite:///{tmp_path}/t.sqlite")
    with Session(engine) as s:
        s.add(Player(steamid=STEAMID, name="Ana"))
        s.add(
            User(
                steamid=STEAMID,
                email="ana@test.local",
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
                instructions="Jumpthrow",
                created_at="2026-01-01T00:00:00",
            )
        )
        s.add(
            Lineup(
                map="de_mirage",
                category="he",
                team="CT",
                label="Caverna",
                x=0.44,
                y=0.23,
                video_url="/lineups/de_mirage/ct/deto-ct-caverna.mp4",
                created_at="2026-01-01T00:00:00",
            )
        )
        s.add(
            Lineup(
                map="de_dust2",
                category="flash",
                team="T",
                label="Long",
                x=0.5,
                y=0.5,
                video_url="/lineups/de_dust2/t/flash-long.mp4",
                created_at="2026-01-01T00:00:00",
            )
        )
        s.commit()
    c = TestClient(app)
    c.cookies.set(COOKIE_NAME, create_session_cookie(STEAMID))
    return c


def test_sin_sesion_401(client):
    client.cookies.delete(COOKIE_NAME)
    assert client.get("/lineups").status_code == 401


def test_lista_todo_sin_filtros(client):
    r = client.get("/lineups")
    assert r.status_code == 200
    assert len(r.json()) == 3


def test_filtra_por_mapa(client):
    body = client.get("/lineups?map=de_mirage").json()
    assert len(body) == 2
    assert all(item["map"] == "de_mirage" for item in body)


def test_filtra_por_team_y_category(client):
    body = client.get("/lineups?map=de_mirage&team=CT&category=he").json()
    assert len(body) == 1
    assert body[0]["label"] == "Caverna"
    assert body[0]["video_url"] == "/lineups/de_mirage/ct/deto-ct-caverna.mp4"
    assert body[0]["instructions"] is None


def test_mapa_sin_lineups_devuelve_vacio(client):
    assert client.get("/lineups?map=de_nuke").json() == []


def test_lineup_maps(client):
    body = client.get("/lineups/maps").json()
    assert body == {"maps": [{"map": "de_dust2", "count": 1}, {"map": "de_mirage", "count": 2}]}
