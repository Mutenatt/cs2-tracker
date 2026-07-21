"""Test del endpoint /matches/{id}/duels sembrando la DB (sin .dem)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from cs2tracker.api.main import app
from cs2tracker.auth import COOKIE_NAME, create_session_cookie
from cs2tracker.db import Kill, Match, MatchPlayer, Player
from cs2tracker.db.session import init_db


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
                ingested_at="2026-07-16T00:00:00Z",
            )
        )
        for sid, name, tn in [
            ("A1", "Ana", 2),
            ("A2", "Abel", 2),
            ("B1", "Beto", 3),
            ("B2", "Bruno", 3),
        ]:
            s.add(Player(steamid=sid, name=name))
            s.add(MatchPlayer(match_id="m1", steamid=sid, team_num=tn))
        # A1 mata a B1 dos veces (una con posición), B1 mata a A1 una vez.
        s.add(
            Kill(
                match_id="m1",
                round_num=0,
                tick=100,
                attacker="A1",
                victim="B1",
                weapon="ak47",
                headshot=True,
                victim_x=-2000.0,
                victim_y=1000.0,
                attacker_x=-2100.0,
                attacker_y=900.0,
            )
        )
        s.add(
            Kill(
                match_id="m1",
                round_num=2,
                tick=300,
                attacker="A1",
                victim="B1",
                weapon="awp",
                thru_smoke=True,
            )
        )
        s.add(
            Kill(match_id="m1", round_num=1, tick=200, attacker="B1", victim="A1", weapon="deagle")
        )
        # Excluidos: team kill y muerte sin atacante (caída).
        s.add(
            Kill(
                match_id="m1", round_num=3, tick=400, attacker="A1", victim="A2", weapon="hegrenade"
            )
        )
        s.add(Kill(match_id="m1", round_num=4, tick=500, attacker=None, victim="B2"))
        s.commit()
    c = TestClient(app)
    c.cookies.set(COOKIE_NAME, create_session_cookie("A1"))  # A1 jugó m1
    return c


def test_duels_matriz_y_eventos(client):
    r = client.get("/matches/m1/duels")
    assert r.status_code == 200
    body = r.json()

    assert body["map"] == "de_ancient"
    assert body["has_radar"] is True
    assert [t["team_num"] for t in body["teams"]] == [2, 3]
    assert len(body["cells"]) == 4  # 2x2, incluye pares 0-0

    cell = next(c for c in body["cells"] if c["steamid_a"] == "A1" and c["steamid_b"] == "B1")
    assert cell["kills_a"] == 2 and cell["kills_b"] == 1
    zero = next(c for c in body["cells"] if c["steamid_a"] == "A2" and c["steamid_b"] == "B2")
    assert zero["kills_a"] == 0 and zero["kills_b"] == 0

    # Solo los 3 duelos cross-team, ordenados por ronda; exclusiones ausentes.
    assert [e["round_num"] for e in body["events"]] == [0, 1, 2]
    assert all(e["attacker"] is not None for e in body["events"])

    # uv poblado cuando hay posición, None cuando falta.
    first = body["events"][0]
    assert first["victim_u"] is not None and first["victim_v"] is not None
    assert first["headshot"] is True
    assert body["events"][2]["victim_u"] is None
    assert body["events"][2]["thru_smoke"] is True


def test_duels_404(client):
    assert client.get("/matches/nope/duels").status_code == 404
