"""Test de la API sembrando la DB con modelos (sin necesitar un .dem)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from cs2tracker.api.main import app
from cs2tracker.auth import COOKIE_NAME, create_session_cookie
from cs2tracker.db import Match, MatchPlayer, Player, PlayerMatchStats, Round, User
from cs2tracker.db.session import init_db


def _add_user(session, steamid):
    """get_current_steamid ahora valida el steamid de la cookie contra una
    fila User real (ver auth.py::_steamid_if_epoch_matches) -- un cookie de
    test necesita una fila User de respaldo, no solo Player."""
    session.add(
        User(
            steamid=steamid,
            email=f"{steamid}@test.local",
            password_hash="x",
            email_verified_at="2026-01-01T00:00:00",
        )
    )


@pytest.fixture()
def client(tmp_path):
    engine = init_db(f"sqlite:///{tmp_path}/t.sqlite")
    with Session(engine) as s:
        s.add(
            Match(
                match_id="m1",
                demo_file="x.dem",
                map="de_ancient",
                n_rounds=20,
                ingested_at="2026-07-13T00:00:00Z",
            )
        )
        s.add(Player(steamid="A", name="Ana"))
        s.add(Player(steamid="B", name="Beto"))
        _add_user(s, "A")
        s.add(MatchPlayer(match_id="m1", steamid="A", team_num=2))
        s.add(MatchPlayer(match_id="m1", steamid="B", team_num=3))
        s.add(
            PlayerMatchStats(
                match_id="m1",
                steamid="A",
                kills=25,
                deaths=10,
                assists=5,
                damage=2000,
                adr=100.0,
                kd=2.5,
                hs_pct=60.0,
            )
        )
        s.add(
            PlayerMatchStats(
                match_id="m1",
                steamid="B",
                kills=8,
                deaths=18,
                assists=3,
                damage=900,
                adr=45.0,
                kd=0.44,
                hs_pct=25.0,
            )
        )
        s.add(Round(match_id="m1", round_num=0, winner_num=2))
        s.add(Round(match_id="m1", round_num=1, winner_num=2))
        s.add(Round(match_id="m1", round_num=2, winner_num=3))
        s.commit()
    c = TestClient(app)
    c.cookies.set(COOKIE_NAME, create_session_cookie("A"))  # A jugó m1
    return c


def test_list_matches(client):
    r = client.get("/matches")
    assert r.status_code == 200
    assert r.json()[0]["map"] == "de_ancient"


def test_list_matches_requiere_login(client):
    client.cookies.clear()
    assert client.get("/matches").status_code == 401


def test_match_detail_ordenado(client):
    r = client.get("/matches/m1")
    assert r.status_code == 200
    body = r.json()
    sb = body["scoreboard"]
    assert [p["name"] for p in sb] == ["Ana", "Beto"]
    assert sb[0]["adr"] == 100.0
    assert sb[0]["team_num"] == 2
    assert sorted(t["score"] for t in body["teams"]) == [1, 2]


def test_match_detail_403_si_no_participo(client):
    from cs2tracker.db.session import get_engine

    with Session(get_engine()) as s:
        s.add(Player(steamid="outsider", name="Outsider"))
        _add_user(s, "outsider")
        s.commit()
    client.cookies.set(COOKIE_NAME, create_session_cookie("outsider"))
    assert client.get("/matches/m1").status_code == 403


def test_match_404(client):
    assert client.get("/matches/nope").status_code == 404
