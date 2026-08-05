"""
Genera la metadata de los line ups a partir del nombre de cada .mp4.

Los clips ya viven en frontend/public/lineups/<mapa>/<archivo>.mp4 (carpeta
gitignoreada). Este script los lee, parsea el nombre según la gramática
`<granada>-<bando>-<callout>[-calificadores]` y emite dos JSON:

  * backend/manifest_lineups.json      -> metadata completa (título SEO,
    descripción redactada, tags). Artefacto versionado.
  * frontend/src/data/lineups.json     -> proyección slim que consume la vista
    Line Ups (sólo lo que se dibuja en la tarjeta).

MIRAGE queda excluida a propósito: se procesó a mano y su naming no sigue esta
gramática (el bando sale de la subcarpeta ct/ o t/, no del nombre).

Uso (desde cs2-tracker/backend):
    python scripts/upload_lineups.py             # genera los dos JSON
    python scripts/upload_lineups.py --check     # solo valida, no escribe
    python scripts/upload_lineups.py --maps de_cache de_nuke
    python scripts/upload_lineups.py --import-from "C:/Users/x/Videos/cs2-lineups"
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
REPO_DIR = BACKEND_DIR.parent

PUBLIC_LINEUPS = REPO_DIR / "frontend" / "public" / "lineups"
MANIFEST_OUT = BACKEND_DIR / "manifest_lineups.json"
FRONTEND_OUT = REPO_DIR / "frontend" / "src" / "data" / "lineups.json"

# Mirage no se toca: sus 24 entradas siguen hardcodeadas en LineUps.tsx.
EXCLUDED_MAPS = ("de_mirage",)

MAP_NAMES = {
    "de_cache": "Cache",
    "de_dust2": "Dust II",
    "de_inferno": "Inferno",
    "de_nuke": "Nuke",
}

# Carpeta de origen (la que grabó el usuario) -> clave de mapa. Sólo se usa con
# --import-from, para copiar clips de un mapa nuevo a public/lineups/.
SOURCE_DIRS = {
    "CACHE": "de_cache",
    "DUST 2": "de_dust2",
    "INFERNO": "de_inferno",
    "NUKE": "de_nuke",
}

# Token 0 del nombre -> (etiqueta en espanol, categoria que entiende la UI).
GRENADES = {
    "smoke": ("Humo", "smoke"),
    "moli": ("Molotov", "molotov"),
    "deto": ("Granada Explosiva", "he"),
    "flash": ("Cegadora", "flash"),
    "popflash": ("Cegadora", "flash"),
}

# Token 1 del nombre -> (side de la UI, etiqueta larga, etiqueta corta).
SIDES = {
    "tt": ("T", "T / Terrorista", "T"),
    "ct": ("CT", "CT / Counter-Terrorista", "CT"),
    "cttt": ("BOTH", "Ambos bandos", "T/CT"),
    "retake": ("RETAKE", "Situación de Retake", "Retake"),
}

# Tokens que describen el contexto del lanzamiento, no el destino. Ojo: sólo
# cuentan como calificador si el token coincide exacto -- "spawnMID" o
# "oneguyB" son callouts, no calificadores.
QUALIFIERS = ("spawn", "retake", "oneguy", "default")

# Sufijo final del callout -> etiqueta de variante.
VARIANT_SUFFIXES = {
    "easy": "Fácil",
    "facil": "Fácil",
    "hard": "Difícil",
    "dificil": "Difícil",
    "pro": "Pro",
}

# Palabras que el humanizador no debe capitalizar como palabra comun.
ACRONYMS = {"ct": "CT", "tt": "TT", "kz": "KZ", "he": "HE", "a": "A", "b": "B"}

# Overrides de callout por mapa: sólo donde el humanizador automático queda
# feo o ambiguo. La clave es el slug de callout ya sin calificadores ni sufijo
# de variante; el valor es lo que ve el usuario.
CALLOUTS: dict[str, dict[str, str]] = {
    "de_cache": {
        "afu-azul": "Afuera Azul",
        "basura-conector": "Basura -> Conector",
        "ct": "Spawn CT",
        "garage-basect": "Garage (base CT)",
        "garage-toyota": "Garage -> Toyota",
        "mediocemento": "Medio Cemento",
        "siteBToxico": "Site B (Tóxico)",
        "soloCombination": "Combinación en solitario",
        "sunroomHeadshoot": "Sunroom (Headshot)",
    },
    "de_dust2": {
        "cat": "Catwalk",
        "ct-mid": "CT Mid",
        "mediospawn": "Medio (desde spawn)",
        "previaoscuro": "Previa Oscuro",
        "puertaavanzado": "Puerta (avanzado)",
        "puertalong": "Puerta Long",
        "puerta-baranda": "Puerta -> Baranda",
        "puerta-previaOscuro": "Puerta (previa Oscuro)",
        "ventana-previaOscuro": "Ventana (previa Oscuro)",
    },
    "de_inferno": {
        "A": "Site A",
        "arcoVino": "Arco del Vino",
        "ataud": "Ataúd",
        "ct": "Spawn CT",
        "oneguyB": "Site B (un jugador)",
        "siteA-Long": "Site A (desde Long)",
    },
    "de_nuke": {
        "afue": "Afuera",
        "ducto": "Ducto",
        "ductos": "Ducto",
        "falsoducto": "Falso Ducto",
        "garageAfue": "Garage Afuera",
        "rampaprofunda": "Rampa Profunda",
        "rojaSecret": "Roja -> Secret",
        "secretRoja": "Secret -> Roja",
        "taxi-afu": "Taxi Afuera",
        "taxiRooft": "Taxi Rooftop",
    },
}

# Detalle escrito a mano, keyed por id. Se agrega como párrafo final de la
# descripción. Arranca vacío: el generador no inventa posiciones de mira.
NOTES: dict[str, str] = {}

SIDE_INTRO = {
    "T": "desde el lado Terrorista",
    "CT": "desde el lado Counter-Terrorista",
    "BOTH": "válido para ambos bandos",
    "RETAKE": "pensado para situaciones de retake",
}

QUALIFIER_PHRASES = {
    "spawn": (
        "Se ejecuta desde el punto de aparición, apenas arranca la ronda: "
        "no hace falta moverse del spawn."
    ),
    "retake": "Está pensado para retomar el site con la bomba ya plantada.",
    "oneguy": "Un solo jugador cubre toda la ejecución con esta granada.",
    "default": (
        "Es el lanzamiento por defecto de la ejecución, el que se tira en la mayoría de las rondas."
    ),
}

QUALIFIER_SHORT = {
    "spawn": "Desde el spawn.",
    "retake": "Para retake.",
    "oneguy": "Un solo jugador.",
    "default": "Lanzamiento default.",
}

VARIANT_PHRASES = {
    "Fácil": (
        "Esta es la versión fácil: pide menos precisión, a costa de algo de tiempo o de cobertura."
    ),
    "Difícil": (
        "Esta es la versión difícil: exige más precisión, pero sale más rápido "
        "o cubre mejor el ángulo."
    ),
    "Pro": "Esta es la versión pro: la ejecución más exigente de este line up.",
}

MAX_TITLE = 100
MAX_TAG_LEN = 30
MAX_TAGS_JOINED = 480

# Listas exactas por mapa, tal cual estan en disco. Se declaran a mano (en vez
# de escanear la carpeta) para que el script avise si falta o sobra un clip.
FILES: dict[str, list[str]] = {
    "de_cache": [
        "deto-tt-backsideB.mp4",
        "flash-tt-garage.mp4",
        "moli-ct-lona.mp4",
        "moli-ct-lona2.mp4",
        "moli-tt-backsideB.mp4",
        "moli-tt-default-headshotB.mp4",
        "moli-tt-mediocemento.mp4",
        "moli-tt-mulita.mp4",
        "moli-tt-siteBToxico.mp4",
        "moli-tt-sunroomHeadshoot.mp4",
        "smoke-ct-basura-conector.mp4",
        "smoke-ct-garage-basect.mp4",
        "smoke-ct-garage-toyota.mp4",
        "smoke-ct-garageA.mp4",
        "smoke-ct-mainB.mp4",
        "smoke-ct-mid-spawn1.mp4",
        "smoke-ct-mid-spawn2.mp4",
        "smoke-ct-mid-spawn3.mp4",
        "smoke-ct-mid-spawn4.mp4",
        "smoke-tt-afu-azul.mp4",
        "smoke-tt-calle.mp4",
        "smoke-tt-ct.mp4",
        "smoke-tt-defaultA.mp4",
        "smoke-tt-heavenEasy.mp4",
        "smoke-tt-heavenHard.mp4",
        "smoke-tt-leftMid.mp4",
        "smoke-tt-mainB.mp4",
        "smoke-tt-mid.mp4",
        "smoke-tt-rightMid.mp4",
        "smoke-tt-roja.mp4",
        "smoke-tt-siteB.mp4",
        "smoke-tt-siteCaja.mp4",
        "smoke-tt-siteCajaA.mp4",
        "smoke-tt-soloCombination.mp4",
    ],
    "de_dust2": [
        "flash-tt-baranda.mp4",
        "flash-tt-barandaOscuro.mp4",
        "flash-tt-fondo.mp4",
        "flash-tt-larga.mp4",
        "flash-tt-puertaFondo.mp4",
        "flash-tt-siteA.mp4",
        "moli-ct-baranda.mp4",
        "moli-cttt-siteA-desdeRampa.mp4",
        "moli-cttt-siteA.mp4",
        "moli-retake-arenaNinja.mp4",
        "moli-retake-cajaB.mp4",
        "moli-retake-cat.mp4",
        "moli-retake-siteB.mp4",
        "smoke-ct-fondo.mp4",
        "smoke-ct-fondo2.mp4",
        "smoke-ct-mediospawn.mp4",
        "smoke-ct-mid.mp4",
        "smoke-ct-oscuro.mp4",
        "smoke-ct-previaoscuro.mp4",
        "smoke-ct-puertaavanzado.mp4",
        "smoke-ct-suicida.mp4",
        "smoke-tt-CajaMid.mp4",
        "smoke-tt-auto.mp4",
        "smoke-tt-baranda.mp4",
        "smoke-tt-ct-mid.mp4",
        "smoke-tt-entryOscuro.mp4",
        "smoke-tt-long.mp4",
        "smoke-tt-puerta-baranda.mp4",
        "smoke-tt-puerta-previaOscuro.mp4",
        "smoke-tt-puertaOscuro.mp4",
        "smoke-tt-puertaOscuro2.mp4",
        "smoke-tt-puertalong.mp4",
        "smoke-tt-rampaCT.mp4",
        "smoke-tt-spawnMID.mp4",
        "smoke-tt-uperB.mp4",
        "smoke-tt-ventana-previaOscuro.mp4",
        "smoke-tt-ventanaB.mp4",
    ],
    "de_inferno": [
        "deto-tt-triple.mp4",
        "flash-ct-arena.mp4",
        "flash-ct-banana.mp4",
        "flash-tt-banana.mp4",
        "flash-tt-longA.mp4",
        "flash-tt-mid.mp4",
        "flash-tt-short.mp4",
        "flash-tt-tapete.mp4",
        "moli-ct-banana.mp4",
        "moli-ct-default-retake.mp4",
        "moli-tt-ataud.mp4",
        "moli-tt-default.mp4",
        "moli-tt-oscuroB.mp4",
        "moli-tt-tripleeasy.mp4",
        "moli-tt-triplepro.mp4",
        "smoke-ct-arena-retake.mp4",
        "smoke-ct-banana-spawn.mp4",
        "smoke-ct-banana.-retake.mp4",
        "smoke-ct-medio.spawn.mp4",
        "smoke-ct-mid-spawn.mp4",
        "smoke-tt-A-oneguy.mp4",
        "smoke-tt-arcoVino-oneguy.mp4",
        "smoke-tt-arena.mp4",
        "smoke-tt-ataud.mp4",
        "smoke-tt-camioneta.mp4",
        "smoke-tt-ct.mp4",
        "smoke-tt-long-spawn.mp4",
        "smoke-tt-long.mp4",
        "smoke-tt-mid-spawn.mp4",
        "smoke-tt-oneguyB.mp4",
        "smoke-tt-siteA-Long.mp4",
        "smoke-tt-siteA-pasarela.mp4",
    ],
    "de_nuke": [
        "deto-ct-radio.mp4",
        "deto-ct-radio2.mp4",
        "deto-tt-metal.mp4",
        "deto-tt-roja.mp4",
        "flash-ct-ducto.mp4",
        "flash-ct-heaven1.mp4",
        "flash-ct-heaven2.mp4",
        "flash-ct-heaven3.mp4",
        "flash-tt-rampa.mp4",
        "flash-tt-site3.mp4",
        "flash-tt-siteA.mp4",
        "moli-ct-defaultA.mp4",
        "moli-ct-ducto.mp4",
        "moli-ct-kz.mp4",
        "moli-ct-medio.mp4",
        "moli-ct-silo.mp4",
        "moli-ct-taxi.mp4",
        "moli-tt-cielo.mp4",
        "moli-tt-falsoducto.mp4",
        "moli-tt-kz1.mp4",
        "moli-tt-kz2.mp4",
        "moli-tt-kz3.mp4",
        "moli-tt-rafters.mp4",
        "moli-tt-roja.mp4",
        "moli-tt-secret.mp4",
        "moli-tt-siteA-default.mp4",
        "moli-tt-siteA-default2.mp4",
        "smoke-tt-afue1.mp4",
        "smoke-tt-afue2.mp4",
        "smoke-tt-cieloA.mp4",
        "smoke-tt-ducto-spawn.mp4",
        "smoke-tt-ductos-spawn2.mp4",
        "smoke-tt-garage-spawn.mp4",
        "smoke-tt-garage2.mp4",
        "smoke-tt-garageAfue.mp4",
        "smoke-tt-lockers.mp4",
        "smoke-tt-lockers2.mp4",
        "smoke-tt-lockers3.mp4",
        "smoke-tt-pasajeLockers.mp4",
        "smoke-tt-rampa.mp4",
        "smoke-tt-rampaprofunda.mp4",
        "smoke-tt-roja.mp4",
        "smoke-tt-rojaSecret.mp4",
        "smoke-tt-rojaSecret2.mp4",
        "smoke-tt-rojaSecret3.mp4",
        "smoke-tt-secretRoja1.mp4",
        "smoke-tt-secretRoja2.mp4",
        "smoke-tt-secretRoja3.mp4",
        "smoke-tt-secretRoja4.mp4",
        "smoke-tt-taxi-afu.mp4",
        "smoke-tt-taxi1.mp4",
        "smoke-tt-taxi2.mp4",
        "smoke-tt-taxiRooft-spawn.mp4",
        "smoke-tt-taxiRooft.mp4",
    ],
}


@dataclass
class Lineup:
    """Una entrada del manifest, ya parseada del nombre de archivo."""

    # Los campos de texto se completan en fill_texts(), después de que
    # assign_variants() haya podido comparar los line ups entre sí.

    id: str
    filename: str
    map_key: str
    map_name: str
    grenade: str
    grenade_label: str
    category: str
    side: str
    side_label: str
    side_short: str
    to: str
    origin: str | None
    qualifiers: list[str] = field(default_factory=list)
    variant: str | None = None
    title: str = ""
    short_title: str = ""
    description: str = ""
    notes: str | None = None
    tags: list[str] = field(default_factory=list)
    video: str = ""
    bytes: int = 0


# --------------------------------------------------------------------------
# Parsing del nombre de archivo
# --------------------------------------------------------------------------


def split_stem(filename: str) -> list[str]:
    """Tokeniza el nombre. Normaliza los puntos sueltos que quedaron en dos
    archivos de Inferno (`smoke-ct-banana.-retake`, `smoke-ct-medio.spawn`)
    tratandolos como separador, igual que el guion."""
    stem = Path(filename).stem
    return [t for t in stem.replace(".", "-").split("-") if t]


def humanize(token: str) -> str:
    """camelCase -> palabras separadas, con mayúscula inicial y respetando las
    siglas (`rampaCT` -> "Rampa CT", `site3` -> "Site 3")."""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", token)
    spaced = re.sub(r"(?<=[A-Za-z])(?=\d)", " ", spaced)
    out = []
    for word in spaced.split():
        acronym = ACRONYMS.get(word.lower())
        if acronym:
            out.append(acronym)
        elif word[0].isupper():
            out.append(word)
        else:
            out.append(word.capitalize())
    return " ".join(out)


def strip_variant(token: str) -> tuple[str, str | None, int | None]:
    """Separa el sufijo de variante del último token del callout.

    Devuelve (base, etiqueta de variante, número). El número se guarda aparte
    porque si el line up termina siendo único se vuelve a pegar al callout
    (`flash-tt-site3` -> "Site 3", no "Site versión 3")."""
    numeric = re.match(r"^(.*?)(\d+)$", token)
    if numeric and numeric.group(1):
        return numeric.group(1), None, int(numeric.group(2))
    for suffix, label in VARIANT_SUFFIXES.items():
        # Case-insensitive para cubrir camelCase (`heavenEasy`) y todo junto
        # en minusculas (`tripleeasy`).
        if len(token) > len(suffix) and token.lower().endswith(suffix):
            return token[: -len(suffix)], label, None
    return token, None, None


def parse_filename(map_key: str, filename: str) -> Lineup:
    """Aplica la gramática `<granada>-<bando>-<callout>[-calificadores]`."""
    tokens = split_stem(filename)
    if len(tokens) < 3:
        raise ValueError(f"nombre sin suficientes tokens: {filename}")

    grenade = tokens[0].lower()
    if grenade not in GRENADES:
        raise ValueError(f"granada desconocida '{tokens[0]}' en {filename}")
    grenade_label, category = GRENADES[grenade]

    side_token = tokens[1].lower()
    if side_token not in SIDES:
        raise ValueError(f"bando desconocido '{tokens[1]}' en {filename}")
    side, side_label, side_short = SIDES[side_token]

    # El sufijo de variante se saca ANTES de clasificar: puede colgar de un
    # calificador y no del callout (`mid-spawn1` -> Mid, desde spawn, v1).
    rest = tokens[2:]
    base, variant, number = strip_variant(rest[-1])
    if base:
        rest = [*rest[:-1], base]
    else:  # el token era sólo dígitos: se deja como estaba
        variant, number = None, None

    # El resto se parte en calificadores de contexto, origen (`desdeX`) y el
    # callout propiamente dicho.
    qualifiers: list[str] = []
    origin: str | None = None
    callout_tokens: list[str] = []
    for token in rest:
        low = token.lower()
        if low in QUALIFIERS:
            qualifiers.append(low)
        elif low.startswith("desde") and len(token) > len("desde"):
            origin = humanize(token[len("desde") :])
        else:
            callout_tokens.append(token)

    # `moli-ct-default-retake` es todo calificador: el primero pasa a ser el
    # destino para no quedarnos sin callout.
    if not callout_tokens and qualifiers:
        callout_tokens = [qualifiers.pop(0)]

    slug = "-".join(callout_tokens)
    override = CALLOUTS.get(map_key, {}).get(slug)
    to = override or " ".join(humanize(t) for t in callout_tokens)

    lineup = Lineup(
        id=f"{map_key}-{Path(filename).stem.replace('.', '-').lower()}",
        filename=filename,
        map_key=map_key,
        map_name=MAP_NAMES[map_key],
        grenade=grenade,
        grenade_label=grenade_label,
        category=category,
        side=side,
        side_label=side_label,
        side_short=side_short,
        to=to,
        origin=origin,
        qualifiers=qualifiers,
        variant=variant,
    )
    # `_number` es interno de assign_variants; no viaja al JSON.
    lineup._number = number  # type: ignore[attr-defined]
    return lineup


def assign_variants(items: list[Lineup]) -> None:
    """Numera las variantes de un mismo line up.

    Agrupa por (mapa, granada, bando, destino, calificadores) usando el destino
    ya resuelto, para que los overrides de CALLOUTS junten cosas como `ducto` y
    `ductos`. Grupo de uno = no hay variante; el número, si lo había, vuelve al
    callout."""
    groups: dict[tuple, list[Lineup]] = defaultdict(list)
    for lu in items:
        # El origen entra en la clave: "Site A" y "Site A desde Rampa" son dos
        # line ups distintos, no dos versiones del mismo.
        key = (lu.map_key, lu.grenade, lu.side, lu.to, lu.origin, tuple(sorted(lu.qualifiers)))
        groups[key].append(lu)

    for group in groups.values():
        if len(group) == 1:
            lu = group[0]
            number = getattr(lu, "_number", None)
            if number is not None and lu.variant is None:
                lu.to = f"{lu.to} {number}"
            continue
        group.sort(key=lambda x: (getattr(x, "_number", None) or 0, x.filename))
        for i, lu in enumerate(group, start=1):
            if lu.variant is None:  # Fácil/Difícil/Pro ganan sobre el número
                lu.variant = f"Versión {i}"


# --------------------------------------------------------------------------
# Textos
# --------------------------------------------------------------------------


def build_short_title(lu: Lineup) -> str:
    """Lo que renderiza la tarjeta: corto, sin el mapa ni el sufijo SEO."""
    suffix = f" ({lu.variant})" if lu.variant else ""
    return f"{lu.grenade_label} — {lu.to}{suffix}"


def build_title(lu: Lineup) -> str:
    suffix = f" ({lu.variant})" if lu.variant else ""
    title = f"{lu.grenade_label} {lu.to}{suffix} — {lu.map_name} {lu.side_short} | Line Up CS2"
    if len(title) > MAX_TITLE:
        title = title[: MAX_TITLE - 1].rstrip() + "…"
    return title


def build_description(lu: Lineup) -> str:
    """Prosa armada sólo con lo que el nombre de archivo realmente dice. No se
    inventan posiciones de mira ni tipo de tiro: eso no es deducible."""
    intro = f"Line up de {lu.grenade_label.lower()} en {lu.map_name}, {SIDE_INTRO[lu.side]}."

    context = [QUALIFIER_PHRASES[q] for q in lu.qualifiers if q in QUALIFIER_PHRASES]
    if not context:
        context = ["Se lanza desde la posición que muestra el clip al arrancar."]

    detail = [f"Objetivo: {lu.to}."]
    if lu.origin:
        detail.append(f"Se tira desde {lu.origin}.")
    if lu.variant:
        detail.append(
            VARIANT_PHRASES.get(
                lu.variant,
                f"Es la {lu.variant.lower()} de este line up; las demás cubren el "
                f"mismo objetivo desde otra posición.",
            )
        )
    detail.append(
        "Seguí en el video la posición de salida, la referencia de mira y el tipo "
        "de tiro exactos: el clip muestra la ejecución completa de principio a fin."
    )

    paragraphs = [intro, " ".join(context), " ".join(detail)]
    hand_written = NOTES.get(lu.id)
    if hand_written:
        paragraphs.append(hand_written)
    return "\n\n".join(paragraphs)


def build_notes(lu: Lineup) -> str | None:
    """Una línea para la tarjeta. None si no hay nada que agregar al título."""
    parts = [QUALIFIER_SHORT[q] for q in lu.qualifiers if q in QUALIFIER_SHORT]
    if lu.side == "BOTH":
        parts.insert(0, "Sirve en T y en CT.")
    return " ".join(parts) or None


def build_tags(lu: Lineup) -> list[str]:
    map_slug = lu.map_name.lower()
    side_tag = {
        "T": "terrorista",
        "CT": "counter terrorista",
        "BOTH": "ambos bandos",
        "RETAKE": "retake",
    }[lu.side]
    candidates = [
        "cs2",
        "counter strike 2",
        "cs2 lineups",
        "lineups cs2",
        map_slug,
        lu.map_key,
        f"lineups {map_slug}",
        f"{lu.grenade_label.lower()} {map_slug}",
        lu.grenade_label.lower(),
        lu.grenade,
        side_tag,
        lu.to.lower(),
        f"{lu.grenade_label.lower()} {lu.to.lower()}",
    ]

    tags: list[str] = []
    for tag in candidates:
        tag = re.sub(r"\s+", " ", tag.replace("->", " ")).strip()
        if not tag or len(tag) > MAX_TAG_LEN or tag in tags:
            continue
        if len(", ".join([*tags, tag])) > MAX_TAGS_JOINED:
            break
        tags.append(tag)
    return tags


def fill_texts(lu: Lineup, size: int) -> None:
    lu.short_title = build_short_title(lu)
    lu.title = build_title(lu)
    lu.description = build_description(lu)
    lu.notes = build_notes(lu)
    lu.tags = build_tags(lu)
    lu.video = f"/lineups/{lu.map_key}/{lu.filename}"
    lu.bytes = size


# --------------------------------------------------------------------------
# Lectura de disco y salidas
# --------------------------------------------------------------------------


def build_manifest(
    lineups_root: Path, maps: list[str]
) -> tuple[list[Lineup], list[str], list[str]]:
    """Parsea las listas declaradas y las contrasta contra el disco.

    Devuelve (entradas, faltantes, extras). Los faltantes se reportan pero no
    frenan la generación: el manifest describe lo que sí está."""
    entries: list[Lineup] = []
    missing: list[str] = []
    extra: list[str] = []

    for map_key in maps:
        declared = FILES[map_key]
        map_dir = lineups_root / map_key
        on_disk = {p.name for p in map_dir.glob("*.mp4")} if map_dir.is_dir() else set()

        parsed: list[Lineup] = []
        for filename in declared:
            path = map_dir / filename
            if not path.exists():
                missing.append(f"{map_key}/{filename}")
                print(f"[falta] {map_key}/{filename}")
                continue
            try:
                lu = parse_filename(map_key, filename)
            except ValueError as e:
                print(f"[skip] {map_key}/{filename}: {e}")
                continue
            lu._size = path.stat().st_size  # type: ignore[attr-defined]
            parsed.append(lu)

        assign_variants(parsed)
        for lu in parsed:
            fill_texts(lu, getattr(lu, "_size", 0))
        entries.extend(parsed)

        for name in sorted(on_disk - set(declared)):
            extra.append(f"{map_key}/{name}")
            print(f"[extra] {map_key}/{name} (en disco pero no declarado)")

        print(f"[info] {map_key}: {len(parsed)} line ups")

    return entries, missing, extra


def to_manifest_entry(lu: Lineup) -> dict:
    return {
        "id": lu.id,
        "map": lu.map_key,
        "map_name": lu.map_name,
        "grenade": lu.grenade,
        "grenade_label": lu.grenade_label,
        "category": lu.category,
        "side": lu.side,
        "side_label": lu.side_label,
        "to": lu.to,
        "from": lu.origin,
        "variant": lu.variant,
        "qualifiers": lu.qualifiers,
        "title": lu.title,
        "short_title": lu.short_title,
        "description": lu.description,
        "notes": lu.notes,
        "tags": lu.tags,
        "source_file": f"{lu.map_key}/{lu.filename}",
        "video": lu.video,
        "bytes": lu.bytes,
    }


def to_frontend_entry(lu: Lineup) -> dict:
    """Proyección slim: sólo lo que la tarjeta dibuja. Sin description ni tags,
    que no se renderizan y sumarían ~120 KB al bundle."""
    entry = {
        "id": lu.id,
        "title": lu.short_title,
        "side": lu.side,
        "category": lu.category,
        "to": lu.to,
        "video": lu.video,
    }
    if lu.origin:
        entry["from"] = lu.origin
    if lu.notes:
        entry["notes"] = lu.notes
    return entry


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(f"[ok] {path}")


# --------------------------------------------------------------------------
# Subida (copia a public/lineups)
# --------------------------------------------------------------------------


def publish_lineup(
    filename: str,
    map_key: str,
    src_dir: Path,
    dest_root: Path,
    *,
    force: bool = False,
    dry_run: bool = False,
) -> str:
    """Copia un clip a frontend/public/lineups/<mapa>/.

    Idempotente: si el destino ya existe con el mismo tamaño, no hace nada.
    Es la única función que escribe videos -- cambiar el destino (CDN, S3,
    YouTube) se hace acá y en ningún otro lado.

    Devuelve 'ok' | 'skip' | 'dry' | 'falta'."""
    src = src_dir / filename
    if not src.exists():
        return "falta"
    dest = dest_root / map_key / filename
    if dest.exists() and not force and dest.stat().st_size == src.stat().st_size:
        return "skip"
    if dry_run:
        return "dry"
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return "ok"


def import_videos(source_root: Path, dest_root: Path, maps: list[str], *, force: bool) -> None:
    """Copia los clips declarados desde la carpeta de grabaciones del usuario.
    Camino secundario: los 157 actuales ya se copiaron a mano."""

    counts: dict[str, int] = defaultdict(int)
    for folder, map_key in SOURCE_DIRS.items():
        if map_key not in maps:
            continue
        src_dir = source_root / folder
        for filename in FILES[map_key]:
            status = publish_lineup(filename, map_key, src_dir, dest_root, force=force)
            counts[status] += 1
            if status in ("ok", "falta"):
                print(f"[{status}] {map_key}/{filename}")
    print(f"[info] copiados: {dict(counts)}")


# --------------------------------------------------------------------------


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="CS2 Tracker - metadata de line ups")
    ap.add_argument(
        "--lineups",
        type=Path,
        default=PUBLIC_LINEUPS,
        help="carpeta publica con los .mp4 ya copiados",
    )
    ap.add_argument("--out", type=Path, default=MANIFEST_OUT, help="manifest completo")
    ap.add_argument("--frontend-out", type=Path, default=FRONTEND_OUT, help="JSON para la UI")
    ap.add_argument("--maps", nargs="+", choices=sorted(FILES), help="limita a estos mapas")
    ap.add_argument("--check", action="store_true", help="sólo valida, no escribe nada")
    ap.add_argument(
        "--import-from",
        type=Path,
        help="copia los .mp4 desde la carpeta de grabaciones antes de generar",
    )
    ap.add_argument("--force", action="store_true", help="--import-from: pisa el destino")
    args = ap.parse_args(argv)

    maps = args.maps or sorted(FILES)
    print(f"[info] mapas: {', '.join(maps)} (excluidos: {', '.join(EXCLUDED_MAPS)})")

    if args.import_from:
        import_videos(args.import_from, args.lineups, maps, force=args.force)

    entries, missing, extra = build_manifest(args.lineups, maps)
    print(f"[info] {len(entries)} line ups parseados, {len(missing)} faltan, {len(extra)} extra")

    if args.check:
        print("[fin] --check: no se escribió nada")
        return 1 if missing else 0

    write_json(
        args.out,
        {
            "generated_at": datetime.now(UTC).isoformat(),
            "excluded": list(EXCLUDED_MAPS),
            "count": len(entries),
            "lineups": [to_manifest_entry(lu) for lu in entries],
        },
    )

    by_map: dict[str, list[dict]] = defaultdict(list)
    for lu in entries:
        by_map[lu.map_key].append(to_frontend_entry(lu))
    write_json(args.frontend_out, dict(sorted(by_map.items())))

    print(f"[fin] {len(entries)} line ups")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
