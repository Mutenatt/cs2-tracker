"""Ranking mundial de equipos de HLTV (hltv.org/ranking/teams).

HLTV está detrás de Cloudflare: un GET pelado devuelve 403. curl_cffi con
impersonate de Chrome (TLS fingerprint real) suele pasar, pero igual hay que
ser MUY poco frecuente con las requests (el caller cachea horas — el ranking
rota una vez por semana). Best-effort: cualquier falla devuelve [] y el
caller degrada a la fuente alternativa (Valve).
"""

from __future__ import annotations

from dataclasses import dataclass

from selectolax.parser import HTMLParser

RANKING_URL = "https://www.hltv.org/ranking/teams/"


@dataclass
class RankedTeam:
    position: int
    name: str
    points: int
    # None = equipo nuevo en el ranking (HLTV muestra "NEW TEAM"); 0 = sin cambio.
    change: int | None
    logo_url: str | None


def _parse_change(text: str) -> int | None:
    text = text.strip()
    if text == "-":
        return 0
    try:
        return int(text)
    except ValueError:
        # "NEW TEAM" o cualquier cosa no numérica.
        return None


def parse_hltv_ranking(html: str, limit: int = 10) -> list[RankedTeam]:
    """Parsea el HTML del ranking. Pura (testeable con un fixture). Un bloque
    con markup inesperado se saltea en vez de romper todo el listado."""
    tree = HTMLParser(html)
    teams: list[RankedTeam] = []
    for node in tree.css(".ranked-team"):
        try:
            position_el = node.css_first(".position")
            name_el = node.css_first(".name")
            points_el = node.css_first(".points")
            if position_el is None or name_el is None or points_el is None:
                continue
            position = int(position_el.text().strip().lstrip("#"))
            # ".points" viene como "(945 points)".
            points = int(points_el.text().strip().strip("()").split()[0])
            change_el = node.css_first(".change")
            change = _parse_change(change_el.text()) if change_el is not None else 0

            logo_url = None
            for img in node.css("img"):
                src = img.attributes.get("src") or ""
                if "img-cdn.hltv.org/teamlogo" in src:
                    logo_url = src
                    break

            teams.append(
                RankedTeam(
                    position=position,
                    name=name_el.text().strip(),
                    points=points,
                    change=change,
                    logo_url=logo_url,
                )
            )
        except (ValueError, AttributeError):
            continue
        if len(teams) >= limit:
            break
    return teams


async def fetch_hltv_top10() -> list[RankedTeam]:
    """Top 10 del ranking mundial. Best-effort: [] si Cloudflare bloquea,
    hay timeout o el HTML no parsea (un 200 con challenge da 0 equipos y
    también degrada solo)."""
    try:
        from curl_cffi.requests import AsyncSession

        async with AsyncSession(impersonate="chrome") as session:
            resp = await session.get(RANKING_URL, timeout=15)
            if resp.status_code != 200:
                return []
            return parse_hltv_ranking(resp.text)
    except Exception:
        return []
