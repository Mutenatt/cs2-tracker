"""
Render de clips 2D de radar (momentos destacados) a MP4 9:16 listo para
redes. Server-side puro: posiciones/armas/ángulo de vista/eventos de
granada vía demoparser2 (parse_ticks/parse_event SOLO del rango de la
ronda destacada -- no se construye la tabla positions global, decisión del
ROADMAP que se mantiene), frames con Pillow sobre un radar oscuro
pre-generado (tools/build_dark_radars.py), íconos de arma/granada
pre-rasterizados (tools/rasterize_weapon_icons.py), encode H.264 vía el
ffmpeg que trae imageio-ffmpeg (sin instalación de sistema). Requiere que
el .dem siga en disco.

Utilidad (grenades): se prioriza el dato REAL del demo cuando existe --
`weapon_fire` da tick+posición exactos de lanzamiento (filtrando a los
weapon_* de granada), y `smokegrenade_expired`/`inferno_expire` dan tick
real de expiración (matcheados por entityid contra la detonación). Cuando
no hay match (arma soltada al morir, ronda cortada, etc.) se cae a la
aproximación heurística de domain/clip_utility.py::estimate_throw_tick +
una duración fija por arma (UTILITY_STYLE) -- son fallbacks, no el camino
principal. La trayectoria dibujada (línea + arco del ícono en vuelo) sigue
siendo una aproximación cosmética (línea recta con un offset senoidal para
simular parábola), no física real.

El render 3D real (footage del juego) queda como fase futura: exige CS2
corriendo en Windows+GPU vía HLAE -- así funcionan allstar.gg y CS Demo
Manager -- y no puede correr headless en un server.
"""

from __future__ import annotations

import math
import random
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from cs2tracker import maps
from cs2tracker.domain.clip_utility import estimate_throw_tick

# 64 ticks/s del server / TICK_STRIDE = fps del clip.
TICK_STRIDE = 8
FPS = 8
OUT_W, OUT_H = 1080, 1920  # 9:16 vertical (TikTok/Reels/Shorts)
RADAR_SIZE = 1000
RADAR_X = (OUT_W - RADAR_SIZE) // 2
RADAR_Y = 380
PAD_SECONDS = 3  # respiro antes del freezetime-end y después del round_end

BG = (10, 14, 21)
COLOR_T = (255, 158, 92)  # --signal, aclarado para las pills/texto
COLOR_CT = (110, 224, 255)  # --recon, aclarado para las pills/texto
COLOR_HERO = (70, 224, 160)  # --go
COLOR_TEXT = (233, 237, 243)
COLOR_DIM = (139, 149, 167)

_ASSETS_DIR = Path(__file__).resolve().parent / "clip_assets"
_ICONS_DIR = _ASSETS_DIR / "weapons"
_RADAR_DARK_DIR = _ASSETS_DIR / "radar_dark"

# Detonación/efecto -> clave de estilo (mismos valores que ya usaba `grenades`).
_DETONATE_EVENTS = {
    "flashbang_detonate": "flashbang",
    "hegrenade_detonate": "hegrenade",
    "inferno_startburn": "inferno",
    "smokegrenade_detonate": "smokegrenade",
    "decoy_detonate": "decoy",
}
# Expiración real -> misma clave de estilo, matcheada por entityid.
_EXPIRE_EVENTS = {
    "smokegrenade_expired": "smokegrenade",
    "inferno_expire": "inferno",
}
# weapon_fire trae "weapon_<nombre>" -- normalizado a la clave de efecto.
_THROW_WEAPON_TO_EFFECT = {
    "flashbang": "flashbang",
    "hegrenade": "hegrenade",
    "molotov": "inferno",
    "incgrenade": "inferno",
    "smokegrenade": "smokegrenade",
    "decoy": "decoy",
}
# Efecto -> ícono representativo para el sprite que "vuela" en la trayectoria
# (para "inferno" no existe un weapon_fire con ese nombre, así que se usa el
# ícono del arma que realmente se tira: molotov.svg).
_EFFECT_TO_ICON = {"inferno": "molotov"}
_MAX_THROW_LOOKBACK_TICKS = 5 * 64  # no buscar un weapon_fire más viejo que esto
_INFERNO_CLUSTER_GAP_TICKS = 3 * 64  # separa dos molotov del mismo thrower

# Estilo por tipo de granada. duration_s es un FALLBACK -- se usa el tick de
# expiración real (smoke/inferno) cuando hay match, ver _extract_grenades.
UTILITY_STYLE: dict[str, dict] = {
    "flashbang": {"color": (255, 255, 255), "max_alpha": 235, "radius": 60, "duration_s": 0.6},
    "hegrenade": {"color": (255, 120, 60), "max_alpha": 150, "radius": 38, "duration_s": 1.0},
    "inferno": {"color": (255, 90, 30), "max_alpha": 150, "radius": 45, "duration_s": 7.0},
    "smokegrenade": {"color": (205, 208, 214), "max_alpha": 150, "radius": 68, "duration_s": 18.0},
    "decoy": {"color": (220, 190, 120), "max_alpha": 110, "radius": 30, "duration_s": 18.0},
}
UTILITY_FADE_FRACTION = 0.25  # último 25% de la duración: fade-out lineal
UTILITY_GROWTH_FRACTION = 0.15  # primer 15%: el marcador crece hasta su radio final
GRENADE_ARC_HEIGHT = 70  # px de "altura" cosmética del arco en vuelo

VIEW_CONE_LENGTH = 17
VIEW_CONE_HALF_ANGLE = 24

DEATH_FADE_TICKS = TICK_STRIDE * 2  # ~0.25s de transición punto vivo -> X

ICON_HAND_HEIGHT = 16
ICON_FLIGHT_HEIGHT = 22


def _font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arialbd.ttf", size)
    except OSError:
        return ImageFont.load_default(size)


_ICON_CACHE: dict[tuple[str, int], Image.Image | None] = {}


def _weapon_icon(weapon: str | None, height: int) -> Image.Image | None:
    """Ícono PNG pre-rasterizado (tools/rasterize_weapon_icons.py), escalado
    y cacheado en memoria por (arma, alto). None si no hay asset (no revienta
    el render, simplemente no se dibuja nada para esa arma)."""
    if not weapon:
        return None
    key = (weapon, height)
    if key not in _ICON_CACHE:
        path = _ICONS_DIR / f"{weapon}.png"
        if path.exists():
            im = Image.open(path).convert("RGBA")
            ratio = height / im.height
            im = im.resize((max(1, int(im.width * ratio)), height))
            _ICON_CACHE[key] = im
        else:
            _ICON_CACHE[key] = None
    return _ICON_CACHE[key]


def _paste_icon(frame: Image.Image, icon: Image.Image | None, cx: float, cy: float) -> None:
    if icon is None:
        return
    x = int(cx - icon.width / 2)
    y = int(cy - icon.height / 2)
    frame.alpha_composite(icon, (x, y))


def _round_window(parser, round_num: int) -> tuple[int, int] | None:
    """(tick inicio, tick fin) de la ronda 0-based, con padding. None si el
    demo no expone freeze/round_end para esa ronda."""
    try:
        freeze = parser.parse_event("round_freeze_end", other=["total_rounds_played"])
        ends = parser.parse_event("round_end")
    except Exception:
        return None
    freeze_tick = None
    for _, r in freeze.iterrows():
        if int(r["total_rounds_played"]) == round_num:
            freeze_tick = int(r["tick"])
            break
    if freeze_tick is None:
        return None
    end_tick = None
    for _, r in ends.iterrows():
        t = int(r["tick"])
        if t > freeze_tick:
            end_tick = t
            break
    if end_tick is None:
        return None
    return freeze_tick - PAD_SECONDS * 64, end_tick + PAD_SECONDS * 64


def _dashed_line(
    d: ImageDraw.ImageDraw,
    p1: tuple[float, float],
    p2: tuple[float, float],
    fill: tuple[int, int, int, int],
    width: int = 2,
    dash: float = 12,
    gap: float = 9,
) -> None:
    x1, y1 = p1
    x2, y2 = p2
    dist = math.hypot(x2 - x1, y2 - y1)
    if dist < 1:
        return
    dx, dy = (x2 - x1) / dist, (y2 - y1) / dist
    step = dash + gap
    s = 0.0
    while s < dist:
        e = min(s + dash, dist)
        d.line(
            [(x1 + dx * s, y1 + dy * s), (x1 + dx * e, y1 + dy * e)],
            fill=fill,
            width=width,
        )
        s += step


def _draw_death_marker(
    d: ImageDraw.ImageDraw, cx: float, cy: float, alpha: int, r: int = 8
) -> None:
    color = (*COLOR_DIM, alpha)
    d.line([(cx - r, cy - r), (cx + r, cy + r)], fill=color, width=3)
    d.line([(cx - r, cy + r), (cx + r, cy - r)], fill=color, width=3)


def _draw_name_tag(
    d: ImageDraw.ImageDraw,
    font: ImageFont.ImageFont,
    cx: float,
    bottom_y: float,
    text: str,
    color: tuple[int, int, int],
    alpha: int = 190,
) -> None:
    """Pill semi-transparente con el nombre, apoyada justo arriba de
    `bottom_y` (el punto/marcador del jugador). El alpha bajo hace que dos
    etiquetas superpuestas se mezclen en vez de taparse."""
    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad_x, pad_y = 9, 4
    w, h = tw + pad_x * 2, th + pad_y * 2
    x0, y0 = cx - w / 2, bottom_y - h
    x1, y1 = cx + w / 2, bottom_y
    d.rounded_rectangle([x0, y0, x1, y1], radius=7, fill=(*BG, alpha))
    text_alpha = min(255, int(alpha * 1.3))
    d.text((cx, (y0 + y1) / 2), text, font=font, fill=(*color, text_alpha), anchor="mm")


def _draw_view_cone(
    d: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    yaw_deg: float,
    color: tuple[int, int, int],
    alpha: int = 60,
) -> None:
    """Cuña sutil orientada al ángulo de vista (yaw). El mundo usa Y hacia
    "arriba" pero el radar proyecta v = (pos_y - y)/scale (eje v invertido
    respecto de y) -- se refleja la componente y del vector de dirección
    antes de pasarlo a coordenadas de pantalla (donde y ya crece hacia
    abajo), así el cono apunta al mismo lugar que el jugador está mirando."""
    rad = math.radians(yaw_deg)
    dx, dy = math.cos(rad), -math.sin(rad)
    angle = math.degrees(math.atan2(dy, dx))
    box = (
        cx - VIEW_CONE_LENGTH,
        cy - VIEW_CONE_LENGTH,
        cx + VIEW_CONE_LENGTH,
        cy + VIEW_CONE_LENGTH,
    )
    d.pieslice(
        box,
        angle - VIEW_CONE_HALF_ANGLE,
        angle + VIEW_CONE_HALF_ANGLE,
        fill=(*color, alpha),
    )


def _blob_offsets(seed: int, n: int, spread: float) -> list[tuple[float, float]]:
    rnd = random.Random(seed)
    return [(rnd.uniform(-spread, spread), rnd.uniform(-spread, spread)) for _ in range(n)]


def _utility_progress(g: dict, tick: int) -> tuple[float, int]:
    """(radio_factor 0..1, alpha) para el tick actual dentro de la ventana de
    detonación->fin, aplicando crecimiento al inicio y fade-out al final."""
    style = g["style"]
    elapsed = tick - g["tick"]
    duration = g["duration_ticks"]
    growth_ticks = max(1, int(duration * UTILITY_GROWTH_FRACTION))
    fade_ticks = max(1, int(duration * UTILITY_FADE_FRACTION))
    remaining = duration - elapsed
    radius_factor = (
        min(1.0, 0.35 + 0.65 * (elapsed / growth_ticks)) if elapsed < growth_ticks else 1.0
    )
    if remaining <= fade_ticks:
        alpha = max(0, int(style["max_alpha"] * remaining / fade_ticks))
    else:
        alpha = style["max_alpha"]
    return radius_factor, alpha


def _draw_utility_effect(d: ImageDraw.ImageDraw, frame: Image.Image, g: dict, tick: int) -> None:
    style = g["style"]
    weapon = g["effect_weapon"]
    radius_factor, alpha = _utility_progress(g, tick)
    if alpha <= 0:
        return
    cx, cy = g["target"]
    r = style["radius"] * radius_factor
    color = style["color"]

    if weapon == "smokegrenade":
        pad = int(r * 1.3) + 8
        layer = Image.new("RGBA", (pad * 2, pad * 2), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        for ox, oy in _blob_offsets(g["seed"], 4, r * 0.35):
            bx, by = pad + ox, pad + oy
            br = r * 0.62
            ld.ellipse((bx - br, by - br, bx + br, by + br), fill=(*color, min(255, alpha)))
        layer = layer.filter(ImageFilter.GaussianBlur(radius=max(2, int(r * 0.12))))
        frame.alpha_composite(layer, (int(cx - pad), int(cy - pad)))
        return

    if weapon == "inferno":
        for ox, oy in _blob_offsets(g["seed"], 3, r * 0.4):
            br = r * 0.65
            bx, by = cx + ox, cy + oy
            d.ellipse((bx - br, by - br, bx + br, by + br), fill=(*color, alpha))
        return

    # flashbang / hegrenade / decoy: un único círculo.
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(*color, alpha))


def _extract_grenades(parser, map_name: str, start: int, end: int) -> list[dict]:
    """Granadas detonadas en la ventana [start, end], con origen/tick de
    lanzamiento y duración reales cuando el demo los expone (weapon_fire /
    *_expired / *_expire), con fallback heurístico si no hay match."""
    detonations: list[dict] = []
    for event_name, weapon in _DETONATE_EVENTS.items():
        try:
            df = parser.parse_event(event_name)
        except Exception:
            continue
        for _, r in df.iterrows():
            t = int(r["tick"])
            if not (start <= t <= end):
                continue
            detonations.append(
                {
                    "entityid": r.get("entityid"),
                    "tick": t,
                    "thrower": str(r["user_steamid"]) if r.get("user_steamid") else None,
                    "weapon": weapon,
                    "x": r.get("x"),
                    "y": r.get("y"),
                }
            )

    # inferno_startburn dispara varias veces por molotov (focos de fuego que
    # se propagan) -- se agrupan por thrower + cercanía temporal, quedándose
    # con la primera fila de cada racha como "la" detonación de ese molotov.
    infernos = sorted(
        (d for d in detonations if d["weapon"] == "inferno"),
        key=lambda d: (d["thrower"], d["tick"]),
    )
    clustered_infernos: list[dict] = []
    last_by_thrower: dict[str | None, int] = {}
    for d in infernos:
        prev = last_by_thrower.get(d["thrower"])
        if prev is not None and d["tick"] - prev <= _INFERNO_CLUSTER_GAP_TICKS:
            last_by_thrower[d["thrower"]] = d["tick"]
            continue  # parte de la misma racha, no es un molotov nuevo
        clustered_infernos.append(d)
        last_by_thrower[d["thrower"]] = d["tick"]
    detonations = [d for d in detonations if d["weapon"] != "inferno"] + clustered_infernos

    expires: dict[str, list[dict]] = {"smokegrenade": [], "inferno": []}
    for event_name, weapon in _EXPIRE_EVENTS.items():
        try:
            df = parser.parse_event(event_name)
        except Exception:
            continue
        for _, r in df.iterrows():
            expires[weapon].append(
                {
                    "entityid": r.get("entityid"),
                    "tick": int(r["tick"]),
                    "thrower": str(r["user_steamid"]) if r.get("user_steamid") else None,
                }
            )

    try:
        fires = parser.parse_event("weapon_fire", player=["X", "Y", "Z"])
    except Exception:
        fires = None
    throws: list[dict] = []
    if fires is not None:
        for _, r in fires.iterrows():
            raw = str(r.get("weapon") or "")
            name = raw.removeprefix("weapon_")
            effect = _THROW_WEAPON_TO_EFFECT.get(name)
            if effect is None:
                continue
            throws.append(
                {
                    "tick": int(r["tick"]),
                    "thrower": str(r["user_steamid"]) if r.get("user_steamid") else None,
                    "effect_weapon": effect,
                    "icon": _EFFECT_TO_ICON.get(effect, name),
                    "x": r.get("user_X"),
                    "y": r.get("user_Y"),
                }
            )

    prepared: list[dict] = []
    for idx, det in enumerate(detonations):
        style = UTILITY_STYLE.get(det["weapon"])
        if style is None or det["x"] is None or det["y"] is None:
            continue
        uv = maps.to_radar_norm(map_name, float(det["x"]), float(det["y"]))
        if uv is None:
            continue
        target = (RADAR_X + uv[0] * RADAR_SIZE, RADAR_Y + uv[1] * RADAR_SIZE)

        # Duración: real si hay un *_expired/*_expire matcheable, si no fija.
        duration_ticks = max(1, int(style["duration_s"] * 64))
        candidates = expires.get(det["weapon"], [])
        match = None
        if det["weapon"] == "smokegrenade" and det["entityid"] is not None:
            match = next((e for e in candidates if e["entityid"] == det["entityid"]), None)
        elif det["weapon"] == "inferno" and det["thrower"] is not None:
            after = [
                e for e in candidates if e["thrower"] == det["thrower"] and e["tick"] > det["tick"]
            ]
            match = min(after, key=lambda e: e["tick"]) if after else None
        if match is not None and match["tick"] > det["tick"]:
            duration_ticks = match["tick"] - det["tick"]

        # Origen: real si hay un weapon_fire cercano del mismo thrower+tipo.
        origin = None
        origin_tick = None
        icon_name = _EFFECT_TO_ICON.get(det["weapon"], det["weapon"])
        if det["thrower"] is not None:
            candidates_fire = [
                f
                for f in throws
                if f["thrower"] == det["thrower"]
                and f["effect_weapon"] == det["weapon"]
                and det["tick"] - _MAX_THROW_LOOKBACK_TICKS <= f["tick"] <= det["tick"]
                and f["x"] is not None
                and f["y"] is not None
            ]
            if candidates_fire:
                best = max(candidates_fire, key=lambda f: f["tick"])
                ouv = maps.to_radar_norm(map_name, float(best["x"]), float(best["y"]))
                if ouv is not None:
                    origin = (RADAR_X + ouv[0] * RADAR_SIZE, RADAR_Y + ouv[1] * RADAR_SIZE)
                    origin_tick = best["tick"]
                    icon_name = best["icon"]
        if origin is None:
            origin_tick = estimate_throw_tick(det["tick"], det["weapon"], start)

        prepared.append(
            {
                "tick": det["tick"],
                "thrower": det["thrower"],
                "throw_tick": origin_tick,
                "duration_ticks": duration_ticks,
                "target": target,
                "origin": origin,  # None -> se resuelve con by_tick como antes
                "style": style,
                "effect_weapon": det["weapon"],
                "icon_name": icon_name,
                "seed": (det["entityid"] or 0) * 1000 + det["tick"] + idx,
            }
        )
    return prepared


def render_clip(
    dem_path: Path,
    map_name: str,
    round_num: int,
    steamid: str,
    label: str,
    player_name: str,
    out_path: Path,
    roster: dict[str, str] | None = None,
) -> None:
    """Renderiza el MP4 del momento. Lanza ValueError si el demo/mapa no
    dan los datos mínimos (sin radar, ronda sin ticks).

    roster: {steamid: nombre} de la partida, para las etiquetas flotantes."""
    from demoparser2 import DemoParser
    from imageio_ffmpeg import get_ffmpeg_exe

    roster = roster or {}

    if not maps.has_radar(map_name):
        raise ValueError(f"mapa sin radar: {map_name}")
    radar_png = _RADAR_DARK_DIR / f"{map_name}.png"
    if not radar_png.exists():
        raise ValueError(f"radar oscuro no encontrado: {radar_png}")

    parser = DemoParser(str(dem_path))
    window = _round_window(parser, round_num)
    if window is None:
        raise ValueError(f"ronda {round_num} sin ticks de inicio/fin en el demo")
    start, end = window
    start = max(start, 0)
    ticks = list(range(start, end, TICK_STRIDE))
    df = parser.parse_ticks(
        ["X", "Y", "team_num", "health", "active_weapon_name", "yaw"], ticks=ticks
    )
    if df is None or len(df) == 0:
        raise ValueError("sin posiciones para la ronda")

    by_tick: dict[int, list] = {}
    for row in df.itertuples(index=False):
        by_tick.setdefault(int(row.tick), []).append(row)

    deaths_raw = parser.parse_event("player_death", player=["X", "Y", "Z"])
    killfeed: list[tuple[int, str, str]] = []  # (tick, attacker, victim)
    death_info: dict[str, tuple[int, float, float, str | None]] = {}
    for _, r in deaths_raw.iterrows():
        t = int(r["tick"])
        if not (start <= t <= end):
            continue
        killfeed.append((t, str(r.get("attacker_name") or "?"), str(r.get("user_name") or "?")))
        vic = r.get("user_steamid")
        vx, vy = r.get("user_X"), r.get("user_Y")
        if vic is None or vx is None or vy is None:
            continue
        sid = str(vic)
        if sid in death_info:
            continue  # solo puede morir una vez por ronda
        uv = maps.to_radar_norm(map_name, float(vx), float(vy))
        if uv is None:
            continue
        death_info[sid] = (t, uv[0], uv[1], roster.get(sid))

    prepared_grenades = _extract_grenades(parser, map_name, start, end)
    # Resolver el origen aproximado de las que no tuvieron weapon_fire real,
    # igual que antes: posición muestreada del thrower cerca del throw_tick.
    for g in prepared_grenades:
        if g["origin"] is not None or not ticks or g["thrower"] is None:
            continue
        closest = min(ticks, key=lambda t: abs(t - g["throw_tick"]))
        for r in by_tick.get(closest, []):
            if str(r.steamid) == g["thrower"]:
                ouv = maps.to_radar_norm(map_name, float(r.X), float(r.Y))
                if ouv is not None:
                    g["origin"] = (RADAR_X + ouv[0] * RADAR_SIZE, RADAR_Y + ouv[1] * RADAR_SIZE)
                break

    radar = Image.open(radar_png).convert("RGBA").resize((RADAR_SIZE, RADAR_SIZE))
    font_title = _font(64)
    font_sub = _font(36)
    font_feed = _font(28)
    font_tag = _font(24)

    ffmpeg = get_ffmpeg_exe()
    proc = subprocess.Popen(
        [
            ffmpeg,
            "-y",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{OUT_W}x{OUT_H}",
            "-r",
            str(FPS),
            "-i",
            "-",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-pix_fmt",
            "yuv420p",
            str(out_path),
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    assert proc.stdin is not None

    try:
        for tick in ticks:
            rows = by_tick.get(tick)
            if not rows:
                continue
            frame = Image.new("RGBA", (OUT_W, OUT_H), (*BG, 255))
            frame.paste(radar, (RADAR_X, RADAR_Y))
            d = ImageDraw.Draw(frame, "RGBA")

            d.text((OUT_W // 2, 120), label, font=font_title, fill=COLOR_TEXT, anchor="mm")
            d.text((OUT_W // 2, 200), player_name, font=font_sub, fill=COLOR_HERO, anchor="mm")
            d.text(
                (OUT_W // 2, 260),
                f"{map_name.upper()} · Ronda {round_num + 1}",
                font=font_sub,
                fill=COLOR_DIM,
                anchor="mm",
            )

            # Capa 1: utilidad -- granada en vuelo (línea guía + ícono
            # interpolado con arco cosmético) y efecto de detonación.
            for g in prepared_grenades:
                end_tick = g["tick"] + g["duration_ticks"]
                if tick < g["throw_tick"] or tick > end_tick:
                    continue
                if g["origin"] is not None and g["throw_tick"] <= tick <= g["tick"]:
                    flight = g["tick"] - g["throw_tick"]
                    t = (tick - g["throw_tick"]) / flight if flight > 0 else 1.0
                    ox, oy = g["origin"]
                    tx, ty = g["target"]
                    ix = ox + (tx - ox) * t
                    iy = oy + (ty - oy) * t - GRENADE_ARC_HEIGHT * math.sin(math.pi * t)
                    _dashed_line(d, g["origin"], g["target"], fill=(*g["style"]["color"], 90))
                    icon = _weapon_icon(g["icon_name"], ICON_FLIGHT_HEIGHT)
                    if icon is not None:
                        _paste_icon(frame, icon, ix, iy)
                    else:
                        d.ellipse(
                            (ix - 5, iy - 5, ix + 5, iy + 5), fill=(*g["style"]["color"], 220)
                        )
                if tick >= g["tick"]:
                    _draw_utility_effect(d, frame, g, tick)

            # Capa 2: jugadores vivos (cono de vista + punto + ícono de
            # arma/granada en mano + etiqueta de nombre), con transición
            # suave hacia el marcador de muerte.
            for row in rows:
                sid = str(row.steamid)
                death = death_info.get(sid)
                dtick = death[0] if death else None
                if dtick is not None and tick >= dtick + DEATH_FADE_TICKS:
                    continue  # ya terminó de desvanecerse, la X vive en Capa 3
                if getattr(row, "health", 0) is None or row.health <= 0:
                    if dtick is None or tick < dtick:
                        continue
                dot_alpha = 255
                if dtick is not None and tick >= dtick:
                    dot_alpha = max(0, 255 - int(255 * (tick - dtick) / DEATH_FADE_TICKS))
                if dot_alpha <= 0:
                    continue

                uv = maps.to_radar_norm(map_name, float(row.X), float(row.Y))
                if uv is None:
                    continue
                px = RADAR_X + uv[0] * RADAR_SIZE
                py = RADAR_Y + uv[1] * RADAR_SIZE
                es_hero = sid == steamid
                r_dot = 14 if es_hero else 9
                color = COLOR_HERO if es_hero else (COLOR_T if row.team_num == 2 else COLOR_CT)

                yaw = getattr(row, "yaw", None)
                if yaw is not None and dot_alpha > 120:
                    _draw_view_cone(d, px, py, float(yaw), color, alpha=int(60 * dot_alpha / 255))

                d.ellipse(
                    (px - r_dot, py - r_dot, px + r_dot, py + r_dot), fill=(*color, dot_alpha)
                )
                if es_hero:
                    d.ellipse(
                        (px - r_dot - 4, py - r_dot - 4, px + r_dot + 4, py + r_dot + 4),
                        outline=(*COLOR_TEXT, dot_alpha),
                        width=3,
                    )
                weapon = getattr(row, "active_weapon_name", None)
                if dot_alpha > 120:
                    icon = _weapon_icon(weapon, ICON_HAND_HEIGHT)
                    if icon is not None:
                        _paste_icon(frame, icon, px + r_dot + 10, py)
                name = roster.get(sid)
                if name:
                    _draw_name_tag(
                        d,
                        font_tag,
                        px,
                        py - r_dot - 6,
                        name,
                        color,
                        alpha=int(190 * dot_alpha / 255),
                    )

            # Capa 3: jugadores muertos (marcador X, con fade-in ya cubierto
            # arriba mientras dtick <= tick < dtick+DEATH_FADE_TICKS -- acá
            # solo el estado estable posterior).
            for _sid, (dtick, du, dv, name) in death_info.items():
                if tick < dtick:
                    continue
                px = RADAR_X + du * RADAR_SIZE
                py = RADAR_Y + dv * RADAR_SIZE
                x_alpha = (
                    min(220, int(220 * (tick - dtick) / DEATH_FADE_TICKS))
                    if tick < dtick + DEATH_FADE_TICKS
                    else 220
                )
                _draw_death_marker(d, px, py, alpha=x_alpha)
                if name:
                    tag_alpha = int(110 * x_alpha / 220)
                    _draw_name_tag(d, font_tag, px, py - 8 - 6, name, COLOR_DIM, alpha=tag_alpha)

            recientes = [k for k in killfeed if k[0] <= tick][-4:]
            for i, (_, atk, vic) in enumerate(recientes):
                d.text(
                    (OUT_W // 2, RADAR_Y + RADAR_SIZE + 60 + i * 44),
                    f"{atk}  ×  {vic}",
                    font=font_feed,
                    fill=COLOR_TEXT,
                    anchor="mm",
                )

            d.text(
                (OUT_W // 2, OUT_H - 80),
                "cStats://SISTEMA",
                font=font_sub,
                fill=COLOR_DIM,
                anchor="mm",
            )
            proc.stdin.write(frame.convert("RGB").tobytes())
    finally:
        proc.stdin.close()
        proc.wait(timeout=120)

    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg falló (rc={proc.returncode})")
