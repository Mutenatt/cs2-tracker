"""Test de profile_tags_cache: recompute_profile_tags/profile_tags_for.
Con DB (a diferencia del resto de api/queries.py, que no tiene tests
directos) porque acá el comportamiento interesante es justamente el ciclo
completo de escritura -- idempotencia del delete+reinsert y el round-trip
de `detalle` como JSON."""

import pytest
from sqlalchemy.orm import Session

from cs2tracker.api import queries
from cs2tracker.db import Match, MatchPlayer, PlayerMapEvent, PlayerProfileTag, Round, init_db


@pytest.fixture()
def session():
    engine = init_db("sqlite:///:memory:")
    with Session(engine) as s:
        yield s


def _sembrar_partida_lurker(s: Session, match_id: str, steamid: str, teammate: str) -> None:
    """3 rondas de ataque donde `steamid` mata tarde y lejos del centroide
    de su compañero -> tasa_lurker = 100%, supera LUREKA_MUCHO_MIN_RATE."""
    s.add(Match(match_id=match_id, map="de_mirage", demo_file="x.dem", ingested_at="now"))
    s.add(MatchPlayer(match_id=match_id, steamid=steamid, team_num=2))
    s.add(MatchPlayer(match_id=match_id, steamid=teammate, team_num=2))
    for rnd in range(3):
        s.add(Round(match_id=match_id, round_num=rnd, winner_num=2, attacker_roster=2))
        s.add(
            PlayerMapEvent(
                match_id=match_id,
                round_num=rnd,
                tick=100,
                steamid=steamid,
                event_type="kill",
                map="de_mirage",
                team_num=2,
                seconds_into_round=40.0,
                u=0.95,
                v=0.95,
            )
        )
        s.add(
            PlayerMapEvent(
                match_id=match_id,
                round_num=rnd,
                tick=90,
                steamid=teammate,
                event_type="kill",
                map="de_mirage",
                team_num=2,
                seconds_into_round=10.0,
                u=0.2,
                v=0.2,
            )
        )
    s.commit()


def test_recompute_crea_tag_lurkea_mucho_si_supera_el_umbral(session):
    _sembrar_partida_lurker(session, "m1", "atacante", "compa")

    queries.recompute_profile_tags(session, "atacante", ventana=20)
    session.commit()

    tags = queries.profile_tags_for(session, "atacante")
    assert [t.tag_id for t in tags] == ["lurkea_mucho"]
    assert tags[0].detalle == {"lurker_rate": 100.0}
    assert tags[0].ventana_partidas == 20


def test_recompute_es_idempotente_no_duplica_filas(session):
    _sembrar_partida_lurker(session, "m1", "atacante", "compa")

    queries.recompute_profile_tags(session, "atacante", ventana=20)
    session.commit()
    queries.recompute_profile_tags(session, "atacante", ventana=20)
    session.commit()

    assert session.query(PlayerProfileTag).count() == 1


def test_recompute_borra_tags_viejos_si_ya_no_aplican(session):
    # Sembrar rondas que SÍ califican, recalcular (crea el tag)...
    _sembrar_partida_lurker(session, "m1", "atacante", "compa")
    queries.recompute_profile_tags(session, "atacante", ventana=20)
    session.commit()
    assert len(queries.profile_tags_for(session, "atacante")) == 1

    # ...borrar esos eventos (ya no hay señal de lurker) y recalcular nuevo.
    session.query(PlayerMapEvent).delete()
    session.query(Round).delete()
    session.commit()
    queries.recompute_profile_tags(session, "atacante", ventana=20)
    session.commit()

    assert queries.profile_tags_for(session, "atacante") == []


def test_recompute_sin_datos_no_crea_tags(session):
    queries.recompute_profile_tags(session, "nadie", ventana=20)
    session.commit()
    assert queries.profile_tags_for(session, "nadie") == []


def test_recompute_global_percentiles_crea_una_fila_por_metrica(session):
    from cs2tracker.db import GlobalMetricStats, PlayerMatchStats

    _sembrar_partida_lurker(session, "m1", "atacante", "compa")
    session.add(PlayerMatchStats(match_id="m1", steamid="atacante", adr=100.0, kills=20, assists=5))
    session.add(PlayerMatchStats(match_id="m1", steamid="compa", adr=60.0, kills=10, assists=2))
    session.commit()

    queries.recompute_global_percentiles(session)
    session.commit()

    stats = {g.metric: g for g in session.query(GlobalMetricStats).all()}
    assert set(stats) == {"adr", "entry_attempts", "kill_participation"}
    assert stats["adr"].n_players == 2
    assert stats["adr"].p25 == 70.0  # interpolación entre 60 y 100
    # Idempotencia: recomputar no duplica filas.
    queries.recompute_global_percentiles(session)
    session.commit()
    assert session.query(GlobalMetricStats).count() == 3
