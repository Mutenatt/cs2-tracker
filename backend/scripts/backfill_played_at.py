"""
Backfill de matches.played_at para partidas ya ingeridas.

Reconstruye el sharecode desde el nombre del demo
(match730_<matchid>_<reservation>_<tv>.dem) y le pide el matchtime al
gc-sidecar. Solo funciona para demos cuyo filename tiene el triple REAL del
sharecode (los del auto-fetch siempre; los nombrados por el cliente de CS2
pueden fallar la validación del GC y quedan en NULL, sin romper nada).

Uso (con el sidecar corriendo):
    python scripts/backfill_played_at.py
"""

from __future__ import annotations

import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from cs2tracker.config import settings
from cs2tracker.db import Match, get_engine, init_db
from cs2tracker.infra.gc_client import DemoExpired, SidecarUnavailable, resolve_demo
from cs2tracker.infra.sharecode import DecodedSharecode, encode_sharecode

FILENAME_RE = re.compile(r"match\d+_(\d+)_(\d+)_(\d+)\.dem")


def _save_played_at(match_id: str, played_at: str, retries: int = 5) -> bool:
    """Sesión corta + reintentos: el worker de ingesta puede tener la DB
    tomada (SQLite = un escritor a la vez)."""
    for attempt in range(retries):
        try:
            with Session(get_engine()) as s:
                m = s.get(Match, match_id)
                if m is not None:
                    m.played_at = played_at
                    s.commit()
            return True
        except OperationalError:
            time.sleep(2.0 * (attempt + 1))
    return False


def main() -> int:
    init_db()
    filled = skipped = 0
    # Snapshot de pendientes en una sesión corta: NO retener la DB mientras
    # se habla con el GC (el worker necesita escribir en paralelo).
    with Session(get_engine()) as s:
        pending = [
            (m.match_id, m.map, m.demo_file)
            for m in s.execute(select(Match).where(Match.played_at.is_(None))).scalars()
        ]
    print(f"[info] {len(pending)} partidas sin played_at")

    for match_id, map_name, demo_file in pending:
        match_file = FILENAME_RE.search(demo_file or "")
        if not match_file:
            print(f"[skip] {match_id}: filename no parseable ({demo_file})")
            skipped += 1
            continue
        # Naming del auto-fetch: match730_<reservation>_<matchid>_<tv>.dem
        # (los nombrados por el cliente de CS2 no llevan el matchId real y el
        # GC los rechaza -> quedan como skip, esperado).
        decoded = DecodedSharecode(
            match_id=int(match_file.group(2)),
            reservation_id=int(match_file.group(1)),
            tv_port=int(match_file.group(3)),
        )
        code = encode_sharecode(decoded)
        try:
            _url, match_time = resolve_demo(code, base_url=settings.gc_sidecar_url)
        except (DemoExpired, SidecarUnavailable) as e:
            print(f"[skip] {match_id}: {type(e).__name__} ({e})")
            skipped += 1
            time.sleep(1.5)
            continue
        if not match_time:
            print(f"[skip] {match_id}: el GC no devolvió matchtime")
            skipped += 1
            continue
        played_at = datetime.fromtimestamp(match_time, UTC).isoformat()
        if _save_played_at(match_id, played_at):
            print(f"[ok] {match_id} ({map_name}) -> {played_at}")
            filled += 1
        else:
            print(f"[skip] {match_id}: DB bloqueada tras varios reintentos")
            skipped += 1
        time.sleep(1.5)  # respeto al GC
    print(f"[fin] {filled} backfilleadas, {skipped} sin fecha (reintentables)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
