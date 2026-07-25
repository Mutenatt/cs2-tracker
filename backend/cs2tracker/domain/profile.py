"""
Agregados de Perfil (lifetime, rendimiento por mapa) a partir del historial
de partidas ya resuelto (ver api/queries.py::match_history). PURA: no toca
la DB, solo reduce listas de dicts -- así se testea sin fixtures de SQLite.
"""

from __future__ import annotations

from collections import defaultdict

# Categorías por arma (para TopWeaponsPanel). Claves = valores crudos de
# demoparser2 en kills.weapon/damages.weapon (ver Weapons.tsx::NICE para las
# mismas claves). Causas de muerte que no son un arma de fuego propiamente
# dicha (cuchillo, granadas, caída, taser, C4) se filtran antes de llegar acá.
WEAPON_CATEGORY: dict[str, str] = {
    "ak47": "rifle",
    "m4a1": "rifle",
    "m4a1_silencer": "rifle",
    "galilar": "rifle",
    "famas": "rifle",
    "sg556": "rifle",
    "aug": "rifle",
    "awp": "sniper",
    "ssg08": "sniper",
    "scar20": "sniper",
    "g3sg1": "sniper",
    "deagle": "pistol",
    "glock": "pistol",
    "hkp2000": "pistol",
    "usp_silencer": "pistol",
    "usp_silencer_off": "pistol",
    "elite": "pistol",
    "fiveseven": "pistol",
    "p250": "pistol",
    "tec9": "pistol",
    "revolver": "pistol",
    "mac10": "smg",
    "mp5sd": "smg",
    "mp7": "smg",
    "mp9": "smg",
    "bizon": "smg",
    "p90": "smg",
    "ump45": "smg",
    "mag7": "shotgun",
    "nova": "shotgun",
    "sawedoff": "shotgun",
    "xm1014": "shotgun",
    "negev": "heavy",
    "m249": "heavy",
}

# Cuchillos: excluidos de WEAPON_CATEGORY/top_weapons (no son "arma
# principal" para el resto de la app), pero la landing de armas nueva
# (domain/profile.py::weapon_breakdown) SÍ los muestra en su tab "Melee".
MELEE_WEAPONS = {"knife", "knife_falchion", "knife_kukri", "knife_t"}

# Causas de muerte/daño que no representan un arma de fuego -- se excluyen
# de top_weapons (un cuchillazo o una caída no es un "arma principal").
_NON_WEAPON_CAUSES = MELEE_WEAPONS | {
    "hegrenade",
    "inferno",
    "world",
    "taser",
    "planted_c4",
}

# Causas de muerte/daño que tampoco son "un arma" en weapon_breakdown, pero
# a diferencia de _NON_WEAPON_CAUSES NO incluye cuchillo (ver MELEE_WEAPONS).
_ENV_CAUSES = _NON_WEAPON_CAUSES - MELEE_WEAPONS

# Conversión de unidades Hammer/Source (las que trae crudo demoparser2 en
# kills.distance) a metros: 1 unit = 0.75 pulgadas = 0.01905 m.
HAMMER_UNIT_TO_METERS = 0.01905

# Bucketing de hitgroups crudos (ver damages.hitgroup) a las 3 zonas de la
# silueta de AccuracyPanel. "neck" y "generic" no tienen polígono propio en
# la silueta -- van a torso por ser la asignación menos arbitraria.
_HITGROUP_ZONE: dict[str, str] = {
    "head": "head",
    "chest": "body",
    "stomach": "body",
    "generic": "body",
    "neck": "body",
    "left_arm": "body",
    "right_arm": "body",
    "left_leg": "legs",
    "right_leg": "legs",
}


def accuracy_stats(hitgroup_counts: dict[str, int], hs_pct_series: list[float]) -> dict:
    """Bucketea conteos de hitgroups crudos a head/body/legs y calcula %.
    `hs_pct_series` es la serie oldest-first de HS% por partida (últimas N)
    para el sparkline -- se pasa tal cual, no se recalcula acá."""
    zones = {"head": 0, "body": 0, "legs": 0}
    for hg, count in hitgroup_counts.items():
        zone = _HITGROUP_ZONE.get(hg)
        if zone:
            zones[zone] += count
    total = sum(zones.values())

    def pct(zone: str) -> float:
        return round(100.0 * zones[zone] / total, 1) if total else 0.0

    return {
        "head_pct": pct("head"),
        "head_hits": zones["head"],
        "body_pct": pct("body"),
        "body_hits": zones["body"],
        "legs_pct": pct("legs"),
        "legs_hits": zones["legs"],
        "hs_pct_series": hs_pct_series,
    }


def top_weapons(kill_weapon_counts: dict[str, int]) -> list[dict]:
    """Top 3 armas por kills lifetime, con categoría. Filtra causas que no
    son un arma de fuego (cuchillo, granadas, caída, taser, C4)."""
    rows = [
        {"name": w, "category": WEAPON_CATEGORY.get(w, "rifle"), "kills": kills}
        for w, kills in kill_weapon_counts.items()
        if w not in _NON_WEAPON_CAUSES and kills > 0
    ]
    rows.sort(key=lambda r: -r["kills"])
    return rows[:3]


def _category_for(weapon: str) -> str:
    if weapon in MELEE_WEAPONS:
        return "melee"
    return WEAPON_CATEGORY.get(weapon, "rifle")


def weapon_breakdown(
    kills_by: list[dict],
    deaths_by: list[dict],
    damage_by: dict[str, int],
    rounds_played: int,
) -> list[dict]:
    """Detalle COMPLETO por arma (a diferencia de top_weapons, que corta en
    3 y excluye cuchillo): kills, deaths, HS%, ADR, kills por ronda y
    distancia de kill más larga (en metros). `kills_by`: kills que hizo el
    jugador, [{"weapon","headshot","distance"}]. `deaths_by`: kills que le
    hicieron A ÉL, [{"weapon"}] (solo importa con qué lo mataron).
    `damage_by`: daño total infligido por arma, {weapon: dmg_health}.
    Devuelve todas las armas que aparezcan en kills/deaths/daño, INCLUYE
    cuchillo (categoría "melee") -- a diferencia de top_weapons/badges, acá
    sí se muestra (ver landing de armas, tab Melee)."""
    weapons = {k["weapon"] for k in kills_by if k.get("weapon")}
    weapons |= {d["weapon"] for d in deaths_by if d.get("weapon")}
    weapons |= {w for w in damage_by if w}
    weapons -= _ENV_CAUSES

    rows = []
    for w in weapons:
        wk = [k for k in kills_by if k.get("weapon") == w]
        kills = len(wk)
        hs = sum(1 for k in wk if k.get("headshot"))
        deaths = sum(1 for d in deaths_by if d.get("weapon") == w)
        dmg = damage_by.get(w, 0)
        distances = [k["distance"] for k in wk if k.get("distance")]
        rows.append(
            {
                "name": w,
                "category": _category_for(w),
                "kills": kills,
                "deaths": deaths,
                "hs_pct": round(100.0 * hs / kills, 1) if kills else 0.0,
                "adr": round(dmg / rounds_played, 1) if rounds_played else 0.0,
                "kills_per_round": round(kills / rounds_played, 2) if rounds_played else 0.0,
                "longest_kill_m": (
                    round(max(distances) * HAMMER_UNIT_TO_METERS, 1) if distances else 0.0
                ),
            }
        )
    rows.sort(key=lambda r: -r["kills"])
    return rows


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
            # Distinto de matches_played - wins: partidas con won=None (ronda
            # sin resolver) no cuentan como derrota -- TopMapsPanel necesita
            # wins/losses reales para no ensuciar el win% con irresueltas.
            losses = sum(1 for r in rows if r.get("won") is False)
            avg_kd = sum(r["kd"] for r in rows) / len(rows)
            out.append(
                {
                    "map": mp,
                    "matches_played": len(rows),
                    "wins": wins,
                    "losses": losses,
                    "avg_kd": round(avg_kd, 2),
                    "has_data": True,
                }
            )
        else:
            out.append(
                {
                    "map": mp,
                    "matches_played": 0,
                    "wins": 0,
                    "losses": 0,
                    "avg_kd": None,
                    "has_data": False,
                }
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


def _is_valid_premier(p: dict) -> bool:
    """Punto con un CS Rating Premier real: >0 (no calibrando) y de tipo
    Premier (11) o desconocido (demos viejos sin rank_type explícito).
    Mismo criterio que usa el frontend para filtrar el sparkline."""
    r = p.get("rank")
    return r is not None and r > 0 and p.get("rank_type") in (None, 11)


def rank_history(history: list[dict]) -> list[dict]:
    """Serie de rank para el sparkline: oldest-first (match_history viene
    newest-first), proyectando solo lo que el gráfico necesita. Serie
    COMPLETA, no el slice de 20 del historial visible.

    Cada punto además trae `rating_after`/`rating_delta`: el CS Rating con
    el que TERMINÓ esa partida y cuánto ganó/perdió. GOTV solo graba el
    rating de ENTRADA a cada partida, así que el rating resultante de la
    partida N = el rating de entrada de la partida Premier N+1. El último
    punto queda con `rating_after=None` (todavía no hay partida siguiente
    ingerida: ese gap lo cubre el rating vivo del GC, ver Capa 2)."""
    serie = [
        {
            "match_id": h["match_id"],
            "ingested_at": h.get("ingested_at"),
            "map": h.get("map"),
            "won": h.get("won"),
            "rank": h.get("rank"),
            "rank_type": h.get("rank_type"),
            "comp_wins": h.get("comp_wins"),
            "rating_after": None,
            "rating_delta": None,
        }
        for h in reversed(history)
    ]
    # Recorremos de la más nueva a la más vieja arrastrando el rank de
    # entrada de la siguiente partida Premier válida (= rating de salida de
    # la actual). Se asigna ANTES de actualizar el acumulador con el rank
    # propio, para que cada punto se empareje con el POSTERIOR, no consigo.
    next_valid_rank: int | None = None
    for p in reversed(serie):
        if _is_valid_premier(p):
            if next_valid_rank is not None:
                p["rating_after"] = next_valid_rank
                p["rating_delta"] = next_valid_rank - p["rank"]
            next_valid_rank = p["rank"]
    return serie


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
