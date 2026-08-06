"""Endpoints /scene/* (ranking con fallback + streams LATAM)."""

import pytest
from fastapi.testclient import TestClient

from cs2tracker.api import scene
from cs2tracker.api.main import app
from cs2tracker.auth import COOKIE_NAME, create_session_cookie
from cs2tracker.infra.hltv_ranking import RankedTeam
from cs2tracker.infra.streams_common import LiveStream
from cs2tracker.infra.ttl_cache import cache

STEAMID = "76561198000000000"

HLTV_TEAMS = [
    RankedTeam(position=1, name="Spirit", points=945, change=2, logo_url="https://x/logo.png"),
    RankedTeam(position=2, name="Vitality", points=802, change=0, logo_url=None),
]
VALVE_TEAMS = [
    RankedTeam(position=1, name="Spirit", points=1993, change=None, logo_url=None),
]
TWITCH_STREAMS = [
    LiveStream(
        platform="twitch",
        channel="Streamer",
        login="streamer",
        title="CS2 ranked",
        viewers=1234,
        language="es",
        thumbnail_url="https://x/thumb.jpg",
    ),
    LiveStream(
        platform="twitch",
        channel="Chico",
        login="chico",
        title="faceit",
        viewers=50,
        language="es",
        thumbnail_url="https://x/t2.jpg",
    ),
]
KICK_STREAMS = [
    LiveStream(
        platform="kick",
        channel="KickStar",
        login="kickstar",
        title="premier",
        viewers=500,
        language="pt",
        thumbnail_url="https://x/k.jpg",
    ),
]


def _async_const(value):
    async def _f(*a, **kw):
        return value

    return _f


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # DB limpia por si el import de main la necesita; el cache singleton se
    # limpia para que un test no vea el ranking cacheado por otro.
    from sqlalchemy.orm import Session

    from cs2tracker.db import Player, User
    from cs2tracker.db.session import init_db

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
        s.commit()
    cache.clear()
    c = TestClient(app)
    c.cookies.set(COOKIE_NAME, create_session_cookie(STEAMID))
    return c


def test_sin_sesion_401(client):
    client.cookies.delete(COOKIE_NAME)
    assert client.get("/scene/ranking").status_code == 401
    assert client.get("/scene/streams").status_code == 401


def test_ranking_hltv_ok(client, monkeypatch):
    monkeypatch.setattr(scene, "fetch_hltv_top10", _async_const(HLTV_TEAMS))
    r = client.get("/scene/ranking")
    assert r.status_code == 200
    body = r.json()
    assert body["source"] == "hltv"
    assert [t["name"] for t in body["teams"]] == ["Spirit", "Vitality"]
    assert body["teams"][0]["change"] == 2
    assert body["teams"][0]["logo_url"] == "https://x/logo.png"


def test_ranking_fallback_valve(client, monkeypatch):
    monkeypatch.setattr(scene, "fetch_hltv_top10", _async_const([]))
    monkeypatch.setattr(scene, "fetch_valve_top10", _async_const(VALVE_TEAMS))
    body = client.get("/scene/ranking").json()
    assert body["source"] == "valve"
    assert body["teams"][0]["change"] is None


def test_ranking_ambas_fuentes_caidas_200(client, monkeypatch):
    monkeypatch.setattr(scene, "fetch_hltv_top10", _async_const([]))
    monkeypatch.setattr(scene, "fetch_valve_top10", _async_const([]))
    r = client.get("/scene/ranking")
    assert r.status_code == 200
    assert r.json() == {"source": "unavailable", "teams": []}


def test_ranking_cachea_y_no_reconsulta(client, monkeypatch):
    calls = {"n": 0}

    async def _counting(*a, **kw):
        calls["n"] += 1
        return HLTV_TEAMS

    monkeypatch.setattr(scene, "fetch_hltv_top10", _counting)
    client.get("/scene/ranking")
    client.get("/scene/ranking")
    assert calls["n"] == 1


def _configure(monkeypatch, *, twitch=False, kick=False):
    monkeypatch.setattr(scene.twitch, "is_configured", lambda: twitch)
    monkeypatch.setattr(scene.kick, "is_configured", lambda: kick)


def test_streams_sin_credenciales(client, monkeypatch):
    _configure(monkeypatch, twitch=False, kick=False)
    r = client.get("/scene/streams")
    assert r.status_code == 200
    assert r.json() == {"configured": False, "streams": []}


def test_streams_mezcla_plataformas_por_viewers(client, monkeypatch):
    _configure(monkeypatch, twitch=True, kick=True)
    monkeypatch.setattr(scene.twitch, "fetch_latam_cs_streams", _async_const(TWITCH_STREAMS))
    monkeypatch.setattr(scene.kick, "fetch_latam_cs_streams", _async_const(KICK_STREAMS))
    body = client.get("/scene/streams").json()
    assert body["configured"] is True
    # Mezclados y ordenados por viewers desc: 1234 (twitch) > 500 (kick) > 50.
    assert [(s["platform"], s["viewers"]) for s in body["streams"]] == [
        ("twitch", 1234),
        ("kick", 500),
        ("twitch", 50),
    ]
    kick_out = body["streams"][1]
    assert kick_out["url"] == "https://kick.com/kickstar"
    assert kick_out["channel_slug"] == "kickstar"
    twitch_out = body["streams"][0]
    assert twitch_out["url"] == "https://www.twitch.tv/streamer"
    assert twitch_out["channel_slug"] == "streamer"


def test_streams_solo_twitch_configurado(client, monkeypatch):
    _configure(monkeypatch, twitch=True, kick=False)
    monkeypatch.setattr(scene.twitch, "fetch_latam_cs_streams", _async_const(TWITCH_STREAMS))
    # kick.fetch_latam_cs_streams real ya devuelve [] si no está configurado.
    body = client.get("/scene/streams").json()
    assert body["configured"] is True
    assert [s["platform"] for s in body["streams"]] == ["twitch", "twitch"]


def test_streams_solo_kick_configurado(client, monkeypatch):
    _configure(monkeypatch, twitch=False, kick=True)
    monkeypatch.setattr(scene.kick, "fetch_latam_cs_streams", _async_const(KICK_STREAMS))
    body = client.get("/scene/streams").json()
    assert body["configured"] is True
    assert [s["platform"] for s in body["streams"]] == ["kick"]
