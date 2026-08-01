"""
Queries cross-match compartidas por los distintos endpoints de perfil/partida
(historial, rivals, compare, badges, monthly, etc.).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from cs2tracker.db import (
    Blind,
    Damage,
    GlobalMetricStats,
    Kill,
    Match,
    MatchPlayer,
    Player,
    PlayerClutch,
    PlayerMapEvent,
    PlayerMatchStats,
    PlayerProfileTag,
    Round,
    RoundEconomy,
)
from cs2tracker.domain import economia as economia_domain
from cs2tracker.domain import find_flash_assists
from cs2tracker.domain import highlights as highlights_domain
from cs2tracker.domain import kast as kast_domain
from cs2tracker.domain import loadouts as loadouts_domain
from cs2tracker.domain import lurker as lurker_domain
from cs2tracker.domain import percentiles as percentiles_domain
from cs2tracker.domain import social as social_domain
from cs2tracker.domain.badges import catalog as badges_catalog

MIN_SAMPLE = 5  # celdas con menos eventos que esto no se muestran (ruido)


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
                "hs_pct": stats.hs_pct if stats else 0.0,
            }
        )
    return out


def lifetime_weapon_kills(s: Session, steamid: str) -> dict[str, int]:
    """Kills lifetime por arma (todas las partidas), para TopWeaponsPanel.
    Excluye suicidio, igual que role_inputs."""
    rows = s.execute(
        select(Kill.weapon, func.count())
        .where(Kill.attacker == steamid, Kill.attacker != Kill.victim)
        .group_by(Kill.weapon)
    ).all()
    return {weapon: count for weapon, count in rows if weapon}


def lifetime_rounds_played(s: Session, steamid: str) -> int:
    """Suma de Match.n_rounds de todas las partidas del jugador -- el
    denominador de ADR/kills-por-ronda en domain/profile.py::
    weapon_breakdown y del ADR lifetime que alimenta DDΔ en loadouts."""
    return (
        s.scalar(
            select(func.coalesce(func.sum(Match.n_rounds), 0))
            .select_from(MatchPlayer)
            .join(Match, Match.match_id == MatchPlayer.match_id)
            .where(MatchPlayer.steamid == steamid)
        )
        or 0
    )


def weapon_breakdown_inputs(s: Session, steamid: str) -> dict:
    """Kills/deaths/daño lifetime por arma, para domain/profile.py::
    weapon_breakdown. Se lee de player_map_events en vez de kills/damages
    crudas: esa tabla ya denormaliza weapon/headshot/distance tanto en la
    fila 'kill' del atacante como en la fila 'death' de la víctima (mismo
    evento de kill, ver ingest.py) -- da kills Y deaths por arma sin
    cruzar attacker/victim a mano como sí hace lifetime_weapon_kills."""
    kills_by = [
        {"weapon": w, "headshot": bool(hs), "distance": d}
        for w, hs, d in s.execute(
            select(PlayerMapEvent.weapon, PlayerMapEvent.headshot, PlayerMapEvent.distance).where(
                PlayerMapEvent.steamid == steamid, PlayerMapEvent.event_type == "kill"
            )
        ).all()
    ]
    deaths_by = [
        {"weapon": w}
        for (w,) in s.execute(
            select(PlayerMapEvent.weapon).where(
                PlayerMapEvent.steamid == steamid, PlayerMapEvent.event_type == "death"
            )
        ).all()
    ]
    damage_by = {
        w: int(dmg)
        for w, dmg in s.execute(
            select(Damage.weapon, func.coalesce(func.sum(Damage.dmg_health), 0))
            .where(Damage.attacker == steamid)
            .group_by(Damage.weapon)
        ).all()
        if w
    }
    return {"kills_by": kills_by, "deaths_by": deaths_by, "damage_by": damage_by}


def loadout_breakdown_inputs(s: Session, steamid: str) -> list[dict]:
    """Una fila por (partida, ronda) donde `steamid` tiene economía
    registrada (round_economy), con kills/deaths/assists/daño de esa
    ronda, KAST (bool) y si fue su entry attempt/win -- insumo de
    domain/loadouts.py::aggregate_loadout_stats. KAST se reconstruye por
    partida (mismo patrón de loop que flash_assist_count: recorre las
    partidas del jugador trayendo los kills crudos + teams de CADA una,
    porque KAST necesita ver a todo el roster, no solo lo propio).
    Rondas sin round_economy (demo ingerido antes de esa tabla) quedan
    afuera -- no se inventa una fila."""
    econ_rows = (
        s.execute(select(RoundEconomy).where(RoundEconomy.steamid == steamid)).scalars().all()
    )
    if not econ_rows:
        return []
    match_ids = {r.match_id for r in econ_rows}

    kills_count: dict[tuple[str, int], int] = defaultdict(int)
    deaths_count: dict[tuple[str, int], int] = defaultdict(int)
    assists_count: dict[tuple[str, int], int] = defaultdict(int)
    for mid, rnd, attacker, victim, assister in s.execute(
        select(Kill.match_id, Kill.round_num, Kill.attacker, Kill.victim, Kill.assister).where(
            Kill.match_id.in_(match_ids)
        )
    ).all():
        if rnd is None:
            continue
        if attacker == steamid and attacker != victim:
            kills_count[(mid, rnd)] += 1
        if victim == steamid:
            deaths_count[(mid, rnd)] += 1
        if assister == steamid:
            assists_count[(mid, rnd)] += 1

    damage_count: dict[tuple[str, int], int] = defaultdict(int)
    for mid, rnd, dmg in s.execute(
        select(Damage.match_id, Damage.round_num, Damage.dmg_health).where(
            Damage.attacker == steamid, Damage.match_id.in_(match_ids)
        )
    ).all():
        if rnd is not None:
            damage_count[(mid, rnd)] += dmg or 0

    entry_attempt: set[tuple[str, int]] = set()
    entry_win: set[tuple[str, int]] = set()
    for mid, rnd, event_type in s.execute(
        select(PlayerMapEvent.match_id, PlayerMapEvent.round_num, PlayerMapEvent.event_type).where(
            PlayerMapEvent.steamid == steamid,
            PlayerMapEvent.event_type.in_(("kill", "death")),
            PlayerMapEvent.is_entry.is_(True),
            PlayerMapEvent.match_id.in_(match_ids),
        )
    ).all():
        if rnd is None:
            continue
        entry_attempt.add((mid, rnd))
        if event_type == "kill":
            entry_win.add((mid, rnd))

    kast_rounds: set[tuple[str, int]] = set()
    for match_id in match_ids:
        teams = {
            mp.steamid: mp.team_num
            for mp in s.execute(
                select(MatchPlayer).where(MatchPlayer.match_id == match_id)
            ).scalars()
        }
        kills = [
            {
                "round_num": k.round_num,
                "tick": k.tick,
                "attacker": k.attacker,
                "victim": k.victim,
                "assister": k.assister,
            }
            for k in s.execute(select(Kill).where(Kill.match_id == match_id)).scalars()
        ]
        for rnd in kast_domain.kast_rounds_for_player(kills, teams, steamid):
            kast_rounds.add((match_id, rnd))

    rows = []
    for r in econ_rows:
        key = (r.match_id, r.round_num)
        rows.append(
            {
                "tier": loadouts_domain.loadout_tier(r.round_num, r.equip_value),
                "kills": kills_count.get(key, 0),
                "deaths": deaths_count.get(key, 0),
                "assists": assists_count.get(key, 0),
                "damage": damage_count.get(key, 0),
                "kast": key in kast_rounds,
                "entry_attempt": key in entry_attempt,
                "entry_win": key in entry_win,
            }
        )
    return rows


def lifetime_hitgroup_counts(s: Session, steamid: str) -> dict[str, int]:
    """Cantidad de impactos por hitgroup crudo en todas las partidas del
    jugador, para AccuracyPanel."""
    rows = s.execute(
        select(Damage.hitgroup, func.count())
        .where(Damage.attacker == steamid)
        .group_by(Damage.hitgroup)
    ).all()
    return {hitgroup: count for hitgroup, count in rows if hitgroup}


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


def winrate_conjunto(s: Session, steamid_a: str, steamid_b: str) -> dict | None:
    """Partidas donde `steamid_a` y `steamid_b` jugaron en el MISMO equipo
    (mismo patrón `my_teams` que rivals(), líneas 302-344 -- no el SQL
    crudo con alias inválido del doc original). None si nunca compartieron
    equipo (pueden haber sido siempre rivales, o nunca haber compartido
    partida). Partidas con resultado irresoluto no cuentan ni como
    victoria ni como derrota."""
    my_teams = dict(
        s.execute(
            select(MatchPlayer.match_id, MatchPlayer.team_num).where(
                MatchPlayer.steamid == steamid_a
            )
        ).all()
    )
    if not my_teams:
        return None
    their_teams = dict(
        s.execute(
            select(MatchPlayer.match_id, MatchPlayer.team_num).where(
                MatchPlayer.steamid == steamid_b, MatchPlayer.match_id.in_(my_teams.keys())
            )
        ).all()
    )
    same_team_matches = [
        match_id for match_id, team in my_teams.items() if their_teams.get(match_id) == team
    ]
    if not same_team_matches:
        return None

    partidas = []
    for match_id in same_team_matches:
        scores = _match_scores(s, match_id)
        my_score = scores.get(my_teams[match_id])
        opp_score = next((v for k, v in scores.items() if k != my_teams[match_id]), None)
        if my_score is None or opp_score is None:
            continue  # ronda/partida sin resolver -- no cuenta
        partidas.append({"won": my_score > opp_score})
    return social_domain.calcular_winrate_conjunto(partidas)


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

    lurker_rounds = lurker_inputs(s, steamid, [match_id])
    lurker_rate = lurker_domain.tasa_lurker(lurker_rounds) if lurker_rounds else None
    economia = economia_inputs(s, match_id, steamid)

    return {
        "entry_kills": entry_kills,
        "entry_kill_win_rate": entry_kill_win_rate,
        "clutches_won": clutches_won,
        "avg_flash_blind_duration": avg_blind,
        "grenade_damage": grenade_damage,
        "team_flashes": team_flashes,
        "team_flashes_total": team_flashes_total,
        "lurker_rate": lurker_rate,
        "force_buy_wins": economia["force_buy_wins"],
        "eco_frags": economia["eco_frags"],
        "millonario_weapon": economia["millonario_weapon"],
        "economia_rate": economia["economia_rate"],
    }


def lurker_inputs(s: Session, steamid: str, match_ids: list[str]) -> list[dict]:
    """Por cada (partida, ronda) de `match_ids` donde el roster de
    `steamid` atacaba (Round.attacker_roster == su team_num en ESA
    partida), su evento kill/death más temprano + los de sus compañeros de
    roster en esa misma ronda. Insumo de domain.lurker.tasa_lurker. Sirve
    tanto para el badge de una partida (match_ids=[match_id]) como para el
    tag de perfil sobre una ventana de partidas -- agrupa por
    (match_id, round_num), no solo round_num, porque ese número se repite
    entre partidas distintas. Sin datos: la ronda queda sin fila (no se
    puede evaluar aislamiento/timing sin al menos un evento propio)."""
    if not match_ids:
        return []
    my_teams = dict(
        s.execute(
            select(MatchPlayer.match_id, MatchPlayer.team_num).where(
                MatchPlayer.steamid == steamid, MatchPlayer.match_id.in_(match_ids)
            )
        ).all()
    )
    if not my_teams:
        return []

    attacker_rounds = {
        (mid, round_num)
        for mid, round_num, attacker in s.execute(
            select(Round.match_id, Round.round_num, Round.attacker_roster).where(
                Round.match_id.in_(my_teams.keys())
            )
        ).all()
        if attacker == my_teams.get(mid)
    }
    if not attacker_rounds:
        return []

    rows = s.execute(
        select(
            PlayerMapEvent.steamid,
            PlayerMapEvent.match_id,
            PlayerMapEvent.round_num,
            PlayerMapEvent.team_num,
            PlayerMapEvent.seconds_into_round,
            PlayerMapEvent.u,
            PlayerMapEvent.v,
        )
        .where(
            PlayerMapEvent.match_id.in_(my_teams.keys()),
            PlayerMapEvent.event_type.in_(("kill", "death")),
        )
        .order_by(PlayerMapEvent.match_id, PlayerMapEvent.round_num, PlayerMapEvent.tick)
    ).all()

    by_round: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for sid, mid, round_num, team_num, sir, u, v in rows:
        if (mid, round_num) not in attacker_rounds or team_num != my_teams.get(mid):
            continue
        by_round[(mid, round_num)].append(
            {"steamid": sid, "seconds_into_round": sir, "u": u, "v": v}
        )

    out = []
    for (mid, round_num), events in by_round.items():
        mios = [e for e in events if e["steamid"] == steamid]
        if not mios:
            continue
        out.append(
            {
                "match_id": mid,
                "round_num": round_num,
                "mi_evento": mios[0],  # ya viene ordenado por tick
                "eventos_equipo": [e for e in events if e["steamid"] != steamid],
            }
        )
    return out


def lurker_rate_ventana(s: Session, steamid: str, ventana: int = 20) -> float | None:
    """tasa_lurker sobre las últimas `ventana` partidas del jugador. None
    si no hay ninguna ronda de ataque evaluable en esa ventana (insumo del
    tag de perfil "lurkea_mucho" -- ver recompute_profile_tags)."""
    match_ids = [
        mid
        for (mid,) in s.execute(
            select(MatchPlayer.match_id)
            .join(Match, Match.match_id == MatchPlayer.match_id)
            .where(MatchPlayer.steamid == steamid)
            .order_by(Match.match_id.desc())
            .limit(ventana)
        ).all()
    ]
    rounds = lurker_inputs(s, steamid, match_ids)
    return lurker_domain.tasa_lurker(rounds) if rounds else None


DEFAULT_VENTANA_TAGS = 20

# Expresiones de métrica compartidas entre el agregado global (todos los
# jugadores) y el de la ventana de un usuario -- misma base en ambos lados
# o el percentil no significa nada.
_METRIC_EXPRS = {
    "adr": func.avg(PlayerMatchStats.adr),
    "entry_attempts": func.avg(PlayerMatchStats.entry_kills + PlayerMatchStats.entry_deaths),
    "kill_participation": func.avg(PlayerMatchStats.kills + PlayerMatchStats.assists),
}


def recompute_global_percentiles(s: Session) -> None:
    """Recalcula global_metric_stats: percentiles de cada métrica sobre el
    promedio por-jugador de player_match_stats (una fila-fuente por
    jugador, no por partida -- un jugador con 100 partidas no pesa 100
    veces más). Delete+reinsert completo; se dispara una vez por ingesta."""
    rows = s.execute(
        select(PlayerMatchStats.steamid, *_METRIC_EXPRS.values()).group_by(PlayerMatchStats.steamid)
    ).all()
    por_metrica: dict[str, list[float]] = {m: [] for m in _METRIC_EXPRS}
    for row in rows:
        for metric, valor in zip(_METRIC_EXPRS, row[1:], strict=True):
            por_metrica[metric].append(float(valor or 0.0))

    now = datetime.now(UTC).isoformat()
    s.execute(delete(GlobalMetricStats))
    for metric, valores in por_metrica.items():
        p = percentiles_domain.calcular_percentiles(valores)
        s.add(GlobalMetricStats(metric=metric, **p, n_players=len(valores), calculado_en=now))


def recompute_profile_tags(s: Session, steamid: str, ventana: int = DEFAULT_VENTANA_TAGS) -> None:
    """Recalcula profile_tags_cache para `steamid`: borra e inserta de
    nuevo (idempotente, mismo patrón que ingest_demo con match_id). Se
    dispara al final de ingest_demo para cada jugador de la partida
    recién ingerida -- no hay cron aparte. Emite: lurkea_mucho (mismo
    umbral que el badge de partida, sobre la ventana) + los tags
    relativos-a-global (domain/percentiles.py, contra global_metric_stats
    -- correr recompute_global_percentiles antes)."""
    s.execute(delete(PlayerProfileTag).where(PlayerProfileTag.steamid == steamid))
    now = datetime.now(UTC).isoformat()

    lurker_rate = lurker_rate_ventana(s, steamid, ventana)
    if lurker_rate is not None and lurker_rate >= badges_catalog.LURKEA_MUCHO_MIN_RATE:
        s.add(
            PlayerProfileTag(
                steamid=steamid,
                tag_id="lurkea_mucho",
                detalle={"lurker_rate": lurker_rate},
                calculado_en=now,
                ventana_partidas=ventana,
            )
        )

    globales = {
        g.metric: {"p25": g.p25, "p50": g.p50, "p75": g.p75, "p90": g.p90}
        for g in s.execute(select(GlobalMetricStats)).scalars()
    }
    n_players = s.scalar(select(func.max(GlobalMetricStats.n_players))) or 0
    if globales:
        ventana_ids = (
            select(MatchPlayer.match_id)
            .join(Match, Match.match_id == MatchPlayer.match_id)
            .where(MatchPlayer.steamid == steamid)
            .order_by(Match.match_id.desc())
            .limit(ventana)
        )
        row = s.execute(
            select(*_METRIC_EXPRS.values()).where(
                PlayerMatchStats.steamid == steamid, PlayerMatchStats.match_id.in_(ventana_ids)
            )
        ).one()
        stats_usuario = {
            metric: float(valor) if valor is not None else None
            for metric, valor in zip(_METRIC_EXPRS, row, strict=True)
        }
        for tag in percentiles_domain.evaluar_tags_globales(stats_usuario, globales, n_players):
            s.add(
                PlayerProfileTag(
                    steamid=steamid,
                    tag_id=tag["tag_id"],
                    detalle=tag["detalle"],
                    calculado_en=now,
                    ventana_partidas=ventana,
                )
            )


def profile_tags_for(s: Session, steamid: str) -> list[PlayerProfileTag]:
    """Lectura del cache -- no recalcula nada (ver recompute_profile_tags)."""
    return list(
        s.execute(select(PlayerProfileTag).where(PlayerProfileTag.steamid == steamid)).scalars()
    )


def highlight_moments(
    s: Session, steamid: str, ventana: int = DEFAULT_VENTANA_TAGS, top_n: int = 10
) -> list[dict]:
    """Momentos clipeables del jugador en sus últimas `ventana` partidas:
    kills por ronda (player_map_events) + clutches ganados
    (player_clutches), puntuados por domain/highlights.py. Incluye mapa y
    demo_file para que el render sepa de dónde sacar las posiciones."""
    match_ids = [
        mid
        for (mid,) in s.execute(
            select(MatchPlayer.match_id)
            .join(Match, Match.match_id == MatchPlayer.match_id)
            .where(MatchPlayer.steamid == steamid)
            .order_by(Match.match_id.desc())
            .limit(ventana)
        ).all()
    ]
    if not match_ids:
        return []

    kills_por_ronda = {
        (mid, rnd): count
        for mid, rnd, count in s.execute(
            select(PlayerMapEvent.match_id, PlayerMapEvent.round_num, func.count())
            .where(
                PlayerMapEvent.steamid == steamid,
                PlayerMapEvent.event_type == "kill",
                PlayerMapEvent.match_id.in_(match_ids),
            )
            .group_by(PlayerMapEvent.match_id, PlayerMapEvent.round_num)
        ).all()
    }
    clutches = {
        (c.match_id, c.round_num): c.enemies_at_start
        for c in s.execute(
            select(PlayerClutch).where(
                PlayerClutch.steamid == steamid,
                PlayerClutch.outcome == "won",
                PlayerClutch.match_id.in_(match_ids),
            )
        ).scalars()
    }

    rondas = [
        {
            "match_id": mid,
            "round_num": rnd,
            "steamid": steamid,
            "kills": kills_por_ronda.get((mid, rnd), 0),
            "clutch_enemies": clutches.get((mid, rnd)),
        }
        for mid, rnd in set(kills_por_ronda) | set(clutches)
    ]
    moments = highlights_domain.score_moments(rondas, top_n)

    match_meta = {
        m.match_id: m
        for m in s.execute(select(Match).where(Match.match_id.in_(match_ids))).scalars()
    }
    for mo in moments:
        meta = match_meta.get(mo["match_id"])
        mo["map"] = meta.map if meta else None
        mo["demo_file"] = meta.demo_file if meta else None
    return moments


def economia_inputs(s: Session, match_id: str, steamid: str) -> dict:
    """Insumos de domain/economia.py para los badges de esta partida:
    clasificación de compra ronda a ronda, victorias en force_buy, eco
    frags conectados, y si compró un arma cara estando en eco/semi_eco
    (Millonario). None en `millonario_weapon`/`economia_rate` si el
    jugador no tiene filas en round_economy (partida no re-ingerida con
    --force desde que existe esta feature)."""
    rows = (
        s.execute(
            select(RoundEconomy).where(
                RoundEconomy.match_id == match_id, RoundEconomy.steamid == steamid
            )
        )
        .scalars()
        .all()
    )
    if not rows:
        return {
            "force_buy_wins": 0,
            "eco_frags": 0,
            "millonario_weapon": None,
            "economia_rate": None,
        }

    all_rows = (
        s.execute(select(RoundEconomy).where(RoundEconomy.match_id == match_id)).scalars().all()
    )
    tipo_compra_por_ronda: dict[int, dict[str, str]] = defaultdict(dict)
    for r in all_rows:
        tipo_compra_por_ronda[r.round_num][r.steamid] = economia_domain.clasificar_tipo_compra(
            r.equip_value
        )

    round_winners = dict(
        s.execute(select(Round.round_num, Round.winner_num).where(Round.match_id == match_id)).all()
    )
    team_num = s.scalar(
        select(MatchPlayer.team_num).where(
            MatchPlayer.match_id == match_id, MatchPlayer.steamid == steamid
        )
    )

    force_buy_wins = 0
    clasificaciones = []
    millonario_weapon = None
    for r in rows:
        tipo = tipo_compra_por_ronda[r.round_num][steamid]
        clasificaciones.append(tipo)
        if (
            tipo == "force_buy"
            and team_num is not None
            and round_winners.get(r.round_num) == team_num
        ):
            force_buy_wins += 1
        if millonario_weapon is None and r.armas_compradas:
            compras_ronda = [{"steamid": steamid, "item": item} for item in r.armas_compradas]
            hits = economia_domain.detectar_millonario(
                compras_ronda, tipo_compra_por_ronda[r.round_num]
            )
            if hits:
                millonario_weapon = hits[0]["arma"]

    kills_por_ronda: dict[int, list[dict]] = defaultdict(list)
    for k in s.execute(
        select(Kill.round_num, Kill.attacker, Kill.victim).where(
            Kill.match_id == match_id, Kill.attacker == steamid
        )
    ).all():
        kills_por_ronda[k.round_num].append({"attacker": k.attacker, "victim": k.victim})

    eco_frags = sum(
        len(economia_domain.detectar_eco_frag(ks, tipo_compra_por_ronda.get(rnd, {})))
        for rnd, ks in kills_por_ronda.items()
    )

    return {
        "force_buy_wins": force_buy_wins,
        "eco_frags": eco_frags,
        "millonario_weapon": millonario_weapon,
        "economia_rate": economia_domain.tasa_buena_economia(clasificaciones),
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
