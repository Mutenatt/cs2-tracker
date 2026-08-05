"""Tests del parser de nombres de line ups (scripts/upload_lineups.py)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from upload_lineups import (  # noqa: E402
    EXCLUDED_MAPS,
    FILES,
    assign_variants,
    humanize,
    parse_filename,
)


def parse(map_key, filename):
    return parse_filename(map_key, filename)


def test_gramatica_basica():
    lu = parse("de_cache", "smoke-tt-mid.mp4")
    assert (lu.grenade_label, lu.category) == ("Humo", "smoke")
    assert (lu.side, lu.to) == ("T", "Mid")


def test_todas_las_granadas():
    assert parse("de_cache", "moli-tt-mulita.mp4").category == "molotov"
    assert parse("de_cache", "deto-tt-backsideB.mp4").category == "he"
    assert parse("de_cache", "flash-tt-garage.mp4").category == "flash"
    # popflash es un alias de flash (naming viejo, sólo aparece en Mirage)
    assert parse("de_cache", "popflash-tt-garage.mp4").category == "flash"


def test_punto_suelto_en_el_nombre():
    """Dos archivos de Inferno tienen un punto de más; se trata como guion."""
    lu = parse("de_inferno", "smoke-ct-banana.-retake.mp4")
    assert (lu.side, lu.to, lu.qualifiers) == ("CT", "Banana", ["retake"])

    lu = parse("de_inferno", "smoke-ct-medio.spawn.mp4")
    assert (lu.side, lu.to, lu.qualifiers) == ("CT", "Medio", ["spawn"])


def test_cttt_es_ambos_bandos():
    lu = parse("de_dust2", "moli-cttt-siteA.mp4")
    assert (lu.side, lu.side_label, lu.to) == ("BOTH", "Ambos bandos", "Site A")


def test_retake_bando_vs_calificador():
    """En posición 2 es el bando; más adelante es contexto y el bando no cambia."""
    bando = parse("de_dust2", "moli-retake-cajaB.mp4")
    assert (bando.side, bando.to, bando.qualifiers) == ("RETAKE", "Caja B", [])

    contexto = parse("de_inferno", "moli-ct-default-retake.mp4")
    assert (contexto.side, contexto.qualifiers) == ("CT", ["retake"])


def test_desde_x_llena_el_origen():
    lu = parse("de_dust2", "moli-cttt-siteA-desdeRampa.mp4")
    assert (lu.to, lu.origin) == ("Site A", "Rampa")


def test_calificador_solo_si_el_token_coincide_exacto():
    """`spawnMID` y `oneguyB` son callouts, no calificadores."""
    assert parse("de_dust2", "smoke-tt-spawnMID.mp4").qualifiers == []
    assert parse("de_dust2", "smoke-tt-spawnMID.mp4").to == "Spawn MID"
    assert parse("de_inferno", "smoke-tt-oneguyB.mp4").qualifiers == []


def test_variante_numerica_cuelga_de_un_calificador():
    """En `mid-spawn1` el número es del line up, no del token `spawn`."""
    lu = parse("de_cache", "smoke-ct-mid-spawn1.mp4")
    assert (lu.to, lu.qualifiers) == ("Mid", ["spawn"])


def test_sufijos_easy_hard_pro():
    assert parse("de_cache", "smoke-tt-heavenEasy.mp4").variant == "Fácil"
    assert parse("de_cache", "smoke-tt-heavenHard.mp4").variant == "Difícil"
    assert parse("de_inferno", "moli-tt-triplepro.mp4").variant == "Pro"
    # y el callout queda limpio del sufijo
    assert parse("de_cache", "smoke-tt-heavenEasy.mp4").to == "Heaven"


def test_grupo_de_varios_se_numera():
    items = [parse("de_cache", f"smoke-ct-mid-spawn{n}.mp4") for n in (1, 2, 3, 4)]
    assign_variants(items)
    assert [i.variant for i in items] == ["Versión 1", "Versión 2", "Versión 3", "Versión 4"]


def test_line_up_unico_conserva_el_numero_en_el_callout():
    """`site3` no tiene hermanos: el 3 es parte del callout, no una versión."""
    items = [parse("de_nuke", "flash-tt-site3.mp4")]
    assign_variants(items)
    assert (items[0].to, items[0].variant) == ("Site 3", None)


def test_el_origen_separa_grupos():
    """ "Site A" y "Site A desde Rampa" son line ups distintos, no dos versiones."""
    items = [
        parse("de_dust2", "moli-cttt-siteA.mp4"),
        parse("de_dust2", "moli-cttt-siteA-desdeRampa.mp4"),
    ]
    assign_variants(items)
    assert [i.variant for i in items] == [None, None]


def test_overrides_de_callout_juntan_variantes():
    """`ductos` y `ducto` mapean al mismo destino, así que son dos versiones."""
    items = [
        parse("de_nuke", "smoke-tt-ducto-spawn.mp4"),
        parse("de_nuke", "smoke-tt-ductos-spawn2.mp4"),
    ]
    assign_variants(items)
    assert all(i.to == "Ducto" for i in items)
    assert [i.variant for i in items] == ["Versión 1", "Versión 2"]


def test_todo_calificador_deja_el_primero_como_destino():
    lu = parse("de_inferno", "moli-tt-default.mp4")
    assert (lu.to, lu.qualifiers) == ("Default", [])


def test_humanize():
    assert humanize("backsideB") == "Backside B"
    assert humanize("rampaCT") == "Rampa CT"
    assert humanize("site3") == "Site 3"
    assert humanize("spawnMID") == "Spawn MID"


def test_mirage_queda_fuera():
    assert "de_mirage" in EXCLUDED_MAPS
    assert "de_mirage" not in FILES


def test_las_listas_declaradas_parsean_enteras():
    for map_key, filenames in FILES.items():
        for filename in filenames:
            parse(map_key, filename)  # no debe levantar ValueError
