"""
Genera una variante oscura/minimalista de los radares de los mapas del pool
Premier (frontend/public/radar/{map}_radar_psd.png -> escala de grises +
duotono azul-oscuro) para que infra/clips.py la use como fondo del clip en
vez del radar a color -- resalta más los puntos de jugadores/utilidad. Se
corre UNA VEZ a mano (no es parte del pipeline de render en producción) y
el resultado se commitea. Volver a correr solo si cambian los radares
fuente o se agregan mapas a maps.MAP_TRANSFORMS.

    python tools/build_dark_radars.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageEnhance, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cs2tracker.maps import MAP_TRANSFORMS  # noqa: E402

SRC_DIR = Path(__file__).resolve().parents[2] / "frontend" / "public" / "radar"
OUT_DIR = (
    Path(__file__).resolve().parents[1] / "cs2tracker" / "infra" / "clip_assets" / "radar_dark"
)

# Duotono: luminancia 0 (negro) -> DARK, luminancia 255 (blanco) -> LIGHT.
DARK = (11, 15, 24)
LIGHT = (88, 101, 128)


def _duotone(gray: Image.Image) -> Image.Image:
    """Mapea luminancia 0..255 a un degradé DARK->LIGHT por banda. Image.point
    con una lista de 768 valores mapea por banda sobre una imagen "RGB" (256
    valores por banda, en orden R,G,B) -- se triplica la imagen en L a RGB
    primero para poder aplicarle cada tercio del LUT a su banda."""
    lut: list[int] = []
    for band in range(3):
        d, light_v = DARK[band], LIGHT[band]
        lut.extend(int(d + (light_v - d) * (i / 255)) for i in range(256))
    rgb = Image.merge("RGB", (gray, gray, gray))
    return rgb.point(lut)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ok, missing = 0, []
    for map_name in sorted(MAP_TRANSFORMS):
        src = SRC_DIR / f"{map_name}_radar_psd.png"
        if not src.exists():
            missing.append(map_name)
            continue
        im = Image.open(src).convert("RGBA")
        alpha = im.getchannel("A")
        gray = ImageOps.grayscale(im.convert("RGB"))
        # El piso del radar fuente es apenas gris oscuro (~20-70/255) sobre
        # fondo transparente con RGB=0 -- sin estirar el rango, el duotono
        # queda casi todo pegado al extremo DARK y no se distingue del fondo
        # del frame. autocontrast estira ese rango angosto a 0..255 antes de
        # mapear al duotono, así el piso realmente contrasta.
        gray = ImageOps.autocontrast(gray, cutoff=1)
        gray = ImageEnhance.Contrast(gray).enhance(1.15)
        duo = _duotone(gray).convert("RGBA")
        duo.putalpha(alpha)
        duo.save(OUT_DIR / f"{map_name}.png")
        ok += 1

    print(f"[ok] {ok}/{len(MAP_TRANSFORMS)} radares oscuros generados en {OUT_DIR}")
    if missing:
        print(f"[faltan assets fuente]: {missing}")


if __name__ == "__main__":
    main()
