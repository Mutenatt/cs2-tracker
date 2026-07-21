"""Noticias oficiales de CS2 vía Steam Web API (ISteamNews).

Endpoint público -- no necesita CS2_STEAM_API_KEY. Solo se filtran los posts
con tag "patchnotes" (el feed también trae anuncios de la comunidad no
oficiales, ej. "Call to Arms-ory").
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

CS2_APPID = 730
_BBCODE_RE = re.compile(r"\[/?\w+[^\]]*\]|\\")
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass
class SteamNewsItem:
    title: str
    summary: str
    url: str
    date: datetime


def _clean_summary(contents: str, max_len: int = 160) -> str:
    text = _BBCODE_RE.sub(" ", contents)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    if len(text) > max_len:
        text = text[:max_len].rsplit(" ", 1)[0] + "…"
    return text


async def fetch_cs2_news(count: int = 8) -> list[SteamNewsItem]:
    """Últimos parches oficiales de CS2. Best-effort: devuelve [] si Steam
    falla o tarda -- nunca rompe la request del caller."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/",
                params={"appid": CS2_APPID, "count": count, "maxlength": 300, "format": "json"},
            )
        raw_items = resp.json().get("appnews", {}).get("newsitems", [])
    except Exception:
        return []

    items = []
    for it in raw_items:
        if "patchnotes" not in it.get("tags", []):
            continue
        items.append(
            SteamNewsItem(
                title=it.get("title", ""),
                summary=_clean_summary(it.get("contents", "")),
                url=it.get("url", ""),
                date=datetime.fromtimestamp(it.get("date", 0), tz=UTC),
            )
        )
    return items
