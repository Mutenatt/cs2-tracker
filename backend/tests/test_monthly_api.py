"""Test del endpoint /players/{steamid}/monthly (sin .dem, sembrando la DB)."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from cs2tracker.api.main import app
from cs2tracker.auth import COOKIE_NAME, create_session_cookie
from cs2tracker.db import (
    Kill,
    Match,
    MatchPlayer,
    Player,
    PlayerClutch,
    PlayerMatchStats,
    Round,
    User,
)
from cs2tracker.db.session import init_db

A, B = "111", "222"  # A y B comparten partida m1

NOW = datetime.now(UTC)
RECENT = (NOW - timedelta(minutes=5)).isoformat()


@pytest.fixture()
def client(tmp_path):
    engine = init_db(f"sqlite:///{tmp_path}/t.sqlite")
    with Session(engine) as s:
        for sid in (A, B, "999"):
            s.add(Player(steamid=sid, name=sid))
            s.add(
                User(
                    steamid=sid,
                    email=f"{sid}@test.local",
                    password_hash="x",
                    email_verified_at="2026-01-01T00:00:00",
                )
            )
        s.add(
            Match(
                match_id="m1",
                demo_file="x.dem",
                map="de_mirage",
                n_rounds=20,
                ingested_at=RECENT,
                played_at=RECENT,
            )
        )
        s.add(MatchPlayer(match_id="m1", steamid=A, team_num=2))
        s.add(MatchPlayer(match_id="m1", steamid=B, team_num=3))
        s.add(
            PlayerMatchStats(
                match_id="m1",
                steamid=A,
                kills=25,
                deaths=10,
                assists=5,
                damage=2000,
                adr=100.0,
                kd=2.5,
                hs_pct=50.0,
                kast=80.0,
                entry_kills=3,
                rating=1.4,
            )
        )
        s.add(Round(match_id="m1", round_num=0, winner_num=2))
        s.add(Round(match_id="m1", round_num=1, winner_num=2))
        s.add(Round(match_id="m1", round_num=2, winner_num=3))
        s.add(
            PlayerClutch(match_id="m1", steamid=A, round_num=15, enemies_at_start=2, outcome="won")
        )
        s.add(Kill(match_id="m1", round_num=15, tick=1000, attacker=A, victim=B))
        s.commit()
    c = TestClient(app)
    c.cookies.set(COOKIE_NAME, create_session_cookie(A))
    return c


def test_monthly_totals_y_headline_con_datos_reales(client):
    r = client.get(f"/players/{A}/monthly")
    assert r.status_code == 200
    body = r.json()
    assert body["totals"]["matches"] == 1
    assert body["totals"]["winrate"] == 100
    assert body["headline"]["rating"] == 1.4
    assert body["headline"]["hs_pct"] == 50


def test_monthly_mvp_incluye_clutch_sembrado(client):
    body = client.get(f"/players/{A}/monthly").json()
    assert body["detail"]["clutches_won"] == 1
    mvp = body["detail"]["mvp"]
    assert mvp is not None
    assert mvp["clutch_size"] == 2
    assert mvp["kills_in_round"] == 1
    assert mvp["round"] == 15


def test_monthly_403_aunque_comparta_partida(client):
    client.cookies.set(COOKIE_NAME, create_session_cookie(B))
    assert client.get(f"/players/{A}/monthly").status_code == 403


def test_monthly_200_con_uno_mismo(client):
    assert client.get(f"/players/{A}/monthly").status_code == 200


def test_monthly_empty_state_sin_partidas(client):
    client.cookies.set(COOKIE_NAME, create_session_cookie("999"))
    r = client.get("/players/999/monthly")
    assert r.status_code == 200
    body = r.json()
    assert body["totals"]["matches"] == 0
    assert body["detail"]["mvp"] is None


def test_monthly_requiere_login(client):
    client.cookies.clear()
    assert client.get(f"/players/{A}/monthly").status_code == 401
