"""Test de fetch_premier_profile (Capa 2): mapea la respuesta del sidecar
al rating Premier vigente, y es best-effort (None en cualquier fallo)."""

import httpx

from cs2tracker.infra.gc_client import fetch_premier_profile

SID = "76561198119714832"


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), base_url="http://sidecar")


def test_fetch_premier_profile_ok():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"rating": 12955, "rankChange": 314.0, "wins": 20})

    prof = fetch_premier_profile(SID, base_url="http://sidecar", client=_client(handler))
    assert prof == {"rating": 12955, "rank_change": 314.0, "wins": 20}


def test_fetch_premier_profile_404_es_none():
    # Usuario no amigo / offline: el sidecar devuelve 404, no rompe nada.
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": "PROFILE_UNAVAILABLE"})

    assert fetch_premier_profile(SID, base_url="http://sidecar", client=_client(handler)) is None


def test_fetch_premier_profile_sin_rating_es_none():
    def handler(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"rating": 0})

    assert fetch_premier_profile(SID, base_url="http://sidecar", client=_client(handler)) is None


def test_fetch_premier_profile_error_de_red_es_none():
    def handler(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("sidecar caído")

    assert fetch_premier_profile(SID, base_url="http://sidecar", client=_client(handler)) is None
