"""
Queries cross-match para heatmaps: leen player_map_zones (agregado, el
read-path barato) y player_map_events solo para el resumen de friendly-fire
(un escalar simple, no vale la pena precomputarlo -- ver Fase 3/4 del plan).
"""

from __future__ import annotations

from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from cs2tracker.db import (
    Blind,
    Kill,
    Match,
    MatchPlayer,
    Player,
    PlayerClutch,
    PlayerMapEvent,
    PlayerMapZone,
    PlayerMatchStats,
    Round,
)
from cs2tracker.domain import find_flash_assists

MIN_SAMPLE = 5  # celdas con menos eventos que esto no se muestran (ruido)


def zones_by_event_type(
    s: Session,
    steamid: str,
    map_name: str,
    event_type: str,
) -> list[PlayerMapZone]:
    """Sin filtro de muestra mÃ­nima: cada endpoint lo aplica sobre la mÃ©trica
    que le corresponda (no siempre es `count`, ver entries/trades)."""
    return list(
        s.execute(
            select(PlayerMapZone).where(
                PlayerMapZone.steamid == steamid,
                PlayerMapZone.map == map_name,
                PlayerMapZone.event_type == event_type,
            )
        )
        .scalars()
        .all()
    )


def shares_a_match(s: Session, viewer: str, target: str) -> bool:
    """Un usuario puede ver su propio heatmap, o el de alguien con quien
    comparte al menos una partida (misma regla de visibilidad que las
    partidas: pertenencia, no ownership)."""
    if viewer == target:
        return True
    viewer_matches = select(MatchPlayer.match_id).where(MatchPlayer.steamid == viewer)
    count = s.scalar(
        select(func.count())
        .select_from(MatchPlayer)
        .where(MatchPlayer.steamid == target, MatchPlayer.match_id.in_(viewer_matches))
    )
    return bool(count)


def is_participant(s: Session, steamid: str, match_id: str) -> bool:
    """True si `steamid` jugó esta partida (aparece en match_players).
    Misma regla de pertenencia que `shares_a_match`, pero para endpoints
    de partida (scoreboard/kills/duels/weapons) que no tienen un `target`
    puntual sino que exponen a TODO el roster."""
    return bool(
        s.scalar(
            select(func.count())
            .select_from(MatchPlayer)
            .where(MatchPlayer.match_id == match_id, MatchPlayer.steamid == steamid)
        )
    )


def friendly_fire_summary(s: Session, steamid: str) -> tuple[int, int]:
    """(total_flashes, friendly_flashes) del jugador, todas sus partidas."""
    base = (
        select(func.count())
        .select_from(PlayerMapEvent)
        .where(PlayerMapEvent.steamid == steamid, PlayerMapEvent.event_type == "flash_thrown")
    )
    total = s.scalar(base) or 0
    friendly = s.scalar(base.where(PlayerMapEvent.teammates_blinded > 0)) or 0
    return total, friendly


def _match_scores(s: Session, match_id: str) -> dict[int, int]:
    rows = s.execute(
        select(Round.winner_num, func.count())
        .where(Round.match_id == match_id, Round.winner_num.is_not(None))
        .group_by(Round.winner_num)
    ).all()
    return dict(rows)


def match_history(s: Session, steamid: str, limit: int = 1000) -> list[dict]:
    """Una entrada por partida jugada por `steamid`, mÃ¡s reciente primero:
    mapa, lado inicial, marcador, resultado y sus stats de esa partida.
    Todo desde tablas ya persistidas (match_players + rounds +
    player_match_stats) -- ninguna requiere reparsear el demo. Fuente Ãºnica
    para /players/{steamid}/profile (lifetime y map pool se derivan de esto
    en domain/profile.py, no se vuelve a consultar la DB para cada uno)."""
    q = (
        select(
            Match,
            MatchPlayer.team_num,
            MatchPlayer.rank,
            MatchPlayer.rank_type,
            MatchPlayer.comp_wins,
            PlayerMatchStats,
        )
        .join(MatchPlayer, MatchPlayer.match_id == Match.match_id)
        .outerjoin(
            PlayerMatchStats,
            (PlayerMatchStats.match_id == Match.match_id) & (PlayerMatchStats.steamid == steamid),
        )
        .where(MatchPlayer.steamid == steamid)
        .order_by(Match.match_id.desc())
        .limit(limit)
    )
    out: list[dict] = []
    for m, team_num, rank, rank_type, comp_wins, stats in s.execute(q).all():
        scores = _match_scores(s, m.match_id)
        my_score = scores.get(team_num) if team_num is not None else None
        opponent_score = next((v for k, v in scores.items() if k != team_num), None)
        won = None
        if my_score is not None and opponent_score is not None:
            won = my_score > opponent_score
        out.append(
            {
                "match_id": m.match_id,
                "map": m.map,
                "n_rounds": m.n_rounds,
                "ingested_at": m.ingested_at,
                "played_at": m.played_at,
                "team_num": team_num,
                "rank": rank,
                "rank_type": rank_type,
                "comp_wins": comp_wins,
                "my_score": my_score,
                "opponent_score": opponent_score,
                "won": won,
                "kills": stats.kills if stats else 0,
                "deaths": stats.deaths if stats else 0,
                "assists": stats.assists if stats else 0,
                "adr": stats.adr if stats else 0.0,
                "kd": stats.kd if stats else 0.0,
                "kast": stats.kast if stats else 0.0,
                "rating": stats.rating if stats else 0.0,
            }
        )
    return out


def lifetime_trade_kills(s: Session, steamid: str) -> int:
    """Trade kills totales del jugador en todas sus partidas (kills marcados
    is_trade_kill=True al ingerir, ver domain/kast.py::find_trade_kills)."""
    return (
        s.scalar(
            select(func.count())
            .select_from(PlayerMapEvent)
            .where(
                PlayerMapEvent.steamid == steamid,
                PlayerMapEvent.event_type == "kill",
                PlayerMapEvent.is_trade_kill.is_(True),
            )
        )
        or 0
    )


def role_inputs(s: Session, steamid: str) -> dict:
    """Agregados para inferir el rol dominante (domain/roles.py). Kills
    excluyen suicidios; el filtro de AWP es igualdad estricta ('ssg08' es
    otra arma y no cuenta); flashes efectivas = cegaron a >= 1 enemigo."""
    matches_played = (
        s.scalar(
            select(func.count()).select_from(MatchPlayer).where(MatchPlayer.steamid == steamid)
        )
        or 0
    )
    kills_base = (
        select(func.count())
        .select_from(Kill)
        .where(Kill.attacker == steamid, Kill.attacker != Kill.victim)
    )
    total_kills = s.scalar(kills_base) or 0
    awp_kills = s.scalar(kills_base.where(Kill.weapon == "awp")) or 0
    entry = s.execute(
        select(
            func.coalesce(func.sum(PlayerMatchStats.entry_kills), 0),
            func.coalesce(func.sum(PlayerMatchStats.entry_deaths), 0),
        ).where(PlayerMatchStats.steamid == steamid)
    ).one()
    effective_flashes = (
        s.scalar(
            select(func.count())
            .select_from(PlayerMapEvent)
            .where(
                PlayerMapEvent.steamid == steamid,
                PlayerMapEvent.event_type == "flash_thrown",
                PlayerMapEvent.enemies_blinded >= 1,
            )
        )
        or 0
    )
    return {
        "matches_played": matches_played,
        "total_kills": total_kills,
        "awp_kills": awp_kills,
        "entry_kills": int(entry[0]),
        "entry_deaths": int(entry[1]),
        "effective_flashes": effective_flashes,
    }


def clutch_timeline(s: Session, match_id: str, steamid: str) -> list[PlayerClutch]:
    return list(
        s.execute(
            select(PlayerClutch)
            .where(PlayerClutch.match_id == match_id, PlayerClutch.steamid == steamid)
            .order_by(PlayerClutch.round_num)
        )
        .scalars()
        .all()
    )


def biggest_clutch_won(s: Session, steamid: str) -> dict | None:
    """El clutch ganado mÃ¡s grande (mayor enemies_at_start) de todas las
    partidas del jugador, o None si nunca ganÃ³ uno."""
    row = s.execute(
        select(PlayerClutch, Match.map)
        .join(Match, Match.match_id == PlayerClutch.match_id)
        .where(PlayerClutch.steamid == steamid, PlayerClutch.outcome == "won")
        .order_by(PlayerClutch.enemies_at_start.desc())
        .limit(1)
    ).first()
    if row is None:
        return None
    pc, map_name = row
    return {
        "match_id": pc.match_id,
        "map": map_name,
        "round_num": pc.round_num,
        "enemies_at_start": pc.enemies_at_start,
    }


def _player_match_ids(s: Session, steamid: str) -> set[str]:
    return {
        mid
        for (mid,) in s.execute(
            select(MatchPlayer.match_id).where(MatchPlayer.steamid == steamid)
        ).all()
    }


def _shared_matches(s: Session, a: str, b: str) -> set[str]:
    """match_ids donde a Y b aparecen, sin importar el equipo."""
    return _player_match_ids(s, a) & _player_match_ids(s, b)


def rivals(s: Session, steamid: str, limit: int = 10) -> list[dict]:
    """Jugadores con los que `steamid` compartiÃ³ partida, compaÃ±eros u
    oponentes, ordenados por partidas compartidas. Insumo del selector de
    rival en Squad & Rivals."""
    my_teams = dict(
        s.execute(
            select(MatchPlayer.match_id, MatchPlayer.team_num).where(MatchPlayer.steamid == steamid)
        ).all()
    )
    if not my_teams:
        return []
    rows = s.execute(
        select(MatchPlayer.steamid, MatchPlayer.match_id, MatchPlayer.team_num, Player.name)
        .join(Player, Player.steamid == MatchPlayer.steamid)
        .where(MatchPlayer.match_id.in_(my_teams.keys()), MatchPlayer.steamid != steamid)
    ).all()

    agg: dict[str, dict] = {}
    rival_matches: dict[str, list[str]] = defaultdict(list)
    for sid, match_id, team_num, name in rows:
        a = agg.setdefault(
            sid, {"steamid": sid, "name": name, "matches_together": 0, "matches_opposed": 0}
        )
        if team_num == my_teams.get(match_id):
            a["matches_together"] += 1
        else:
            a["matches_opposed"] += 1
        rival_matches[sid].append(match_id)

    for sid, a in agg.items():
        avg_rating = s.scalar(
            select(func.avg(PlayerMatchStats.rating)).where(
                PlayerMatchStats.steamid == sid,
                PlayerMatchStats.match_id.in_(rival_matches[sid]),
            )
        )
        a["avg_rating"] = round(avg_rating, 2) if avg_rating is not None else 0.0

    out = list(agg.values())
    out.sort(key=lambda a: -(a["matches_together"] + a["matches_opposed"]))
    return out[:limit]


def compare_players(s: Session, steamid_a: str, steamid_b: str) -> dict | None:
    """ComparaciÃ³n cabeza a cabeza sobre TODAS las partidas que a y b
    compartieron (compaÃ±eros u oponentes). None si nunca compartieron
    ninguna."""
    shared = _shared_matches(s, steamid_a, steamid_b)
    if not shared:
        return None

    def avgs(steamid: str) -> list[float]:
        row = s.execute(
            select(
                func.avg(PlayerMatchStats.rating),
                func.avg(PlayerMatchStats.adr),
                func.avg(PlayerMatchStats.kast),
                func.avg(PlayerMatchStats.hs_pct),
            ).where(PlayerMatchStats.steamid == steamid, PlayerMatchStats.match_id.in_(shared))
        ).one()
        return [round(v, 2) if v is not None else 0.0 for v in row]

    a_vals, b_vals = avgs(steamid_a), avgs(steamid_b)
    metrics = [
        {"key": k, "label": label, "value_a": av, "value_b": bv}
        for k, label, av, bv in zip(
            ["rating", "adr", "kast", "hs_pct"],
            ["RATING", "ADR", "KAST", "HS%"],
            a_vals,
            b_vals,
            strict=True,
        )
    ]

    most_recent = s.execute(
        select(Match.match_id)
        .where(Match.match_id.in_(shared))
        .order_by(Match.match_id.desc())
        .limit(1)
    ).scalar()
    team_a = s.scalar(
        select(MatchPlayer.team_num).where(
            MatchPlayer.match_id == most_recent, MatchPlayer.steamid == steamid_a
        )
    )
    team_b = s.scalar(
        select(MatchPlayer.team_num).where(
            MatchPlayer.match_id == most_recent, MatchPlayer.steamid == steamid_b
        )
    )
    name_a = s.scalar(select(Player.name).where(Player.steamid == steamid_a))
    name_b = s.scalar(select(Player.name).where(Player.steamid == steamid_b))

    return {
        "steamid_a": steamid_a,
        "name_a": name_a,
        "team_num_a": team_a,
        "steamid_b": steamid_b,
        "name_b": name_b,
        "team_num_b": team_b,
        "matches_compared": len(shared),
        "metrics": metrics,
    }


def flash_assist_count(s: Session, thrower_steamid: str) -> int:
    """Kills de un compaÃ±ero mientras el rival estaba cegado por una flash de
    `thrower_steamid`, sumado en todas sus partidas (ver
    domain/utility.py::find_flash_assists -- heurÃ­stica por ventana, no por
    entity_id). Se calcula en vivo, no persistido: hoy solo lo lee Squad &
    Rivals, bajo volumen de lectura; si eso cambia, promoverlo a una columna
    igual que se hizo con is_trade_kill."""
    match_ids = [
        mid
        for (mid,) in s.execute(
            select(MatchPlayer.match_id).where(MatchPlayer.steamid == thrower_steamid)
        ).all()
    ]
    total = 0
    for match_id in match_ids:
        kills = [
            {"round_num": k.round_num, "tick": k.tick, "attacker": k.attacker, "victim": k.victim}
            for k in s.execute(select(Kill).where(Kill.match_id == match_id)).scalars()
        ]
        blinds = [
            {
                "round_num": b.round_num,
                "tick": b.tick,
                "attacker": b.attacker,
                "victim": b.victim,
                "duration": b.duration,
            }
            for b in s.execute(select(Blind).where(Blind.match_id == match_id)).scalars()
        ]
        teams = {
            mp.steamid: mp.team_num
            for mp in s.execute(
                select(MatchPlayer).where(MatchPlayer.match_id == match_id)
            ).scalars()
        }
        assists = find_flash_assists(kills, blinds, teams)
        total += sum(1 for a in assists if a["flash_thrower"] == thrower_steamid)
    return total


def recent_deaths_with_timing(s: Session, steamid: str, last_n_matches: int = 5) -> list[dict]:
    """Muertes con `seconds_into_round` conocido en las Ãºltimas `last_n_matches`
    partidas del jugador -- insumo de domain/coach.py::early_round_death_pattern.
    Partidas sin round_freeze_end en el demo simplemente no aportan filas acÃ¡
    (no se fabrica un valor)."""
    recent_match_ids = (
        select(Match.match_id)
        .join(MatchPlayer, MatchPlayer.match_id == Match.match_id)
        .where(MatchPlayer.steamid == steamid)
        .order_by(Match.match_id.desc())
        .limit(last_n_matches)
    )
    rows = s.execute(
        select(PlayerMapEvent.match_id, PlayerMapEvent.seconds_into_round, Match.map)
        .join(Match, Match.match_id == PlayerMapEvent.match_id)
        .where(
            PlayerMapEvent.steamid == steamid,
            PlayerMapEvent.event_type == "death",
            PlayerMapEvent.seconds_into_round.is_not(None),
            PlayerMapEvent.match_id.in_(recent_match_ids),
        )
    ).all()
    return [{"match_id": mid, "seconds_into_round": s_, "map": mp} for mid, s_, mp in rows]


def badge_inputs(s: Session, match_id: str, steamid: str) -> dict:
    """Insumos para domain.badges.compute_badges. Todo ya estÃ¡ denormalizado
    en player_map_events (is_entry, round_won, enemies_blinded,
    blind_duration_total, damage_dealt, teammates_blinded) y
    player_match_stats.clutches -- ninguna query nueva sobre eventos crudos."""
    base = (
        select(func.count())
        .select_from(PlayerMapEvent)
        .where(PlayerMapEvent.match_id == match_id, PlayerMapEvent.steamid == steamid)
    )
    entry_kills = (
        s.scalar(base.where(PlayerMapEvent.event_type == "kill", PlayerMapEvent.is_entry.is_(True)))
        or 0
    )
    entry_wins = (
        s.scalar(
            base.where(
                PlayerMapEvent.event_type == "kill",
                PlayerMapEvent.is_entry.is_(True),
                PlayerMapEvent.round_won.is_(True),
            )
        )
        or 0
    )
    entry_kill_win_rate = round(100.0 * entry_wins / entry_kills, 1) if entry_kills else 0.0

    stats = s.get(PlayerMatchStats, (match_id, steamid))
    clutches_won = stats.clutches if stats else 0

    avg_blind = s.scalar(
        select(func.avg(PlayerMapEvent.blind_duration_total)).where(
            PlayerMapEvent.match_id == match_id,
            PlayerMapEvent.steamid == steamid,
            PlayerMapEvent.event_type == "flash_thrown",
            PlayerMapEvent.enemies_blinded > 0,
        )
    )

    grenade_damage = (
        s.scalar(
            select(func.coalesce(func.sum(PlayerMapEvent.damage_dealt), 0)).where(
                PlayerMapEvent.match_id == match_id,
                PlayerMapEvent.steamid == steamid,
                PlayerMapEvent.event_type.in_(["he_thrown", "molotov_thrown"]),
            )
        )
        or 0
    )

    team_flashes_total = s.scalar(base.where(PlayerMapEvent.event_type == "flash_thrown")) or 0
    team_flashes = (
        s.scalar(
            base.where(
                PlayerMapEvent.event_type == "flash_thrown", PlayerMapEvent.teammates_blinded > 0
            )
        )
        or 0
    )

    return {
        "entry_kills": entry_kills,
        "entry_kill_win_rate": entry_kill_win_rate,
        "clutches_won": clutches_won,
        "avg_flash_blind_duration": avg_blind,
        "grenade_damage": grenade_damage,
        "team_flashes": team_flashes,
        "team_flashes_total": team_flashes_total,
    }


def monthly_window_rows(s: Session, steamid: str, start_utc: str, end_utc: str) -> list[dict]:
    """Filas de la ventana mensual para steamid: mapa, W/L (mismo patrón que
    match_history/_match_scores) y las métricas por partida que arma
    domain/monthly.py. event_ts = played_at, o ingested_at si played_at es
    NULL (demo manual sin backfill) -- así una partida real nunca desaparece
    del resumen solo por faltar el backfill."""
    event_ts = func.coalesce(Match.played_at, Match.ingested_at)
    q = (
        select(Match, MatchPlayer.team_num, PlayerMatchStats)
        .join(MatchPlayer, MatchPlayer.match_id == Match.match_id)
        .join(
            PlayerMatchStats,
            (PlayerMatchStats.match_id == Match.match_id)
            & (PlayerMatchStats.steamid == MatchPlayer.steamid),
        )
        .where(MatchPlayer.steamid == steamid, event_ts >= start_utc, event_ts < end_utc)
    )
    out: list[dict] = []
    for m, team_num, stats in s.execute(q).all():
        scores = _match_scores(s, m.match_id)
        my_score = scores.get(team_num) if team_num is not None else None
        opponent_score = next((v for k, v in scores.items() if k != team_num), None)
        won = (
            my_score > opponent_score
            if my_score is not None and opponent_score is not None
            else None
        )
        out.append(
            {
                "match_id": m.match_id,
                "map": m.map,
                "played_at": m.played_at or m.ingested_at,
                "won": won,
                "kills": stats.kills,
                "deaths": stats.deaths,
                "adr": stats.adr,
                "kast": stats.kast,
                "hs_pct": stats.hs_pct,
                "rating": stats.rating,
                "entry_kills": stats.entry_kills,
            }
        )
    return out


def monthly_clutches_won(s: Session, steamid: str, start_utc: str, end_utc: str) -> list[dict]:
    """Clutches GANADOS de steamid en la ventana, con las kills del jugador
    en esa ronda (tabla kills) ya resueltas -- insumo del desempate del MVP
    en domain/monthly.py::_select_mvp."""
    event_ts = func.coalesce(Match.played_at, Match.ingested_at)
    q = (
        select(PlayerClutch, Match.map, Match.played_at, Match.ingested_at)
        .join(Match, Match.match_id == PlayerClutch.match_id)
        .where(
            PlayerClutch.steamid == steamid,
            PlayerClutch.outcome == "won",
            event_ts >= start_utc,
            event_ts < end_utc,
        )
    )
    out: list[dict] = []
    for pc, map_name, played_at, ingested_at in s.execute(q).all():
        kills_in_round = (
            s.scalar(
                select(func.count())
                .select_from(Kill)
                .where(
                    Kill.match_id == pc.match_id,
                    Kill.round_num == pc.round_num,
                    Kill.attacker == steamid,
                )
            )
            or 0
        )
        out.append(
            {
                "map": map_name,
                "round_num": pc.round_num,
                "enemies_at_start": pc.enemies_at_start,
                "kills_in_round": kills_in_round,
                "played_at": played_at or ingested_at,
            }
        )
    return out
