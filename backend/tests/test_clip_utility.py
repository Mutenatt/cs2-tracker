from cs2tracker.domain.clip_utility import estimate_throw_tick


def test_estimate_throw_tick_subtracts_flight_time():
    assert estimate_throw_tick(1000, "hegrenade", round_start_tick=0) == 1000 - 64


def test_estimate_throw_tick_varies_by_weapon():
    he = estimate_throw_tick(1000, "hegrenade", round_start_tick=0)
    smoke = estimate_throw_tick(1000, "smokegrenade", round_start_tick=0)
    # el humo tiene un tiempo de vuelo mayor -> origen estimado más atrás en el tiempo
    assert smoke < he


def test_estimate_throw_tick_clamped_to_round_start():
    assert estimate_throw_tick(50, "smokegrenade", round_start_tick=40) == 40


def test_estimate_throw_tick_unknown_weapon_uses_default():
    assert estimate_throw_tick(1000, "unknown", round_start_tick=0) == 1000 - int(1.2 * 64)


def test_estimate_throw_tick_deterministic():
    a = estimate_throw_tick(500, "flashbang", round_start_tick=0)
    b = estimate_throw_tick(500, "flashbang", round_start_tick=0)
    assert a == b
