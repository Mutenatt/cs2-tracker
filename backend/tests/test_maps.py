"""Test del transform mundo->radar y del endpoint de kills."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from cs2tracker import maps
from cs2tracker.api.main import app
from cs2tracker.auth import COOKIE_NAME, create_session_cookie
from cs2tracker.db import Kill, Match, MatchPlayer, Player, User, init_db


def test_transform_en_rango():
    # centro aproximado del mundo de mirage -> debe caer dentro del radar 0..1
    uv = maps.to_radar_norm("de_mirage", -500.0, 0.0)
    assert uv is not None
    u, v = uv
    assert 0.0 <= u <= 1.0 and 0.0 <= v <= 1.0


def test_mapa_desconocido():
    assert maps.to_radar_norm("de_inexistente", 0, 0) is None
    assert maps.has_radar("de_inexistente") is False
    assert maps.has_radar("de_mirage") is True


@pytest.fixture()
def client(tmp_path):
    engine = init_db(f"sqlite:///{tmp_path}/t.sqlite")
    with Session(engine) as s:
        s.add(
            Match(
                match_id="m1",
                demo_file="x.dem",
                map="de_mirage",
                n_rounds=1,
                ingested_at="2026-07-13T00:00:00Z",
            )
        )
        s.add(Player(steamid="B", name="Beto"))
        s.add(
            User(
                steamid="B",
                email="b@test.local",
                password_hash="x",
                email_verified_at="2026-01-01T00:00:00",
            )
        )
        s.add(MatchPlayer(match_id="m1", steamid="B", team_num=2))
        s.add(
            Kill(
                match_id="m1",
                victim="A",
                attacker="B",
                headshot=True,
                victim_x=-500.0,
                victim_y=0.0,
            )
        )
        s.add(
            Kill(
                match_id="m1",
                victim="C",
                attacker="D",
                headshot=False,
                victim_x=None,
                victim_y=None,
            )
        )  # sin coords -> se ignora
        s.commit()
    c = TestClient(app)
    c.cookies.set(COOKIE_NAME, create_session_cookie("B"))  # B jugó m1
    return c


def test_kills_endpoint(client):
    r = client.get("/matches/m1/kills").json()
    assert r["map"] == "de_mirage" and r["has_radar"] is True
    assert len(r["kills"]) == 1  # el que no tiene coords se filtra
    assert r["kills"][0]["headshot"] is True
    assert 0.0 <= r["kills"][0]["u"] <= 1.0
