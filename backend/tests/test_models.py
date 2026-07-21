"""Test de la capa de DB: crear esquema, insertar y consultar (SQLite en memoria)."""

import pytest
from sqlalchemy import select

from cs2tracker.db import Kill, Match, Player, PlayerMatchStats, init_db
from cs2tracker.db.session import get_engine


@pytest.fixture()
def session():
    from sqlalchemy.orm import Session

    engine = init_db("sqlite:///:memory:")
    with Session(engine) as s:
        yield s


def test_crear_e_insertar(session):
    session.add(
        Match(
            match_id="m1",
            demo_file="x.dem",
            map="de_mirage",
            n_rounds=22,
            ingested_at="2026-07-13T00:00:00Z",
        )
    )
    session.add(Player(steamid="A", name="Ana"))
    session.add(Kill(match_id="m1", victim="A", attacker="B", headshot=True))
    session.add(
        PlayerMatchStats(
            match_id="m1",
            steamid="A",
            kills=21,
            deaths=14,
            assists=10,
            damage=2945,
            adr=133.9,
            kd=1.5,
            hs_pct=57.1,
        )
    )
    session.commit()

    m = session.get(Match, "m1")
    assert m.map == "de_mirage"
    st = session.scalar(select(PlayerMatchStats).where(PlayerMatchStats.steamid == "A"))
    assert st.kills == 21 and st.adr == 133.9
    assert session.scalar(select(Kill).where(Kill.match_id == "m1")).headshot is True


def test_engine_singleton():
    assert get_engine("sqlite:///:memory:") is not None
