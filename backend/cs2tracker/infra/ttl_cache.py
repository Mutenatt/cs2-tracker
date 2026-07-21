"""Cache in-memory con TTL, mínimo y sin dependencias.

Alcanza para los datos de la escena pro (ranking/streams): un solo proceso
API, valores chicos, expiración por tiempo. Si algún día hay varios workers,
esto se reemplaza por algo compartido (tabla o Redis) — la interfaz queda.
"""

from __future__ import annotations

import time
from typing import Any


class TtlCache:
    def __init__(self) -> None:
        # key -> (monotonic de expiración, valor)
        self._data: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._data.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() >= expires_at:
            del self._data[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: float) -> None:
        self._data[key] = (time.monotonic() + ttl, value)

    def clear(self) -> None:
        self._data.clear()


# Singleton compartido por los endpoints (y limpiable desde los tests).
cache = TtlCache()
