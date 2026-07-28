"""
Seed de partidas (mapas al azar, todas ganadas o todas perdidas según haga
falta) para llevar el CS Rating del jugador de prueba a un `--target` dado
-- p.ej. 24,999 para dejarlo a una partida de ascender (ver
frontend/src/lib/premierRating.ts::isPromotionalMatch), o 20,000 para
bajarlo de nuevo tras una racha de derrotas.

Sigue el mismo patrón que ya usan las partidas dummy existentes en
cs2.sqlite (match_id zero-padded secuencial, demo_file "dummy_<id>.dem",
bots fijos como compañeros/rivales, rounds con winner_num, stats plausibles)
-- no inventa un esquema nuevo, continúa la serie desde la última partida.
La dirección (ganar o perder) se infiere del signo de target - entry_rank.

Uso:
    python scripts/seed_promo_matches.py [--steamid STEAMID] [--target N] [--count N]
"""

from __future__ import annotations

import argparse
import random
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select
from sqlalchemy.orm import Session

from cs2tracker.db import (
    Match,
    MatchPlayer,
    Player,
    PlayerMatchStats,
    Round,
    User,
    get_engine,
    init_db,
)

MAP_POOL = [
    "de_dust2",
    "de_mirage",
    "de_inferno",
    "de_nuke",
    "de_ancient",
    "de_anubis",
    "de_overpass",
    "de_vertigo",
    "de_train",
]

TEAMMATES = [f"76561199116000{n:03d}" for n in range(1, 5)]  # ya existen como Player
OPPONENTS = [f"76561199117000{n:03d}" for n in range(1, 6)]  # ya existen como Player


def _next_match_id(s: Session) -> int:
    last = s.execute(select(Match.match_id).order_by(Match.match_id.desc()).limit(1)).scalar()
    return int(last) + 1 if last else 1


def _rounds_for(match_id: str, n_wins: int, n_losses: int) -> list[Round]:
    """13-x con las rondas intercaladas al azar, no todas mis victorias
    seguidas -- una racha 13-0 perfecta se ve fabricada."""
    outcomes = [2] * n_wins + [3] * n_losses
    random.shuffle(outcomes)
    return [
        Round(match_id=match_id, round_num=i + 1, winner_num=w, win_reason=1, attacker_roster=None)
        for i, w in enumerate(outcomes)
    ]


def seed(steamid: str, target_rating: int, count: int = 5) -> None:
    init_db()
    with Session(get_engine()) as s:
        if s.get(Player, steamid) is None:
            raise SystemExit(f"steamid {steamid} no existe en players -- creá el jugador primero")

        user = s.get(User, steamid)
        entry_rank = s.execute(
            select(MatchPlayer.rank)
            .where(MatchPlayer.steamid == steamid, MatchPlayer.rank.is_not(None))
            .order_by(MatchPlayer.match_id.desc())
            .limit(1)
        ).scalar()
        if entry_rank is None:
            raise SystemExit(f"{steamid} no tiene ninguna partida Premier previa con rank")

        last_played = s.execute(
            select(Match.played_at).order_by(Match.match_id.desc()).limit(1)
        ).scalar()
        played_at = (
            datetime.fromisoformat(last_played) if last_played else datetime.now(UTC)
        )

        # Reparte los puntos que faltan hasta target_rating en `count` pasos
        # de tamaño creciente (así se ve una progresión, no saltos iguales).
        # Signo positivo = racha ganadora, negativo = racha perdedora.
        delta = target_rating - entry_rank
        if delta == 0:
            raise SystemExit(f"{steamid} ya está en {entry_rank}")
        winning = delta > 0
        weights = [i + 1 for i in range(count)]
        total_w = sum(weights)
        steps = [round(delta * w / total_w) for w in weights]
        steps[-1] += delta - sum(steps)  # ajuste de redondeo, cae en el último

        next_id = _next_match_id(s)
        rank = entry_rank
        for step in steps:
            match_id = f"{next_id:010d}"
            played_at += timedelta(days=random.randint(1, 2), hours=random.randint(0, 6))
            # "n_losses"/"n_rounds" nombrados desde la perspectiva de mi equipo
            # (team_num=2): rondas que NO gana team_num=2 en esta partida.
            n_against = random.randint(3, 9)
            n_rounds = 13 + n_against
            map_name = random.choice(MAP_POOL)

            s.add(
                Match(
                    match_id=match_id,
                    map=map_name,
                    demo_file=f"dummy_{match_id}.dem",
                    tickrate=64,
                    n_rounds=n_rounds,
                    ingested_at=played_at.isoformat(),
                    played_at=played_at.isoformat(),
                    ingested_by_steamid=steamid,
                )
            )
            s.add(
                MatchPlayer(
                    match_id=match_id,
                    steamid=steamid,
                    team_num=2,
                    rank=rank,
                    rank_type=11,
                    comp_wins=None,
                )
            )
            for mate in TEAMMATES:
                s.add(
                    MatchPlayer(
                        match_id=match_id, steamid=mate, team_num=2, rank=None, rank_type=None
                    )
                )
            for opp in OPPONENTS:
                s.add(
                    MatchPlayer(
                        match_id=match_id, steamid=opp, team_num=3, rank=None, rank_type=None
                    )
                )
            if winning:
                rounds = _rounds_for(match_id, n_wins=13, n_losses=n_against)
            else:
                rounds = _rounds_for(match_id, n_wins=n_against, n_losses=13)
            for r in rounds:
                s.add(r)
            if winning:
                stats = dict(
                    kills=random.randint(22, 32),
                    deaths=random.randint(10, 16),
                    assists=random.randint(2, 8),
                    damage=random.randint(1500, 2200),
                    kd=round(random.uniform(1.6, 2.6), 2),
                    hs_pct=round(random.uniform(45.0, 65.0), 1),
                    kast=round(random.uniform(70.0, 85.0), 1),
                    rating=round(random.uniform(1.2, 1.9), 2),
                )
            else:
                stats = dict(
                    kills=random.randint(10, 20),
                    deaths=random.randint(18, 26),
                    assists=random.randint(1, 6),
                    damage=random.randint(900, 1500),
                    kd=round(random.uniform(0.5, 0.9), 2),
                    hs_pct=round(random.uniform(30.0, 55.0), 1),
                    kast=round(random.uniform(45.0, 65.0), 1),
                    rating=round(random.uniform(0.6, 0.95), 2),
                )
            s.add(
                PlayerMatchStats(
                    match_id=match_id,
                    steamid=steamid,
                    adr=round(stats["damage"] / n_rounds, 1),
                    entry_kills=random.randint(1, 5),
                    entry_deaths=random.randint(0, 4),
                    k2=random.randint(0, 5),
                    k3=random.randint(0, 2),
                    k4=random.randint(0, 1),
                    k5=0,
                    clutches=random.randint(0, 2),
                    **stats,
                )
            )

            rank += step
            next_id += 1

        # Rating vigente (vivo del GC): lo que muestra el cartel de perfil.
        # Queda exactamente en target_rating.
        if user is not None:
            user.current_premier_rating = target_rating
            user.current_premier_updated_at = played_at.isoformat()

        s.commit()
        kind = "ganadas" if winning else "perdidas"
        print(f"[ok] {count} partidas {kind} creadas ({next_id - count:010d}..{next_id - 1:010d})")
        print(
            f"[ok] {steamid}: entry_rank final={rank - steps[-1]} "
            f"-> current_premier_rating={target_rating}"
        )
        print(f"[ok] isPromotionalMatch({target_rating}) = {target_rating % 5000 == 4999}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--steamid", default="76561199115599939")
    parser.add_argument("--target", type=int, default=24999)
    parser.add_argument("--count", type=int, default=5)
    args = parser.parse_args()
    seed(args.steamid, args.target, args.count)
