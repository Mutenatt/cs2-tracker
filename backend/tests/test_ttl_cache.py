"""Cache TTL in-memory (infra/ttl_cache.py)."""

from cs2tracker.infra import ttl_cache
from cs2tracker.infra.ttl_cache import TtlCache


def test_get_set_basico():
    c = TtlCache()
    assert c.get("k") is None
    c.set("k", {"a": 1}, ttl=60)
    assert c.get("k") == {"a": 1}


def test_expiracion(monkeypatch):
    c = TtlCache()
    now = 1000.0
    monkeypatch.setattr(ttl_cache.time, "monotonic", lambda: now)
    c.set("k", "v", ttl=30)
    assert c.get("k") == "v"

    now = 1029.9
    assert c.get("k") == "v"
    now = 1030.0
    assert c.get("k") is None
    # La entrada vencida se purga, no queda zombie.
    assert c.get("k") is None


def test_overwrite_renueva_ttl(monkeypatch):
    c = TtlCache()
    now = 0.0
    monkeypatch.setattr(ttl_cache.time, "monotonic", lambda: now)
    c.set("k", "viejo", ttl=10)
    now = 8.0
    c.set("k", "nuevo", ttl=10)
    now = 15.0  # el primer set ya habría vencido; el segundo no
    assert c.get("k") == "nuevo"


def test_clear():
    c = TtlCache()
    c.set("a", 1, ttl=60)
    c.set("b", 2, ttl=60)
    c.clear()
    assert c.get("a") is None
    assert c.get("b") is None
