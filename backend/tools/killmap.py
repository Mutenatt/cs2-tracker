"""
PROTOTIPO Fase 3: heatmap de muertes sobre el radar del mapa.

Lee las muertes (victim_x/y) de la DB, las proyecta a pixeles del radar con
los transforms de awpy y dibuja un heatmap sobre la imagen del mapa.

    python tools/killmap.py --db cs2.sqlite --match <id> --out killmap.png

Deps de prototipo (no del core): awpy, matplotlib.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from awpy.data import MAP_DATA  # noqa: E402
from awpy.data import PATH as AWPY_PATH  # noqa: E402


def to_radar(map_name, xs, ys):
    m = MAP_DATA[map_name]
    px = (np.asarray(xs) - m["pos_x"]) / m["scale"]
    py = (m["pos_y"] - np.asarray(ys)) / m["scale"]
    return px, py


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--match", required=True)
    ap.add_argument("--out", default="killmap.png")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    map_name = con.execute("SELECT map FROM matches WHERE match_id=?", (args.match,)).fetchone()[0]
    rows = con.execute(
        "SELECT victim_x, victim_y FROM kills WHERE match_id=? AND victim_x IS NOT NULL",
        (args.match,),
    ).fetchall()
    con.close()
    xs = [r[0] for r in rows]
    ys = [r[1] for r in rows]
    px, py = to_radar(map_name, xs, ys)

    radar = plt.imread(str(Path(AWPY_PATH) / "map" / f"{map_name}.png"))
    h, w = radar.shape[0], radar.shape[1]

    fig, ax = plt.subplots(figsize=(8, 8), dpi=120)
    ax.imshow(radar, extent=[0, w, h, 0], alpha=0.55)
    # heatmap de densidad de muertes
    ax.hist2d(px, py, bins=40, range=[[0, w], [0, h]], cmap="inferno", alpha=0.75, cmin=1)
    ax.scatter(px, py, s=14, c="white", edgecolors="black", linewidths=0.4, alpha=0.8)
    ax.set_xlim(0, w)
    ax.set_ylim(h, 0)
    ax.axis("off")
    ax.set_title(f"Muertes · {map_name} · {len(xs)} kills", color="#222")
    fig.tight_layout()
    fig.savefig(args.out, bbox_inches="tight")
    print(f"[ok] {args.out} ({len(xs)} muertes, radar {w}x{h})")


if __name__ == "__main__":
    main()
