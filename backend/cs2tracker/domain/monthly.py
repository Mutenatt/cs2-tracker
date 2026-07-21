"""Resumen Mensual (Home): agrega stats ya persistidas del mes calendario
actual (día 1 -> hoy, TZ fija). Puro -- sin DB ni FastAPI, recibe filas ya
resueltas por api/queries.py y devuelve dataclasses."""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass, field
from datetime import UTC, datetime
from zoneinfo import ZoneInfo


@dataclass
class MonthBounds:
    start_utc: datetime
    end_utc: datetime
    from_date: str
    to_date: str
    tz: str
    days_in_month: int


def month_bounds(now: datetime, tz_name: str) -> MonthBounds:
    """Ventana [día 1 00:00 local, ahora] en la TZ dada. `now` debe venir
    con tzinfo (UTC típicamente, ver api/main.py)."""
    tz = ZoneInfo(tz_name)
    now_local = now.astimezone(tz)
    first_of_month_local = now_local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    _, days_in_month = monthrange(now_local.year, now_local.month)
    return MonthBounds(
        start_utc=first_of_month_local.astimezone(UTC),
        end_utc=now.astimezone(UTC),
        from_date=first_of_month_local.date().isoformat(),
        to_date=now_local.date().isoformat(),
        tz=tz_name,
        days_in_month=days_in_month,
    )


def _local_day_of_month(iso_ts: str, tz_name: str) -> int:
    dt = datetime.fromisoformat(iso_ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(ZoneInfo(tz_name)).day


@dataclass
class MonthlyTotals:
    matches: int
    winrate: int  # 0..100
    kd: float


@dataclass
class MonthlyHeadline:
    best_streak_wins: int
    rating: float
    hs_pct: int  # 0..100


@dataclass
class MatchesPerDay:
    day: str  # "01".."31", zero-padded día del mes
    count: int


@dataclass
class TopMap:
    map_id: str
    wins: int
    losses: int


@dataclass
class MonthlyMvp:
    map_id: str
    round: int
    clutch_size: int
    kills_in_round: int


@dataclass
class MonthlyDetail:
    adr_avg: float
    kast_pct: int
    clutches_won: int
    entry_kills: int
    matches_per_day: list[MatchesPerDay] = field(default_factory=list)
    top_maps: list[TopMap] = field(default_factory=list)
    mvp: MonthlyMvp | None = None


@dataclass
class MonthlySummary:
    window: MonthBounds
    totals: MonthlyTotals
    headline: MonthlyHeadline
    detail: MonthlyDetail


def _empty_matches_per_day(days_in_month: int) -> list[MatchesPerDay]:
    return [MatchesPerDay(day=f"{d:02d}", count=0) for d in range(1, days_in_month + 1)]


def _best_win_streak(rows_sorted: list[dict]) -> int:
    """Racha de victorias consecutivas más larga, rows ya ordenadas por
    fecha asc. Derrota o resultado indeterminado (won=None, partida
    terminada anticipadamente) cortan la racha por igual."""
    best = cur = 0
    for r in rows_sorted:
        if r.get("won") is True:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def _top_maps(rows: list[dict], limit: int = 3) -> list[TopMap]:
    agg: dict[str, dict] = {}
    for r in rows:
        m = r.get("map")
        if not m:
            continue
        a = agg.setdefault(m, {"wins": 0, "losses": 0, "played": 0})
        a["played"] += 1
        if r.get("won") is True:
            a["wins"] += 1
        elif r.get("won") is False:
            a["losses"] += 1
    ordered = sorted(agg.items(), key=lambda kv: (-kv[1]["wins"], -kv[1]["played"]))
    return [TopMap(map_id=m, wins=a["wins"], losses=a["losses"]) for m, a in ordered[:limit]]


def _select_mvp(clutches: list[dict]) -> MonthlyMvp | None:
    """El clutch ganado más grande (mayor X en 1vX); desempate por kills
    del jugador en la ronda, luego el más reciente."""
    if not clutches:
        return None
    best = max(
        clutches,
        key=lambda c: (c["enemies_at_start"], c["kills_in_round"], c["played_at"]),
    )
    return MonthlyMvp(
        map_id=best["map"],
        round=best["round_num"],
        clutch_size=best["enemies_at_start"],
        kills_in_round=best["kills_in_round"],
    )


def compute_monthly_summary(
    rows: list[dict],
    clutches: list[dict],
    window: MonthBounds,
) -> MonthlySummary:
    """rows: una fila por partida de la ventana (ya filtrada por la query),
    con map/won/kills/deaths/adr/kast/hs_pct/rating/entry_kills/played_at.
    clutches: clutches GANADOS de la ventana, con kills_in_round ya resuelto
    (ver api/queries.py::monthly_clutches_won)."""
    matches = len(rows)
    if matches == 0:
        return MonthlySummary(
            window=window,
            totals=MonthlyTotals(matches=0, winrate=0, kd=0.0),
            headline=MonthlyHeadline(best_streak_wins=0, rating=0.0, hs_pct=0),
            detail=MonthlyDetail(
                adr_avg=0.0,
                kast_pct=0,
                clutches_won=0,
                entry_kills=0,
                matches_per_day=_empty_matches_per_day(window.days_in_month),
                top_maps=[],
                mvp=None,
            ),
        )

    wins = sum(1 for r in rows if r.get("won") is True)
    total_kills = sum(r["kills"] for r in rows)
    total_deaths = sum(r["deaths"] for r in rows)
    ordered = sorted(rows, key=lambda r: r["played_at"])

    per_day = _empty_matches_per_day(window.days_in_month)
    by_day = {d.day: d for d in per_day}
    for r in rows:
        day_key = f"{_local_day_of_month(r['played_at'], window.tz):02d}"
        by_day[day_key].count += 1

    return MonthlySummary(
        window=window,
        totals=MonthlyTotals(
            matches=matches,
            winrate=round(100.0 * wins / matches),
            kd=round(total_kills / total_deaths, 2) if total_deaths else float(total_kills),
        ),
        headline=MonthlyHeadline(
            best_streak_wins=_best_win_streak(ordered),
            rating=round(sum(r["rating"] for r in rows) / matches, 2),
            hs_pct=round(sum(r["hs_pct"] for r in rows) / matches),
        ),
        detail=MonthlyDetail(
            adr_avg=round(sum(r["adr"] for r in rows) / matches, 1),
            kast_pct=round(sum(r["kast"] for r in rows) / matches),
            clutches_won=len(clutches),
            entry_kills=sum(r["entry_kills"] for r in rows),
            matches_per_day=per_day,
            top_maps=_top_maps(rows),
            mvp=_select_mvp(clutches),
        ),
    )
