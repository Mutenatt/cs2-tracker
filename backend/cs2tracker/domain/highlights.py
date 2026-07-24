"""
Detección de momentos destacados (clips): puntúa rondas por jugador a
partir de datos ya persistidos (kills por ronda, clutches). PURA -- recibe
listas ya resueltas (ver api/queries.py::highlight_moments), no toca la DB
ni el demo.
"""

from __future__ import annotations

MIN_KILLS_HIGHLIGHT = 3  # menos de 3 bajas en la ronda no es clip

SCORE_PER_KILL = 10
SCORE_PER_CLUTCH_ENEMY = 15


def _label(kills: int, clutch_enemies: int | None) -> str:
    if kills >= 5:
        base = "ACE"
    elif kills == 4:
        base = "4K"
    else:
        base = f"{kills}K"
    if clutch_enemies:
        return f"{base} · Clutch 1v{clutch_enemies}"
    return base


def score_moments(rondas: list[dict], top_n: int = 10) -> list[dict]:
    """`rondas`: [{match_id, round_num, steamid, kills, clutch_enemies}]
    donde clutch_enemies = enemigos al inicio de un clutch GANADO esa ronda
    (None si no hubo). Devuelve los top_n momentos ordenados por score
    desc: [{match_id, round_num, steamid, score, label}]."""
    out = []
    for r in rondas:
        kills = r.get("kills", 0)
        clutch = r.get("clutch_enemies")
        if kills < MIN_KILLS_HIGHLIGHT and not clutch:
            continue
        score = kills * SCORE_PER_KILL + (clutch or 0) * SCORE_PER_CLUTCH_ENEMY
        out.append(
            {
                "match_id": r["match_id"],
                "round_num": r["round_num"],
                "steamid": r["steamid"],
                "score": score,
                "label": _label(kills, clutch),
            }
        )
    out.sort(key=lambda m: -m["score"])
    return out[:top_n]
