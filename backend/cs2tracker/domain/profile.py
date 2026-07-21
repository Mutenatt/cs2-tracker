"""
Agregados de Perfil (lifetime, rendimiento por mapa) a partir del historial
de partidas ya resuelto (ver api/queries.py::match_history). PURA: no toca
la DB, solo reduce listas de dicts -- así se testea sin fixtures de SQLite.
"""

from __future__ import annotations

from collections import defaultdict


def lifetime_stats(history: list[dict]) -> dict:
    played = len(history)
    if played == 0:
        return {
            "matches_played": 0,
            "wins": 0,
            "win_rate": 0.0,
            "avg_rating": 0.0,
            "avg_adr": 0.0,
            "avg_kd": 0.0,
            "avg_kast": 0.0,
        }
    wins = sum(1 for h in history if h.get("won"))

    def avg(key: str) -> float:
        return sum(h[key] for h in history) / played

    return {
        "matches_played": played,
        "wins": wins,
        "win_rate": round(100.0 * wins / played, 1),
        "avg_rating": round(avg("rating"), 2),
        "avg_adr": round(avg("adr"), 1),
        "avg_kd": round(avg("kd"), 2),
        "avg_kast": round(avg("kast"), 1),
    }


def map_pool(history: list[dict], known_maps: list[str]) -> list[dict]:
    """Una fila por mapa del pool conocido (`known_maps`), aunque no haya
    datos todavía -- así el frontend puede mostrar "sin datos" en vez de
    simplemente omitir el mapa. Si el jugador tiene partidas reales en un
    mapa FUERA de `known_maps` (p.ej. de_cache, que no tiene radar propio
    en maps.MAP_TRANSFORMS), se agrega igual: un mapa con datos reales
    nunca debe desaparecer solo porque no está en el pool activo."""
    by_map: dict[str, list[dict]] = defaultdict(list)
    for h in history:
        if h.get("map"):
            by_map[h["map"]].append(h)

    all_maps = list(known_maps)
    for mp in by_map:
        if mp not in all_maps:
            all_maps.append(mp)

    out = []
    for mp in all_maps:
        rows = by_map.get(mp, [])
        if rows:
            wins = sum(1 for r in rows if r.get("won"))
            avg_kd = sum(r["kd"] for r in rows) / len(rows)
            out.append(
                {
                    "map": mp,
                    "matches_played": len(rows),
                    "wins": wins,
                    "avg_kd": round(avg_kd, 2),
                    "has_data": True,
                }
            )
        else:
            out.append(
                {"map": mp, "matches_played": 0, "wins": 0, "avg_kd": None, "has_data": False}
            )
    out.sort(key=lambda e: (not e["has_data"], -e["matches_played"]))
    return out


def best_map(pool: list[dict]) -> str | None:
    """Mapa con mejor win rate entre los que tienen datos; desempata por
    cantidad de partidas (más muestra = más confiable). None si no hay datos."""
    with_data = [m for m in pool if m.get("has_data") and m.get("matches_played")]
    if not with_data:
        return None
    return max(
        with_data,
        key=lambda m: (m["wins"] / m["matches_played"], m["matches_played"]),
    )["map"]


def rank_history(history: list[dict]) -> list[dict]:
    """Serie de rank para el sparkline: oldest-first (match_history viene
    newest-first), proyectando solo lo que el gráfico necesita. Serie
    COMPLETA, no el slice de 20 del historial visible."""
    return [
        {
            "match_id": h["match_id"],
            "ingested_at": h.get("ingested_at"),
            "map": h.get("map"),
            "won": h.get("won"),
            "rank": h.get("rank"),
            "rank_type": h.get("rank_type"),
            "comp_wins": h.get("comp_wins"),
        }
        for h in reversed(history)
    ]


def _result_ctx(h: dict) -> str:
    outcome = "victoria" if h.get("won") else "derrota"
    return f"{h.get('map')} · {outcome} {h.get('my_score')}-{h.get('opponent_score')}"


def milestones(
    history: list[dict],
    trade_kills_total: int,
    biggest_clutch: dict | None = None,
) -> list[dict]:
    """Personal bests reales sobre el historial ya resuelto. `biggest_clutch`
    viene de api/queries.py::biggest_clutch_won (necesita el detalle
    por-ronda de player_clutches, que match_history no trae) -- None si el
    jugador nunca ganó un clutch, y en ese caso se omite del todo."""
    if not history:
        return []
    best_rating = max(history, key=lambda h: h["rating"])
    best_adr = max(history, key=lambda h: h["adr"])
    out = [
        {
            "key": "best_rating",
            "label": "Mejor Rating",
            "value": f"{best_rating['rating']:.2f}",
            "context": _result_ctx(best_rating),
        },
        {
            "key": "best_adr",
            "label": "Mejor ADR",
            "value": f"{best_adr['adr']:.1f}",
            "context": _result_ctx(best_adr),
        },
    ]
    if biggest_clutch is not None:
        out.append(
            {
                "key": "biggest_clutch",
                "label": "Clutch más grande ganado",
                "value": f"1v{biggest_clutch['enemies_at_start']}",
                "context": f"ronda {biggest_clutch['round_num']} · {biggest_clutch['map']}",
            }
        )
    out.append(
        {
            "key": "trade_kills",
            "label": "Trade kills totales",
            "value": str(trade_kills_total),
            "context": f"en tus {len(history)} partida{'s' if len(history) != 1 else ''}",
        }
    )
    return out
