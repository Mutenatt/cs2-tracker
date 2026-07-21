"""Ranking oficial de Valve como fallback del de HLTV.

Valve publica sus standings regionales como datos abiertos en GitHub
(ValveSoftware/counter-strike_regional_standings): archivos markdown en
live/<año>/standings_global_YYYY_MM_DD.md, ~uno por mes. No hay un archivo
"latest", así que se lista el directorio del año vía la contents API y se
toma el más nuevo (el nombre con fecha ordena lexicográficamente).

Sin puntos de cambio de posición ni logos — el schema lo refleja con
change=None / logo_url=None y el frontend indica la fuente degradada.
"""

from __future__ import annotations

import re
from datetime import UTC, datetime

import httpx

from cs2tracker.infra.hltv_ranking import RankedTeam

_CONTENTS_URL = (
    "https://api.github.com/repos/ValveSoftware/counter-strike_regional_standings"
    "/contents/live/{year}"
)

# Fila de la tabla markdown: "| 1 | 1993 | Spirit | donk, ... |". El header
# no matchea porque "Standing" no es un dígito.
_ROW_RE = re.compile(r"^\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(.+?)\s*\|")


def parse_valve_standings(md: str, limit: int = 10) -> list[RankedTeam]:
    """Parsea el markdown de standings globales. Pura (testeable con fixture)."""
    teams: list[RankedTeam] = []
    for line in md.splitlines():
        m = _ROW_RE.match(line.strip())
        if m is None:
            continue
        teams.append(
            RankedTeam(
                position=int(m.group(1)),
                name=m.group(3),
                points=int(m.group(2)),
                change=None,
                logo_url=None,
            )
        )
        if len(teams) >= limit:
            break
    return teams


async def _latest_standings_url(client: httpx.AsyncClient) -> str | None:
    """URL raw del standings_global_* más reciente. Prueba el año en curso y,
    si todavía no hay archivos (enero), el anterior."""
    year = datetime.now(tz=UTC).year
    for y in (year, year - 1):
        resp = await client.get(_CONTENTS_URL.format(year=y))
        if resp.status_code != 200:
            continue
        candidates = [
            f
            for f in resp.json()
            if f.get("name", "").startswith("standings_global_") and f.get("download_url")
        ]
        if candidates:
            return max(candidates, key=lambda f: f["name"])["download_url"]
    return None


async def fetch_valve_top10() -> list[RankedTeam]:
    """Top 10 del ranking global de Valve. Best-effort: [] si GitHub falla."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = await _latest_standings_url(client)
            if url is None:
                return []
            resp = await client.get(url)
            if resp.status_code != 200:
                return []
            return parse_valve_standings(resp.text)
    except Exception:
        return []
