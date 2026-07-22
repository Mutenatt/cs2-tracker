"""
Ingesta unificada: un .dem -> SQLite (via SQLAlchemy). Punto unico al que
llegan las dos fuentes. Orquesta: parser (infra) -> stats (domain) -> DB.

CLI:
    cs2-ingest --demo x.dem
    cs2-ingest --source folder --demos ./demos --once
    cs2-ingest --source folder --demos ./demos
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from cs2tracker import maps
from cs2tracker.config import settings
from cs2tracker.db import (
    Blind,
    Damage,
    Grenade,
    Kill,
    Match,
    MatchPlayer,
    Player,
    PlayerClutch,
    PlayerMapEvent,
    PlayerMapZone,
    PlayerMatchStats,
    Round,
    init_db,
)
from cs2tracker.domain import (
    compute_flash_effectiveness,
    compute_kast,
    compute_rating,
    compute_round_stats,
    compute_stats,
    compute_utility_damage,
    find_clutch_situations,
    find_entry_events,
    find_trade_kills,
    find_traded_deaths,
    seconds_into_round,
)
from cs2tracker.infra.parser import ParsedDemo, match_id_from_name, parse_demo
from cs2tracker.infra.sources import FolderSource, SteamAutoSource

# weapon (de grenades) -> event_type de player_map_events. Decoy queda afuera:
# no tiene métrica de efectividad definida (ver Fase 3 del plan).
_UTILITY_EVENT_TYPES = {
    "flashbang": "flash_thrown",
    "hegrenade": "he_thrown",
    "inferno": "molotov_thrown",
    "smokegrenade": "smoke_thrown",
}
_DAMAGE_WEAPONS = {"hegrenade", "inferno"}


def ingest_demo(
    dem_path: Path,
    *,
    force: bool = False,
    ingested_by: str | None = None,
    played_at: str | None = None,
) -> dict:
    engine = init_db()
    with Session(engine) as s:
        match_id = match_id_from_name(dem_path.name)
        exists = s.get(Match, match_id) is not None
        if exists and not force:
            return {"match_id": match_id, "skipped": True, "reason": "ya ingestado"}
        if exists:
            _purge(s, match_id)

        parsed = parse_demo(dem_path)
        _persist(s, parsed, ingested_by=ingested_by, played_at=played_at)
        s.commit()
        return {
            "match_id": parsed.match_id,
            "map": parsed.map,
            "n_rounds": parsed.n_rounds,
            "kills": len(parsed.kills),
            "damages": len(parsed.damages),
            "players": len(parsed.players),
            "score": parsed.score,
            "skipped": False,
        }


def _purge(s: Session, match_id: str) -> None:
    for model in (
        PlayerClutch,
        PlayerMapEvent,
        Blind,
        Grenade,
        Kill,
        Damage,
        PlayerMatchStats,
        Round,
        MatchPlayer,
        Match,
    ):
        s.execute(delete(model).where(model.match_id == match_id))


def _persist(
    s: Session,
    p: ParsedDemo,
    *,
    ingested_by: str | None = None,
    played_at: str | None = None,
) -> None:
    s.add(
        Match(
            match_id=p.match_id,
            map=p.map,
            demo_file=p.demo_file,
            n_rounds=p.n_rounds,
            ingested_at=datetime.now(UTC).isoformat(),
            # Cuándo se jugó (matchtime del GC); NULL en ingesta manual.
            played_at=played_at,
            # Auditoría (no gatea acceso): steamid cuya cadena de sharecodes
            # trajo este demo, si vino del auto-fetch.
            ingested_by_steamid=ingested_by,
        )
    )
    for sid, name in p.players.items():
        if s.get(Player, sid) is None:
            s.add(Player(steamid=sid, name=name))
        else:
            s.get(Player, sid).name = name
        s.add(
            MatchPlayer(
                match_id=p.match_id,
                steamid=sid,
                team_num=p.teams.get(sid),
                rank=p.ranks.get(sid),
                rank_type=p.rank_types.get(sid),
                comp_wins=p.comp_wins.get(sid),
            )
        )

    for rnd in p.rounds:
        s.add(
            Round(
                match_id=p.match_id,
                round_num=rnd["round_num"],
                end_tick=rnd["tick"],
                winner_num=rnd["winner_roster"],
            )
        )

    s.add_all(Kill(match_id=p.match_id, **k) for k in p.kills)
    s.add_all(Damage(match_id=p.match_id, **d) for d in p.damages)
    s.add_all(
        Grenade(
            match_id=p.match_id,
            round_num=g["round_num"],
            tick=g["tick"],
            thrower=g["thrower"],
            weapon=g["weapon"],
            x=g["x"],
            y=g["y"],
            z=g["z"],
        )
        for g in p.grenades
    )
    s.add_all(
        Blind(
            match_id=p.match_id,
            round_num=b["round_num"],
            tick=b["tick"],
            attacker=b["attacker"],
            victim=b["victim"],
            duration=b["duration"],
        )
        for b in p.blinds
    )

    stats = compute_stats(p.kills, p.damages, p.n_rounds, names=p.players)
    kast = compute_kast(p.kills, p.teams, p.n_rounds)
    round_winners = {r["round_num"]: r["winner_roster"] for r in p.rounds}
    rstats = compute_round_stats(p.kills, p.teams, round_winners)
    for st in stats:
        rs = rstats.get(st.steamid, {})
        s.add(
            PlayerMatchStats(
                match_id=p.match_id,
                steamid=st.steamid,
                kills=st.kills,
                deaths=st.deaths,
                assists=st.assists,
                damage=st.damage,
                adr=round(st.adr(p.n_rounds), 1),
                kd=round(st.kd, 2),
                hs_pct=round(st.hs_pct, 1),
                kast=kast.get(st.steamid, 0.0),
                entry_kills=rs.get("entry_kills", 0),
                entry_deaths=rs.get("entry_deaths", 0),
                k2=rs.get("k2", 0),
                k3=rs.get("k3", 0),
                k4=rs.get("k4", 0),
                k5=rs.get("k5", 0),
                clutches=rs.get("clutches", 0),
                rating=compute_rating(
                    st.kills,
                    st.deaths,
                    st.assists,
                    round(st.adr(p.n_rounds), 1),
                    kast.get(st.steamid, 0.0),
                    p.n_rounds,
                ),
            )
        )

    s.add_all(
        PlayerClutch(
            match_id=p.match_id,
            steamid=c["steamid"],
            round_num=c["round_num"],
            enemies_at_start=c["enemies_at_start"],
            outcome=c["outcome"],
        )
        for c in find_clutch_situations(p.kills, p.teams, round_winners)
    )

    _persist_map_events(s, p, round_winners)


def _persist_map_events(
    s: Session,
    p: ParsedDemo,
    round_winners: dict[int, int | None],
) -> None:
    """Construye player_map_events (kill/death/entry/trade/utilidad) y
    recalcula player_map_zones para cada jugador involucrado. Sin mapa no hay
    transform de radar -> no hay nada que proyectar, se omite."""
    if p.map is None:
        return

    entry_events = find_entry_events(p.kills)
    traded_deaths = find_traded_deaths(p.kills, p.teams)
    trade_kills = find_trade_kills(p.kills, p.teams)
    flash_eff = compute_flash_effectiveness(p.grenades, p.blinds, p.teams)
    utility_dmg = compute_utility_damage(p.grenades, p.damages)
    touched: set[str] = set()

    def round_won(steamid: str, round_num: int | None) -> bool | None:
        winner = round_winners.get(round_num)
        return None if winner is None else winner == p.teams.get(steamid)

    def add_event(steamid: str, event_type: str, round_num, tick, x, y, **extra) -> None:
        uv = maps.to_radar_norm(p.map, x, y) if x is not None and y is not None else None
        gx, gy = maps.to_grid_cell(*uv) if uv else (None, None)
        s.add(
            PlayerMapEvent(
                match_id=p.match_id,
                round_num=round_num,
                tick=tick,
                steamid=steamid,
                event_type=event_type,
                map=p.map,
                team_num=p.teams.get(steamid),
                round_won=round_won(steamid, round_num),
                x=x,
                y=y,
                u=uv[0] if uv else None,
                v=uv[1] if uv else None,
                grid_x=gx,
                grid_y=gy,
                **extra,
            )
        )
        touched.add(steamid)

    for k in p.kills:
        atk, vic = k.get("attacker"), k.get("victim")
        rnd, tick = k.get("round_num"), k.get("tick")
        is_entry = (rnd, vic) in entry_events
        if atk and atk != vic:
            avenged = trade_kills.get((rnd, atk))
            add_event(
                atk,
                "kill",
                rnd,
                tick,
                k.get("attacker_x"),
                k.get("attacker_y"),
                is_entry=is_entry,
                is_trade_kill=avenged is not None,
                avenged_steamid=avenged,
                weapon=k.get("weapon"),
                headshot=k.get("headshot"),
                distance=k.get("distance"),
            )
        if vic:
            add_event(
                vic,
                "death",
                rnd,
                tick,
                k.get("victim_x"),
                k.get("victim_y"),
                is_entry=is_entry,
                is_traded=(rnd, vic) in traded_deaths,
                weapon=k.get("weapon"),
                headshot=k.get("headshot"),
                distance=k.get("distance"),
                seconds_into_round=seconds_into_round(rnd, tick, p.round_freeze_ticks),
            )

    for idx, g in enumerate(p.grenades):
        event_type = _UTILITY_EVENT_TYPES.get(g.get("weapon"))
        thrower = g.get("thrower")
        if event_type is None or not thrower:
            continue
        extra: dict = {}
        if g.get("weapon") == "flashbang":
            eff = flash_eff.get(idx)
            if eff is not None:
                extra["enemies_blinded"] = eff.enemies_blinded
                extra["blind_duration_total"] = eff.blind_duration_total
                extra["teammates_blinded"] = eff.teammates_blinded
        elif g.get("weapon") in _DAMAGE_WEAPONS:
            extra["damage_dealt"] = utility_dmg.get(idx, 0)
        add_event(
            thrower,
            event_type,
            g.get("round_num"),
            g.get("tick"),
            g.get("x"),
            g.get("y"),
            weapon=g.get("weapon"),
            **extra,
        )

    for steamid in touched:
        _rebuild_player_map_zones(s, steamid)


def _rebuild_player_map_zones(s: Session, steamid: str) -> None:
    """player_map_zones es cache, siempre reconstruible desde player_map_events
    (mismo principio que player_match_stats). Recalcula TODAS las zonas del
    jugador, no solo las de la partida recién ingerida -- barato a la escala
    de este prototipo; optimizar a upsert incremental si hace falta."""
    s.execute(delete(PlayerMapZone).where(PlayerMapZone.steamid == steamid))

    events = (
        s.execute(select(PlayerMapEvent).where(PlayerMapEvent.steamid == steamid)).scalars().all()
    )

    buckets: dict[tuple[str, str, int, int], dict] = {}
    for e in events:
        if e.grid_x is None or e.grid_y is None:
            continue
        key = (e.map, e.event_type, e.grid_x, e.grid_y)
        b = buckets.setdefault(
            key,
            {
                "count": 0,
                "entry_count": 0,
                "traded_count": 0,
                "weapon_counts": {},
                "blind_sum": 0.0,
                "blind_n": 0,
                "duration_total": 0.0,
                "damage_sum": 0.0,
                "damage_n": 0,
            },
        )
        b["count"] += 1
        b["entry_count"] += int(e.is_entry)
        b["traded_count"] += int(bool(e.is_traded))
        if e.weapon:
            b["weapon_counts"][e.weapon] = b["weapon_counts"].get(e.weapon, 0) + 1
        if e.enemies_blinded is not None:
            b["blind_sum"] += e.enemies_blinded
            b["blind_n"] += 1
        if e.blind_duration_total is not None:
            b["duration_total"] += e.blind_duration_total
        if e.damage_dealt is not None:
            b["damage_sum"] += e.damage_dealt
            b["damage_n"] += 1

    now = datetime.now(UTC).isoformat()
    for (map_, event_type, gx, gy), b in buckets.items():
        top_weapon = (
            max(b["weapon_counts"], key=b["weapon_counts"].get) if b["weapon_counts"] else None
        )
        s.add(
            PlayerMapZone(
                steamid=steamid,
                map=map_,
                event_type=event_type,
                grid_x=gx,
                grid_y=gy,
                count=b["count"],
                entry_count=b["entry_count"],
                traded_count=b["traded_count"],
                top_weapon=top_weapon,
                avg_enemies_blinded=(b["blind_sum"] / b["blind_n"]) if b["blind_n"] else None,
                total_blind_duration=b["duration_total"] or None,
                avg_damage=(b["damage_sum"] / b["damage_n"]) if b["damage_n"] else None,
                updated_at=now,
            )
        )


def _on_demo(
    dem: Path,
    *,
    force: bool = False,
    ingested_by: str | None = None,
    played_at: str | None = None,
) -> None:
    res = ingest_demo(dem, force=force, ingested_by=ingested_by, played_at=played_at)
    tag = "skip" if res.get("skipped") else "ok"
    print(f"[{tag}] {dem.name} -> {res}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="CS2 Tracker - ingesta")
    ap.add_argument("--demo", type=Path, help="Ingesta un solo .dem")
    ap.add_argument("--source", choices=["folder", "steam"])
    ap.add_argument("--demos", type=Path, default=settings.demos_dir)
    ap.add_argument("--once", action="store_true", help="folder: procesa y sale")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)

    def on_demo(dem: Path) -> None:
        _on_demo(dem, force=args.force)

    if args.demo:
        print(ingest_demo(args.demo, force=args.force))
        return 0

    if args.source == "steam":
        # Subcarpeta propia: un FolderSource vigilando demos/ en paralelo no
        # procesa dos veces lo que baja el auto-fetch.
        src = SteamAutoSource(download_dir=args.demos / "autofetch")

        def on_autofetch_demo(dem: Path) -> None:
            _on_demo(
                dem,
                force=args.force,
                ingested_by=src.owner_of(dem),
                played_at=src.played_at_of(dem),
            )
            # Los datos ya quedaron en la DB; no hace falta conservar el
            # .dem crudo (si no, el disco crece sin límite en producción).
            dem.unlink(missing_ok=True)

        src.run(on_autofetch_demo, interval=settings.autofetch_poll_interval)
        return 0

    src = FolderSource(args.demos)
    if args.once:
        for dem in src.scan_existing():
            on_demo(dem)
        return 0
    src.run(on_demo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
