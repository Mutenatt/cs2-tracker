"""Test del endpoint de armas/hitgroups."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from cs2tracker.api.main import app
from cs2tracker.auth import COOKIE_NAME, create_session_cookie
from cs2tracker.db import Damage, Kill, Match, MatchPlayer, Player, init_db


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
        s.add(Player(steamid="A", name="Ana"))
        s.add(MatchPlayer(match_id="m1", steamid="A", team_num=2))
        s.add(Kill(match_id="m1", victim="Z", attacker="A", weapon="ak47"))
        s.add(
            Damage(
                match_id="m1",
                attacker="A",
                victim="Z",
                weapon="ak47",
                dmg_health=100,
                hitgroup="head",
            )
        )
        s.add(
            Damage(
                match_id="m1",
                attacker="A",
                victim="Z",
                weapon="ak47",
                dmg_health=30,
                hitgroup="chest",
            )
        )
        s.commit()
    c = TestClient(app)
    c.cookies.set(COOKIE_NAME, create_session_cookie("A"))  # A jugó m1
    return c


def test_weapons(client):
    r = client.get("/matches/m1/weapons").json()
    ana = [p for p in r["players"] if p["name"] == "Ana"][0]
    assert ana["top_weapons"][0]["weapon"] == "ak47"
    assert ana["top_weapons"][0]["damage"] == 130
    assert ana["top_weapons"][0]["kills"] == 1
    assert ana["hitgroups"]["head"] == 100
