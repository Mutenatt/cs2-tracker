"""Test del Resumen Mensual (domain/monthly.py). Puro, sin DB."""

from datetime import UTC, datetime

from cs2tracker.domain.monthly import compute_monthly_summary, month_bounds

TZ = "America/Argentina/Cordoba"


def _row(
    map_="de_mirage",
    won=True,
    kills=20,
    deaths=15,
    adr=90.0,
    kast=70.0,
    hs_pct=40.0,
    rating=1.1,
    entry_kills=2,
    played_at="2026-07-14T12:00:00+00:00",
):
    return {
        "map": map_,
        "won": won,
        "kills": kills,
        "deaths": deaths,
        "adr": adr,
        "kast": kast,
        "hs_pct": hs_pct,
        "rating": rating,
        "entry_kills": entry_kills,
        "played_at": played_at,
    }


def _clutch(
    map_="de_mirage",
    round_num=15,
    enemies_at_start=2,
    kills_in_round=1,
    played_at="2026-07-14T12:00:00+00:00",
):
    return {
        "map": map_,
        "round_num": round_num,
        "enemies_at_start": enemies_at_start,
        "kills_in_round": kills_in_round,
        "played_at": played_at,
    }


def test_month_bounds_dia_1_a_ahora():
    now = datetime(2026, 7, 16, 14, 0, tzinfo=UTC)
    mb = month_bounds(now, TZ)
    assert mb.from_date == "2026-07-01"
    assert mb.to_date == "2026-07-16"
    assert mb.start_utc == datetime(2026, 7, 1, 3, 0, tzinfo=UTC)  # medianoche local UTC-3
    assert mb.days_in_month == 31


def test_month_bounds_febrero_bisiesto():
    now = datetime(2028, 2, 10, 14, 0, tzinfo=UTC)  # 2028 es bisiesto
    mb = month_bounds(now, TZ)
    assert mb.days_in_month == 29


def test_racha_mas_larga_corta_con_derrota_o_indeterminado():
    window = month_bounds(datetime(2026, 7, 16, 14, 0, tzinfo=UTC), TZ)
    rows = [
        _row(won=True, played_at="2026-07-13T12:00:00+00:00"),
        _row(won=True, played_at="2026-07-13T13:00:00+00:00"),
        _row(won=False, played_at="2026-07-13T14:00:00+00:00"),
        _row(won=True, played_at="2026-07-14T10:00:00+00:00"),
        _row(won=True, played_at="2026-07-14T11:00:00+00:00"),
        _row(won=True, played_at="2026-07-14T12:00:00+00:00"),
        _row(won=None, played_at="2026-07-14T13:00:00+00:00"),
    ]
    summary = compute_monthly_summary(rows, [], window)
    assert summary.headline.best_streak_wins == 3


def test_bucket_dia_cruza_medianoche_utc3():
    window = month_bounds(datetime(2026, 7, 16, 14, 0, tzinfo=UTC), TZ)
    # 15/07 02:30 UTC = 14/07 23:30 en UTC-3 -> debe caer en el día "14", no "15".
    rows = [_row(played_at="2026-07-15T02:30:00+00:00")]
    summary = compute_monthly_summary(rows, [], window)
    by_day = {d.day: d.count for d in summary.detail.matches_per_day}
    assert by_day["14"] == 1
    assert by_day["15"] == 0


def test_matches_per_day_tiene_un_bucket_por_cada_dia_del_mes():
    window = month_bounds(datetime(2026, 7, 16, 14, 0, tzinfo=UTC), TZ)
    summary = compute_monthly_summary([_row()], [], window)
    days = [d.day for d in summary.detail.matches_per_day]
    assert days == [f"{d:02d}" for d in range(1, 32)]  # julio tiene 31 días


def test_top_maps_ordena_por_victorias_desempate_partidas_jugadas():
    window = month_bounds(datetime(2026, 7, 16, 14, 0, tzinfo=UTC), TZ)
    rows = [
        _row(map_="de_inferno", won=True),
        _row(map_="de_inferno", won=True),
        _row(map_="de_inferno", won=False),
        _row(map_="de_inferno", won=True),
        _row(map_="de_mirage", won=True),
        _row(map_="de_mirage", won=True),
        _row(map_="de_mirage", won=False),
        _row(map_="de_cache", won=True),
        _row(map_="de_cache", won=False),
    ]
    top = compute_monthly_summary(rows, [], window).detail.top_maps
    assert [m.map_id for m in top] == ["de_inferno", "de_mirage", "de_cache"]
    inferno = next(m for m in top if m.map_id == "de_inferno")
    assert inferno.wins == 3 and inferno.losses == 1


def test_mvp_elige_clutch_mas_grande_desempate_kills_luego_mas_reciente():
    window = month_bounds(datetime(2026, 7, 16, 14, 0, tzinfo=UTC), TZ)
    clutches = [
        _clutch(enemies_at_start=2, kills_in_round=1, played_at="2026-07-13T10:00:00+00:00"),
        _clutch(enemies_at_start=3, kills_in_round=2, played_at="2026-07-14T10:00:00+00:00"),
        _clutch(enemies_at_start=3, kills_in_round=2, played_at="2026-07-15T10:00:00+00:00"),
    ]
    mvp = compute_monthly_summary([_row()], clutches, window).detail.mvp
    assert mvp is not None
    assert mvp.clutch_size == 3
    assert mvp.kills_in_round == 2
    # Empate en tamaño y kills -> gana el más reciente (15/07).
    assert mvp.round == 15


def test_mvp_null_sin_clutches_ganados():
    window = month_bounds(datetime(2026, 7, 16, 14, 0, tzinfo=UTC), TZ)
    assert compute_monthly_summary([_row()], [], window).detail.mvp is None


def test_empty_state_sin_partidas():
    window = month_bounds(datetime(2026, 7, 16, 14, 0, tzinfo=UTC), TZ)
    summary = compute_monthly_summary([], [], window)
    assert summary.totals.matches == 0
    assert summary.totals.winrate == 0
    assert summary.headline.best_streak_wins == 0
    assert summary.detail.mvp is None
    assert len(summary.detail.matches_per_day) == 31
    assert all(d.count == 0 for d in summary.detail.matches_per_day)
