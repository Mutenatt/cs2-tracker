"""GetNextMatchSharingCode con httpx.MockTransport: sin red real."""

import httpx
import pytest

from cs2tracker.infra.steam_sharecodes import (
    AuthCodeInvalid,
    RateLimited,
    SharecodeChainError,
    get_next_sharecode,
)

ARGS = ("76561198000000000", "AAAA-AAAAA-AAAA", "CSGO-GADqf-jjyJ8-cSP2r-smZRo-TO2xK")


def _client(status: int, body: dict | None = None) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, json=body if body is not None else {})

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_devuelve_el_siguiente_code():
    c = _client(200, {"result": {"nextcode": "CSGO-NUEVO-NUEVO-NUEVO-NUEVO-NUEVO"}})
    assert get_next_sharecode(*ARGS, api_key="k", client=c) == "CSGO-NUEVO-NUEVO-NUEVO-NUEVO-NUEVO"


def test_envia_los_params_correctos():
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(dict(request.url.params))
        return httpx.Response(200, json={"result": {"nextcode": "n/a"}})

    c = httpx.Client(transport=httpx.MockTransport(handler))
    get_next_sharecode(*ARGS, api_key="clave", client=c)
    assert seen == {
        "key": "clave",
        "steamid": ARGS[0],
        "steamidkey": ARGS[1],
        "knowncode": ARGS[2],
    }


def test_na_significa_al_dia():
    c = _client(200, {"result": {"nextcode": "n/a"}})
    assert get_next_sharecode(*ARGS, api_key="k", client=c) is None


def test_202_significa_al_dia():
    assert get_next_sharecode(*ARGS, api_key="k", client=_client(202)) is None


def test_403_auth_code_revocado():
    with pytest.raises(AuthCodeInvalid):
        get_next_sharecode(*ARGS, api_key="k", client=_client(403))


def test_429_rate_limit():
    with pytest.raises(RateLimited):
        get_next_sharecode(*ARGS, api_key="k", client=_client(429))


def test_500_error_generico():
    with pytest.raises(SharecodeChainError):
        get_next_sharecode(*ARGS, api_key="k", client=_client(500))
