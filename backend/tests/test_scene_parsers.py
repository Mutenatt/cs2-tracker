"""Parseo puro de las fuentes del ranking (HLTV HTML / Valve markdown)."""

from pathlib import Path

from cs2tracker.infra.hltv_ranking import parse_hltv_ranking
from cs2tracker.infra.kick import pick_cs_category
from cs2tracker.infra.valve_ranking import parse_valve_standings

FIXTURES = Path(__file__).parent / "fixtures"


def _hltv_html() -> str:
    return (FIXTURES / "hltv_ranking.html").read_text(encoding="utf-8")


def _valve_md() -> str:
    return (FIXTURES / "valve_standings_global.md").read_text(encoding="utf-8")


def test_hltv_parsea_equipos_validos():
    teams = parse_hltv_ranking(_hltv_html())
    # 5 bloques en el fixture, 1 roto que se saltea.
    assert [t.name for t in teams] == ["Spirit", "Vitality", "9z Team", "FURIA"]
    assert [t.position for t in teams] == [1, 2, 3, 5]
    assert [t.points for t in teams] == [945, 802, 310, 287]


def test_hltv_change_sube_baja_neutro_nuevo():
    teams = parse_hltv_ranking(_hltv_html())
    by_name = {t.name: t for t in teams}
    assert by_name["Spirit"].change == 2
    assert by_name["Vitality"].change == 0  # "-" = sin cambio
    assert by_name["9z Team"].change is None  # "NEW TEAM"
    assert by_name["FURIA"].change == -3


def test_hltv_logo_solo_del_cdn():
    teams = parse_hltv_ranking(_hltv_html())
    by_name = {t.name: t for t in teams}
    assert by_name["Spirit"].logo_url == "https://img-cdn.hltv.org/teamlogo/abc123spirit.png"
    assert by_name["9z Team"].logo_url is None


def test_hltv_respeta_limit():
    teams = parse_hltv_ranking(_hltv_html(), limit=2)
    assert len(teams) == 2


def test_hltv_html_basura_devuelve_vacio():
    assert parse_hltv_ranking("<html><body><p>challenge</p></body></html>") == []
    assert parse_hltv_ranking("") == []


def test_valve_parsea_top10():
    teams = parse_valve_standings(_valve_md())
    # El fixture tiene 12 filas; limit por defecto = 10.
    assert len(teams) == 10
    assert teams[0].position == 1
    assert teams[0].name == "Spirit"
    assert teams[0].points == 1993
    assert teams[0].change is None
    assert teams[0].logo_url is None
    # Nombres con espacios se capturan enteros.
    assert teams[2].name == "Team Falcons"


def test_valve_ignora_header_y_separadora():
    teams = parse_valve_standings(_valve_md())
    assert all(t.name not in ("Team Name", "---------") for t in teams)


def test_valve_markdown_vacio_devuelve_vacio():
    assert parse_valve_standings("") == []
    assert parse_valve_standings("# solo un titulo\nsin tabla") == []


def test_kick_categoria_exacta_gana():
    cats = [
        {"id": 7, "name": "Counter-Strike 2"},
        {"id": 3, "name": "Counter-Strike"},
    ]
    assert pick_cs_category(cats) == 3


def test_kick_categoria_por_prefijo():
    cats = [
        {"id": 1, "name": "Chatting"},
        {"id": 7, "name": "Counter-Strike 2"},
    ]
    assert pick_cs_category(cats) == 7


def test_kick_sin_categoria_devuelve_none():
    assert pick_cs_category([{"id": 1, "name": "Fortnite"}]) is None
    assert pick_cs_category([]) is None
