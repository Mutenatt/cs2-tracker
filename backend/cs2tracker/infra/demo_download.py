"""Descarga de replays de Valve: GET streaming + descompresión bz2."""

from __future__ import annotations

import bz2
from pathlib import Path

import httpx


def download_and_extract(
    url: str,
    dest: Path,
    *,
    client: httpx.Client | None = None,
    timeout: float = 300.0,
) -> Path:
    """Descarga el .dem.bz2 y deja el .dem descomprimido en `dest`.

    Streaming + descompresión incremental (los .dem pesan 50-150 MB, nunca
    se cargan enteros en memoria) y escritura atómica: se escribe a .part y
    se renombra al final, así un corte a mitad de descarga no deja un .dem
    truncado que la ingesta confunda con válido.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    decomp = bz2.BZ2Decompressor()

    def _stream(c: httpx.Client) -> None:
        with c.stream("GET", url) as resp:
            resp.raise_for_status()
            with open(part, "wb") as f:
                for chunk in resp.iter_bytes():
                    if chunk:
                        f.write(decomp.decompress(chunk))

    try:
        if client is not None:
            _stream(client)
        else:
            with httpx.Client(timeout=timeout, follow_redirects=True) as c:
                _stream(c)
        part.replace(dest)
    finally:
        part.unlink(missing_ok=True)
    return dest
