"""Test de ingesta: _persist arma player_map_events/zones desde un ParsedDemo."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from cs2tracker.db import MatchPlayer, PlayerMapEvent, PlayerMapZone, init_db
from cs2tracker.infra.parser import ParsedDemo
from cs2tracker.ingest import _persist

TEAMS = {"A": 2, "A2": 2, "B": 3, "B2": 3}


@pytest.fixture()
def session():
    engine = init_db("sqlite:///:memory:")
    with Session(engine) as s:
        yield s


def _demo() -> ParsedDemo:
    p = ParsedDemo(match_id="m1", demo_file="x.dem", map="de_mirage", n_rounds=1)
    p.players = {"A": "Ana", "A2": "Ana2", "B": "Beto", "B2": "Beto2"}
    p.teams = TEAMS
    # A tiene CS Rating real; A2 está calibrando (0); B/B2 sin dato (demo vieja).
    p.ranks = {"A": 14655, "A2": 0}
    p.rank_types = {"A": 11, "A2": 11}
    p.comp_wins = {"A": 120, "A2": 4}
    p.rounds = [{"round_num": 0, "tick": 500, "winner_roster": 2}]
    # Ronda 0: B mata a A2 (entry). A vengó a A2 matando a B enseguida (trade).
    p.kills = [
        {
            "round_num": 0,
            "tick": 100,
            "attacker": "B",
            "victim": "A2",
            "assister": None,
            "weapon": "ak47",
            "headshot": False,
            "distance": 500.0,
            "attacker_x": 0.0,
            "attacker_y": 0.0,
            "attacker_z": 0.0,
            "victim_x": 100.0,
            "victim_y": 100.0,
            "victim_z": 0.0,
        },
        {
            "round_num": 0,
            "tick": 150,
            "attacker": "A",
            "victim": "B",
            "assister": None,
            "weapon": "m4a1",
            "headshot": True,
            "distance": 300.0,
            "attacker_x": 10.0,
            "attacker_y": 10.0,
            "attacker_z": 0.0,
            "victim_x": 200.0,
            "victim_y": 200.0,
            "victim_z": 0.0,
        },
    ]
    p.damages = []
    p.grenades = [
        {
            "round_num": 0,
            "tick": 90,
            "thrower": "A",
            "weapon": "flashbang",
            "x": 50.0,
            "y": 50.0,
            "z": 0.0,
            "entity_id": 1,
        },
    ]
    p.blinds = [
        {
            "round_num": 0,
            "tick": 95,
            "attacker": "A",
            "victim": "B",
            "duration": 2.0,
            "entity_id": 1,
        },
    ]
    return p


def test_persist_crea_kill_y_death_events(session):
    _persist(session, _demo())
    session.commit()

    deaths = session.scalars(
        select(PlayerMapEvent).where(PlayerMapEvent.event_type == "death")
    ).all()
    assert {e.steamid for e in deaths} == {"A2", "B"}

    a2 = next(e for e in deaths if e.steamid == "A2")
    assert a2.is_entry is True
    assert a2.is_traded is True  # vengada por A matando a B

    b = next(e for e in deaths if e.steamid == "B")
    assert b.is_entry is False
    assert b.is_traded is False  # nadie vengó a B

    kills = session.scalars(select(PlayerMapEvent).where(PlayerMapEvent.event_type == "kill")).all()
    assert {e.steamid for e in kills} == {"A", "B"}


def test_persist_crea_flash_thrown_con_efectividad(session):
    _persist(session, _demo())
    session.commit()

    flash = session.scalar(
        select(PlayerMapEvent).where(PlayerMapEvent.event_type == "flash_thrown")
    )
    assert flash.steamid == "A"
    assert flash.enemies_blinded == 1
    assert flash.blind_duration_total == 2.0
    assert flash.teammates_blinded == 0
    assert flash.u is not None and flash.grid_x is not None  # proyectado al radar


def test_persist_guarda_rank_por_jugador(session):
    _persist(session, _demo())
    session.commit()

    mps = {mp.steamid: mp for mp in session.scalars(select(MatchPlayer)).all()}
    assert mps["A"].rank == 14655 and mps["A"].rank_type == 11 and mps["A"].comp_wins == 120
    assert mps["A2"].rank == 0  # calibrando: 0 crudo, no NULL
    assert mps["B"].rank is None  # sin dato en el demo -> NULL


def test_persist_agrega_player_map_zones(session):
    _persist(session, _demo())
    session.commit()

    zones = session.scalars(select(PlayerMapZone).where(PlayerMapZone.steamid == "A2")).all()
    assert len(zones) == 1
    assert zones[0].event_type == "death"
    assert zones[0].count == 1
    assert zones[0].entry_count == 1
