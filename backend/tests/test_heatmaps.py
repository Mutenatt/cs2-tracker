"""Test de los endpoints de heatmaps: auth, min-sample, y las 4 vistas."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from cs2tracker.api.main import app
from cs2tracker.auth import COOKIE_NAME, create_session_cookie
from cs2tracker.db import Match, MatchPlayer, Player, PlayerMapEvent, PlayerMapZone, User
from cs2tracker.db.session import init_db

A, B, C = "111", "222", "333"  # A y B comparten partida; C no comparte con nadie


@pytest.fixture()
def client(tmp_path):
    engine = init_db(f"sqlite:///{tmp_path}/t.sqlite")
    with Session(engine) as s:
        for sid in (A, B, C):
            s.add(Player(steamid=sid, name=sid))
            s.add(User(steamid=sid, display_name=sid))
        s.add(
            Match(
                match_id="m1",
                demo_file="x.dem",
                map="de_mirage",
                n_rounds=10,
                ingested_at="2026-07-14T00:00:00Z",
            )
        )
        s.add(MatchPlayer(match_id="m1", steamid=A, team_num=2))
        s.add(MatchPlayer(match_id="m1", steamid=B, team_num=3))

        # Deaths: una celda por encima del umbral, otra por debajo (se filtra).
        s.add(
            PlayerMapZone(
                steamid=A,
                map="de_mirage",
                event_type="death",
                grid_x=2,
                grid_y=2,
                count=8,
                traded_count=1,
            )
        )
        s.add(
            PlayerMapZone(
                steamid=A,
                map="de_mirage",
                event_type="death",
                grid_x=9,
                grid_y=9,
                count=2,
                traded_count=0,
            )
        )
        # Kills con entries.
        s.add(
            PlayerMapZone(
                steamid=A,
                map="de_mirage",
                event_type="kill",
                grid_x=3,
                grid_y=3,
                count=10,
                entry_count=6,
            )
        )
        # Utility.
        s.add(
            PlayerMapZone(
                steamid=A,
                map="de_mirage",
                event_type="flash_thrown",
                grid_x=4,
                grid_y=4,
                count=5,
                avg_enemies_blinded=1.5,
            )
        )

        # Eventos crudos de flash para friendly_fire_summary.
        for i, tm in enumerate([0, 0, 2]):  # 2 de 3 flashes cegaron a un compañero
            s.add(
                PlayerMapEvent(
                    match_id="m1",
                    round_num=i,
                    tick=i * 100,
                    steamid=A,
                    event_type="flash_thrown",
                    map="de_mirage",
                    teammates_blinded=tm,
                )
            )
        s.commit()
    return TestClient(app)


def _login(client: TestClient, steamid: str) -> None:
    client.cookies.set(COOKIE_NAME, create_session_cookie(steamid))


def test_heatmap_requiere_sesion(client):
    assert client.get(f"/players/{A}/heatmaps/deaths?map=de_mirage").status_code == 401


def test_heatmap_403_si_no_comparten_partida(client):
    _login(client, C)
    assert client.get(f"/players/{A}/heatmaps/deaths?map=de_mirage").status_code == 403


def test_heatmap_propio_siempre_permitido(client):
    _login(client, A)
    assert client.get(f"/players/{A}/heatmaps/deaths?map=de_mirage").status_code == 200


def test_heatmap_deaths_filtra_por_muestra_minima(client):
    _login(client, B)  # B comparte partida con A
    r = client.get(f"/players/{A}/heatmaps/deaths?map=de_mirage")
    assert r.status_code == 200
    cells = r.json()["cells"]
    assert len(cells) == 1
    assert cells[0]["grid_x"] == 2 and cells[0]["count"] == 8


def test_heatmap_entries_usa_entry_count_no_total(client):
    _login(client, A)
    r = client.get(f"/players/{A}/heatmaps/entries?map=de_mirage")
    assert r.status_code == 200
    body = r.json()
    assert len(body["entry_kills"]) == 1
    assert body["entry_kills"][0]["count"] == 6  # entry_count, no el count total (10)
    assert body["entry_deaths"] == []


def test_heatmap_utility_incluye_friendly_fire_aparte(client):
    _login(client, A)
    r = client.get(f"/players/{A}/heatmaps/utility?map=de_mirage&type=flash")
    assert r.status_code == 200
    body = r.json()
    assert len(body["cells"]) == 1
    assert body["cells"][0]["avg_enemies_blinded"] == 1.5
    ff = body["friendly_fire"]
    assert ff["total_flashes"] == 3
    assert ff["friendly_flashes"] == 1
    assert round(ff["friendly_flash_rate"], 1) == round(100 / 3, 1)


def test_heatmap_utility_type_invalido(client):
    _login(client, A)
    r = client.get(f"/players/{A}/heatmaps/utility?map=de_mirage&type=nope")
    assert r.status_code == 400
