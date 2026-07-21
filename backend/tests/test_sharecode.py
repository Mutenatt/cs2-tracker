"""Decode de match share codes: aritmética pura, sin red."""

import pytest

from cs2tracker.infra.parser import match_id_from_name
from cs2tracker.infra.sharecode import (
    DecodedSharecode,
    decode_sharecode,
    demo_filename,
    encode_sharecode,
    extract_sharecode,
    match_id_str,
)

# Vector de referencia del README de csgo-sharecode (akiver).
VECTOR_CODE = "CSGO-GADqf-jjyJ8-cSP2r-smZRo-TO2xK"
VECTOR = DecodedSharecode(
    match_id=3230642215713767580,
    reservation_id=3230647599455273103,
    tv_port=55788,
)


def test_decode_vector_conocido():
    assert decode_sharecode(VECTOR_CODE) == VECTOR


def test_decode_acepta_url_steam():
    url = f"steam://rungame/730/765611985248/+csgo_download_match%20{VECTOR_CODE}"
    assert decode_sharecode(url) == VECTOR


def test_decode_invalido_levanta():
    with pytest.raises(ValueError):
        decode_sharecode("CSGO-esto-no-es")


def test_extract_sharecode_pelado_y_url():
    assert extract_sharecode(VECTOR_CODE) == VECTOR_CODE
    url = f"steam://rungame/730/765611985248/+csgo_download_match%20{VECTOR_CODE}"
    assert extract_sharecode(url) == VECTOR_CODE
    assert extract_sharecode("cualquier cosa") is None


def test_encode_es_el_inverso_de_decode():
    assert encode_sharecode(VECTOR) == VECTOR_CODE
    assert decode_sharecode(encode_sharecode(VECTOR)) == VECTOR


def test_match_id_str_es_el_reservation_zero_padded_21():
    # La clave canónica es el RESERVATION id (no el matchId): es el único
    # número presente tanto en el sharecode como en el filename del cliente.
    s = match_id_str(VECTOR)
    assert len(s) == 21
    assert s == "003230647599455273103"


def test_demo_filename_dedup_contra_naming_del_cliente():
    # Par REAL observado: el cliente de CS2 nombró este demo
    # match730_003831319103881085310_0668262702_346.dem, y el sharecode de la
    # misma partida decodifica a reservation_id=3831319103881085310. Ambos
    # caminos deben producir la MISMA clave vía match_id_from_name — usar el
    # matchId acá fue el bug que duplicaba partidas.
    d = DecodedSharecode(
        match_id=3831314918435455031, reservation_id=3831319103881085310, tv_port=57646
    )
    assert match_id_from_name(demo_filename(d)) == "003831319103881085310"
    assert (
        match_id_from_name("match730_003831319103881085310_0668262702_346.dem")
        == "003831319103881085310"
    )
