"""SteamAutoSource: la mÃ¡quina de estados del auto-fetch, todo mockeado.

Regla de oro bajo test: last_sharecode avanza SOLO tras descarga exitosa o
skip deliberado (expirado / ya en DB); nunca con el sidecar caÃ­do.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from cs2tracker.db import Match, Player, User, init_db
from cs2tracker.infra import sources
from cs2tracker.infra.gc_client import DemoExpired, SidecarUnavailable
from cs2tracker.infra.sharecode import decode_sharecode, demo_filename, match_id_str
from cs2tracker.infra.sources import SteamAutoSource
from cs2tracker.infra.steam_sharecodes import AuthCodeInvalid, RateLimited

STEAMID = "76561198000000000"
STEAMID2 = "76561198000000001"
CODE_A = "CSGO-GADqf-jjyJ8-cSP2r-smZRo-TO2xK"  # knowncode inicial
CODE_B = "CSGO-AAAAA-AAAAA-AAAAA-AAAAA-AAAAA"  # "siguiente" (decodifica a ceros)


def _add_user(s: Session, steamid: str, name: str) -> None:
    s.add(Player(steamid=steamid, name=name))
    s.add(
        User(
            steamid=steamid,
            display_name=name,
            avatar_url=None,
            steam_auth_code="AAAA-AAAAA-AAAA",
            last_sharecode=CODE_A,
            autofetch_status="active",
        )
    )


@pytest.fixture()
def engine(tmp_path):
    engine = init_db(f"sqlite:///{tmp_path}/t.sqlite")
    with Session(engine) as s:
        _add_user(s, STEAMID, "Ana")
        s.commit()
    return engine


@pytest.fixture()
def src(tmp_path, monkeypatch):
    monkeypatch.setattr(sources, "sidecar_healthy", lambda **kw: True)
    return SteamAutoSource(
        download_dir=tmp_path / "dl",
        api_key="clave",
        sidecar_url="http://sidecar.test",
        request_spacing=0,
    )


def _chain(monkeypatch, responses: list):
    """get_next_sharecode falso: consume `responses` (str | None | Exception)."""
    calls: list[str] = []

    def fake(steamid, auth_code, known_code, *, api_key, **kw):
        calls.append(known_code)
        r = responses.pop(0) if responses else None
        if isinstance(r, Exception):
            raise r
        return r

    monkeypatch.setattr(sources, "get_next_sharecode", fake)
    return calls


def _fake_download(monkeypatch):
    downloads: list[str] = []

    def fake(url, dest, **kw):
        downloads.append(url)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"demo")
        return dest

    monkeypatch.setattr(sources, "download_and_extract", fake)
    return downloads


def _user(engine, steamid=STEAMID) -> User:
    with Session(engine) as s:
        u = s.get(User, steamid)
        s.expunge(u)
        return u


def test_camino_feliz_descarga_y_avanza(engine, src, monkeypatch):
    _chain(monkeypatch, [CODE_B, None])
    monkeypatch.setattr(
        sources, "resolve_demo", lambda code, **kw: ("http://replay/x.dem.bz2", 1730000000)
    )
    downloads = _fake_download(monkeypatch)

    demos = list(src.poll())

    assert [d.name for d in demos] == [demo_filename(decode_sharecode(CODE_B))]
    assert downloads == ["http://replay/x.dem.bz2"]
    assert src.owner_of(demos[0]) == STEAMID
    # matchtime del GC -> played_at ISO para la ingesta
    assert src.played_at_of(demos[0]) == "2024-10-27T03:33:20+00:00"
    u = _user(engine)
    assert u.last_sharecode == CODE_B
    assert u.last_polled_at is not None
    assert u.last_fetched_at is not None


def test_al_dia_no_hace_nada(engine, src, monkeypatch):
    _chain(monkeypatch, [None])

    assert list(src.poll()) == []
    u = _user(engine)
    assert u.last_sharecode == CODE_A
    assert u.last_polled_at is not None


def test_403_marca_revoked_y_no_vuelve_a_pollear(engine, src, monkeypatch):
    calls = _chain(monkeypatch, [AuthCodeInvalid("403")])

    assert list(src.poll()) == []
    u = _user(engine)
    assert u.autofetch_status == "revoked"
    assert u.last_sharecode == CODE_A  # la posiciÃ³n se conserva

    # Segundo ciclo: ya no estÃ¡ 'active', no se le pega a Steam.
    assert list(src.poll()) == []
    assert len(calls) == 1


def test_429_corta_el_ciclo_sin_avanzar(engine, src, monkeypatch):
    _chain(monkeypatch, [RateLimited("429")])

    assert list(src.poll()) == []
    u = _user(engine)
    assert u.autofetch_status == "active"
    assert u.last_sharecode == CODE_A
    assert u.last_polled_at is not None
    assert u.autofetch_error == "rate limited by Steam"


def test_sidecar_caido_no_avanza_la_cadena(engine, src, monkeypatch):
    def _raise(code, **kw):
        raise SidecarUnavailable("503")

    _chain(monkeypatch, [CODE_B, None])
    monkeypatch.setattr(sources, "resolve_demo", _raise)

    assert list(src.poll()) == []
    assert _user(engine).last_sharecode == CODE_A  # reintento en el prÃ³ximo ciclo


def test_demo_expirado_avanza_sin_descargar(engine, src, monkeypatch):
    def _raise(code, **kw):
        raise DemoExpired(code)

    _chain(monkeypatch, [CODE_B, None])
    monkeypatch.setattr(sources, "resolve_demo", _raise)
    downloads = _fake_download(monkeypatch)

    assert list(src.poll()) == []
    assert downloads == []
    assert _user(engine).last_sharecode == CODE_B  # la cadena no se estanca


def test_partida_ya_en_db_avanza_sin_llamar_al_gc(engine, src, monkeypatch):
    with Session(engine) as s:
        s.add(
            Match(
                match_id=match_id_str(decode_sharecode(CODE_B)),
                demo_file="x.dem",
                ingested_at=datetime.now(UTC).isoformat(),
            )
        )
        s.commit()

    _chain(monkeypatch, [CODE_B, None])
    resolves: list[str] = []
    monkeypatch.setattr(
        sources, "resolve_demo", lambda code, **kw: resolves.append(code) or ("http://x", None)
    )

    assert list(src.poll()) == []
    assert resolves == []  # dedup pre-GC
    assert _user(engine).last_sharecode == CODE_B


def test_dos_usuarios_misma_partida_un_solo_download(engine, src, monkeypatch):
    with Session(engine) as s:
        _add_user(s, STEAMID2, "Bruno")
        s.commit()

    # Ambas cadenas devuelven CODE_B y despuÃ©s "al dÃ­a".
    _chain(monkeypatch, [CODE_B, None, CODE_B, None])
    monkeypatch.setattr(
        sources, "resolve_demo", lambda code, **kw: ("http://replay/x.dem.bz2", 1730000000)
    )
    downloads = _fake_download(monkeypatch)

    demos = list(src.poll())

    assert len(demos) == 1  # el segundo dedupea por archivo ya descargado
    assert len(downloads) == 1
    assert _user(engine, STEAMID).last_sharecode == CODE_B
    assert _user(engine, STEAMID2).last_sharecode == CODE_B


def test_sin_api_key_ciclo_vacio(engine, tmp_path, monkeypatch):
    monkeypatch.setattr(sources, "sidecar_healthy", lambda **kw: True)
    src = SteamAutoSource(download_dir=tmp_path / "dl", api_key=None, request_spacing=0)
    src.api_key = None  # settings puede tener una key real en .env
    assert list(src.poll()) == []
    # El ciclo se salta entero, pero igual queda rastro de que el poller
    # sigue vivo: /autofetch/status no debe verse indistinguible de
    # "nunca corrió".
    u = _user(engine)
    assert u.last_polled_at is not None
    assert u.autofetch_error == "missing CS2_STEAM_API_KEY"


def test_sidecar_unhealthy_ciclo_vacio(engine, tmp_path, monkeypatch):
    monkeypatch.setattr(sources, "sidecar_healthy", lambda **kw: False)
    src = SteamAutoSource(download_dir=tmp_path / "dl", api_key="clave", request_spacing=0)
    assert list(src.poll()) == []
    u = _user(engine)
    assert u.last_polled_at is not None
    assert u.autofetch_error == "gc-sidecar unreachable"


def test_ciclo_ok_limpia_error_previo(engine, src, monkeypatch):
    with Session(engine) as s:
        u = s.get(User, STEAMID)
        u.autofetch_error = "gc-sidecar unreachable"
        s.commit()

    _chain(monkeypatch, [None])

    assert list(src.poll()) == []
    assert _user(engine).autofetch_error is None
