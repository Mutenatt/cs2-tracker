"""
Smoketest manual del render de clips 2D (infra/clips.py). No es un test de
pytest -- invoca render_clip() directo contra una partida/ronda ya ingerida
en la DB local y su .dem en disco, para inspección visual del MP4 resultante.

    python tools/render_clip_smoketest.py --db cs2.sqlite --demos demos \
        --match 003831319103881085310 --round 6 --out clips/_smoketest.mp4
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path


def _find_demo(demos_dir: Path, demo_file: str) -> Path | None:
    for p in demos_dir.rglob(demo_file):
        return p
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--demos", required=True, help="carpeta raíz donde buscar el .dem")
    ap.add_argument("--match", required=True, dest="match_id")
    ap.add_argument("--round", required=True, type=int, dest="round_num")
    ap.add_argument(
        "--steamid",
        default=None,
        help="jugador 'hero' del clip; por defecto el primero de la partida",
    )
    ap.add_argument("--out", default="clips/_smoketest.mp4")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    row = con.execute(
        "SELECT map, demo_file FROM matches WHERE match_id=?", (args.match_id,)
    ).fetchone()
    if row is None:
        raise SystemExit(f"partida no encontrada: {args.match_id}")
    map_name, demo_file = row

    steamid = args.steamid
    if steamid is None:
        steamid_row = con.execute(
            "SELECT steamid FROM match_players WHERE match_id=? ORDER BY steamid LIMIT 1",
            (args.match_id,),
        ).fetchone()
        if steamid_row is None:
            raise SystemExit("la partida no tiene match_players")
        steamid = steamid_row[0]
    name_row = con.execute("SELECT name FROM players WHERE steamid=?", (steamid,)).fetchone()
    player_name = (name_row[0] if name_row else None) or steamid

    roster = {}
    for (sid,) in con.execute(
        "SELECT steamid FROM match_players WHERE match_id=?", (args.match_id,)
    ):
        name_row = con.execute("SELECT name FROM players WHERE steamid=?", (sid,)).fetchone()
        roster[sid] = (name_row[0] if name_row else None) or sid

    con.close()

    dem_path = _find_demo(Path(args.demos), demo_file)
    if dem_path is None:
        raise SystemExit(f".dem no encontrado bajo {args.demos}: {demo_file}")

    from cs2tracker.infra.clips import render_clip

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    render_clip(
        dem_path=dem_path,
        map_name=map_name,
        round_num=args.round_num,
        steamid=steamid,
        label=f"Smoketest ronda {args.round_num + 1}",
        player_name=player_name,
        out_path=out_path,
        roster=roster,
    )
    print(
        f"[ok] {out_path} (mapa={map_name}, ronda={args.round_num}, hero={player_name}, "
        f"roster={len(roster)})"
    )


if __name__ == "__main__":
    main()
