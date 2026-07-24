"""
Render de clips 2D de radar (momentos destacados) a MP4 9:16 listo para
redes. Server-side puro: posiciones vía demoparser2 (parse_ticks SOLO del
rango de la ronda destacada -- no se construye la tabla positions global,
decisión del ROADMAP que se mantiene), frames con Pillow sobre el radar
PNG, encode H.264 vía el ffmpeg que trae imageio-ffmpeg (sin instalación
de sistema). Requiere que el .dem siga en disco.

El render 3D real (footage del juego) queda como fase futura: exige CS2
corriendo en Windows+GPU vía HLAE -- así funcionan allstar.gg y CS Demo
Manager -- y no puede correr headless en un server.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from cs2tracker import maps

# 64 ticks/s del server / TICK_STRIDE = fps del clip.
TICK_STRIDE = 8
FPS = 8
OUT_W, OUT_H = 1080, 1920  # 9:16 vertical (TikTok/Reels/Shorts)
RADAR_SIZE = 1000
RADAR_X = (OUT_W - RADAR_SIZE) // 2
RADAR_Y = 380
PAD_SECONDS = 3  # respiro antes del freezetime-end y después del round_end

BG = (10, 14, 21)
COLOR_T = (255, 138, 61)  # --signal
COLOR_CT = (63, 214, 255)  # --recon
COLOR_HERO = (70, 224, 160)  # --go
COLOR_TEXT = (233, 237, 243)
COLOR_DIM = (139, 149, 167)


def _font(size: int) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("arialbd.ttf", size)
    except OSError:
        return ImageFont.load_default(size)


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


def render_clip(
    dem_path: Path,
    map_name: str,
    round_num: int,
    steamid: str,
    label: str,
    player_name: str,
    out_path: Path,
) -> None:
    """Renderiza el MP4 del momento. Lanza ValueError si el demo/mapa no
    dan los datos mínimos (sin radar, ronda sin ticks)."""
    from demoparser2 import DemoParser
    from imageio_ffmpeg import get_ffmpeg_exe

    if not maps.has_radar(map_name):
        raise ValueError(f"mapa sin radar: {map_name}")
    radar_png = (
        Path(__file__).resolve().parents[3] / "frontend" / "public" / "maps" / f"{map_name}.png"
    )
    if not radar_png.exists():
        raise ValueError(f"radar no encontrado: {radar_png}")

    parser = DemoParser(str(dem_path))
    window = _round_window(parser, round_num)
    if window is None:
        raise ValueError(f"ronda {round_num} sin ticks de inicio/fin en el demo")
    start, end = window
    ticks = list(range(max(start, 0), end, TICK_STRIDE))
    df = parser.parse_ticks(["X", "Y", "team_num", "health"], ticks=ticks)
    if df is None or len(df) == 0:
        raise ValueError("sin posiciones para la ronda")

    deaths = parser.parse_event("player_death")
    killfeed: list[tuple[int, str, str]] = []  # (tick, attacker, victim)
    for _, r in deaths.iterrows():
        t = int(r["tick"])
        if start <= t <= end:
            killfeed.append((t, str(r.get("attacker_name") or "?"), str(r.get("user_name") or "?")))

    radar = Image.open(radar_png).convert("RGB").resize((RADAR_SIZE, RADAR_SIZE))
    font_title = _font(64)
    font_sub = _font(36)
    font_feed = _font(28)

    by_tick: dict[int, list] = {}
    for row in df.itertuples(index=False):
        by_tick.setdefault(int(row.tick), []).append(row)

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
            frame = Image.new("RGB", (OUT_W, OUT_H), BG)
            frame.paste(radar, (RADAR_X, RADAR_Y))
            d = ImageDraw.Draw(frame)

            d.text((OUT_W // 2, 120), label, font=font_title, fill=COLOR_TEXT, anchor="mm")
            d.text((OUT_W // 2, 200), player_name, font=font_sub, fill=COLOR_HERO, anchor="mm")
            d.text(
                (OUT_W // 2, 260),
                f"{map_name.upper()} · Ronda {round_num + 1}",
                font=font_sub,
                fill=COLOR_DIM,
                anchor="mm",
            )

            for row in rows:
                if getattr(row, "health", 0) is None or row.health <= 0:
                    continue
                uv = maps.to_radar_norm(map_name, float(row.X), float(row.Y))
                if uv is None:
                    continue
                px = RADAR_X + uv[0] * RADAR_SIZE
                py = RADAR_Y + uv[1] * RADAR_SIZE
                es_hero = str(row.steamid) == steamid
                r_dot = 14 if es_hero else 9
                color = COLOR_HERO if es_hero else (COLOR_T if row.team_num == 2 else COLOR_CT)
                d.ellipse((px - r_dot, py - r_dot, px + r_dot, py + r_dot), fill=color)
                if es_hero:
                    d.ellipse(
                        (px - r_dot - 4, py - r_dot - 4, px + r_dot + 4, py + r_dot + 4),
                        outline=COLOR_TEXT,
                        width=3,
                    )

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
            proc.stdin.write(frame.tobytes())
    finally:
        proc.stdin.close()
        proc.wait(timeout=120)

    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg falló (rc={proc.returncode})")
