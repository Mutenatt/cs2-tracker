"""
Match share codes de CS2/CS:GO (CSGO-xxxxx-xxxxx-xxxxx-xxxxx-xxxxx).

El sharecode es un entero de 144 bits en base 57 que empaqueta
(matchId, reservationId, tvPort). Decodificarlo es aritmética pura: este
módulo no habla con Steam. La cadena de sharecodes (Web API) vive en
steam_sharecodes.py; la resolución a URL de demo (GC), en gc_client.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Alfabeto oficial de 57 símbolos (sin caracteres ambiguos: 0, 1, l, g...).
_ALPHABET = "ABCDEFGHJKLMNOPQRSTUVWXYZabcdefhijkmnopqrstuvwxyz23456789"

SHARECODE_RE = re.compile(
    r"CSGO-[A-Za-z0-9]{5}-[A-Za-z0-9]{5}-[A-Za-z0-9]{5}-[A-Za-z0-9]{5}-[A-Za-z0-9]{5}"
)


@dataclass(frozen=True)
class DecodedSharecode:
    match_id: int
    reservation_id: int
    tv_port: int


def extract_sharecode(raw: str) -> str | None:
    """Acepta tanto el código pelado como el steam://rungame/.../+csgo_download_match%20CSGO-...
    que copia el cliente de CS2 (así es como realmente lo pegan los usuarios)."""
    m = SHARECODE_RE.search(raw)
    return m.group(0) if m else None


def decode_sharecode(code: str) -> DecodedSharecode:
    """CSGO-... -> (matchId, reservationId, tvPort).

    Los 25 símbolos forman un entero base 57 (dígito menos significativo
    primero); sus 18 bytes big-endian contienen matchId (u64 LE),
    reservationId (u64 LE) y tvPort (u16 LE) — mismo layout que usan
    csgo-sharecode y boiler. Validado contra vectores conocidos.
    """
    m = SHARECODE_RE.search(code)
    if m is None:
        raise ValueError(f"sharecode inválido: {code!r}")
    digits = m.group(0).removeprefix("CSGO-").replace("-", "")
    n = 0
    for ch in reversed(digits):
        n = n * 57 + _ALPHABET.index(ch)
    try:
        raw = n.to_bytes(18, "big")
    except OverflowError as e:
        # 57^25 > 2^144: no todo string con el formato es un code válido.
        raise ValueError(f"sharecode fuera de rango: {code!r}") from e
    return DecodedSharecode(
        match_id=int.from_bytes(raw[0:8], "little"),
        reservation_id=int.from_bytes(raw[8:16], "little"),
        tv_port=int.from_bytes(raw[16:18], "little"),
    )


def encode_sharecode(decoded: DecodedSharecode) -> str:
    """Inverso de decode_sharecode. Permite reconstruir el sharecode de un
    demo ya descargado (sus tres componentes están en el nombre de archivo)
    para volver a pedirle datos al GC — p.ej. backfill de played_at."""
    raw = (
        decoded.match_id.to_bytes(8, "little")
        + decoded.reservation_id.to_bytes(8, "little")
        + decoded.tv_port.to_bytes(2, "little")
    )
    n = int.from_bytes(raw, "big")
    digits = []
    for _ in range(25):
        n, rem = divmod(n, 57)
        digits.append(_ALPHABET[rem])
    s = "".join(digits)
    return f"CSGO-{s[0:5]}-{s[5:10]}-{s[10:15]}-{s[15:20]}-{s[20:25]}"


def match_id_str(decoded: DecodedSharecode) -> str:
    """La clave canónica de partida como la persiste la ingesta: el
    RESERVATION id zero-padded a 21 dígitos. Es el primer número del nombre
    de demo del cliente de CS2 (match730_<reservation>_...) y el único
    componente presente tanto en filenames del cliente como en el sharecode
    — usar matchId acá duplica partidas (bug ya sufrido). Permite dedup
    ANTES de pedir nada al GC."""
    return f"{decoded.reservation_id:021d}"


def demo_filename(decoded: DecodedSharecode) -> str:
    """Nombre de archivo compatible con el naming del cliente de CS2
    (match730_<reservation>_<...>.dem), para que un demo auto-fetcheado
    dedupe contra el mismo demo copiado a mano a la carpeta."""
    return f"match730_{match_id_str(decoded)}_{decoded.match_id}_{decoded.tv_port}.dem"
