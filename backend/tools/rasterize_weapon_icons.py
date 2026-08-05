"""
Rasteriza los SVG de armas/granadas (frontend/public/weapons/*.svg) a PNG
chicos que infra/clips.py pueda abrir con Pillow (Pillow no sabe leer SVG).
Se corre UNA VEZ a mano (no es parte del pipeline de render en producción,
no agrega dependencias al server) y los PNG resultantes se commitean.
Volver a correr solo si se agregan/cambian armas en frontend/public/weapons.

    python tools/rasterize_weapon_icons.py

Deps de este script (no del core): svglib, reportlab -- puro Python, sin
depender de la librería nativa Cairo (histórica dolor de cabeza en Windows).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from reportlab.graphics import renderPM
from svglib.svglib import svg2rlg

ICON_HEIGHT = 28  # alto en px del ícono final; el ancho se escala proporcional


def _to_transparent_silhouette(png_path: Path) -> None:
    """renderPM no respeta el fondo transparente pedido (queda RGB con fondo
    negro sólido) -- los íconos de origen son siluetas claras sobre fondo
    vacío, así que se recupera la transparencia real usando la luminancia de
    cada píxel como canal alfa (blanco/gris opaco -> alfa alto, negro -> alfa
    0), en vez de quedarnos con un fondo negro sólido."""
    im = Image.open(png_path).convert("RGB")
    gray = im.convert("L")
    out = Image.new("RGBA", im.size, (255, 255, 255, 0))
    out.putalpha(gray)
    out.save(png_path)


SRC_DIR = Path(__file__).resolve().parents[2] / "frontend" / "public" / "weapons"
OUT_DIR = Path(__file__).resolve().parents[1] / "cs2tracker" / "infra" / "clip_assets" / "weapons"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    svgs = sorted(SRC_DIR.glob("*.svg"))
    if not svgs:
        raise SystemExit(f"no se encontraron SVG en {SRC_DIR}")

    ok, failed = 0, []
    for svg_path in svgs:
        out_path = OUT_DIR / f"{svg_path.stem}.png"
        try:
            drawing = svg2rlg(str(svg_path))
            if drawing is None or drawing.height <= 0:
                raise ValueError("svg2rlg devolvió un drawing vacío")
            scale = ICON_HEIGHT / drawing.height
            drawing.width *= scale
            drawing.height *= scale
            drawing.scale(scale, scale)
            renderPM.drawToFile(drawing, str(out_path), fmt="PNG", bg=0x000000)
            _to_transparent_silhouette(out_path)
            ok += 1
        except Exception as exc:  # noqa: BLE001 -- se reporta al final, no corta el batch
            failed.append((svg_path.name, str(exc)))

    print(f"[ok] {ok}/{len(svgs)} íconos rasterizados en {OUT_DIR}")
    if failed:
        print(f"[fallaron {len(failed)}]:")
        for name, err in failed:
            print(f"  {name}: {err}")


if __name__ == "__main__":
    main()
