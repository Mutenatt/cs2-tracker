"""Test de detección de momentos destacados. Puro, sin DB."""

from cs2tracker.domain.highlights import score_moments


def test_score_moments_puntua_y_ordena():
    rondas = [
        {"match_id": "m1", "round_num": 3, "steamid": "a", "kills": 5, "clutch_enemies": None},
        {"match_id": "m1", "round_num": 7, "steamid": "a", "kills": 3, "clutch_enemies": 4},
        {"match_id": "m1", "round_num": 9, "steamid": "a", "kills": 2, "clutch_enemies": None},
    ]
    moments = score_moments(rondas)
    # ACE (50) < 3K+clutch 1v4 (30+60=90) -> el clutch queda primero.
    assert [m["label"] for m in moments] == ["3K · Clutch 1v4", "ACE"]
    assert moments[0]["score"] == 90
    # 2 kills sin clutch no es momento.
    assert all(m["round_num"] != 9 for m in moments)


def test_score_moments_clutch_solo_tambien_cuenta():
    rondas = [
        {"match_id": "m1", "round_num": 1, "steamid": "a", "kills": 2, "clutch_enemies": 3},
    ]
    moments = score_moments(rondas)
    assert moments[0]["label"] == "2K · Clutch 1v3"


def test_score_moments_top_n():
    rondas = [
        {"match_id": "m1", "round_num": n, "steamid": "a", "kills": 3, "clutch_enemies": None}
        for n in range(20)
    ]
    assert len(score_moments(rondas, top_n=5)) == 5
