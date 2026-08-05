"""
Rate limiting en memoria para los endpoints anónimos de /auth/* (login,
registro, reset de contraseña). Ventana fija por IP, sin dependencias nuevas
ni store externo -- el deploy actual es un solo proceso uvicorn, no hace
falta Redis. Si algún día se corre con múltiples workers/instancias esto deja
de ser efectivo (cada proceso tiene su propio estado) y hay que migrar a un
store compartido.
"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, Request


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str, limit: int, window_seconds: float) -> None:
        now = time.monotonic()
        cutoff = now - window_seconds
        hits = [t for t in self._hits[key] if t > cutoff]
        if len(hits) >= limit:
            self._hits[key] = hits
            raise HTTPException(429, "demasiados intentos, esperá un momento")
        hits.append(now)
        self._hits[key] = hits


_limiter = RateLimiter()


def rate_limit(limit: int, window_seconds: float, key_prefix: str):
    """Dependency factory: limita por IP del request (`request.client.host`)."""

    def _dep(request: Request) -> None:
        ip = request.client.host if request.client else "unknown"
        _limiter.check(f"{key_prefix}:{ip}", limit, window_seconds)

    return _dep
