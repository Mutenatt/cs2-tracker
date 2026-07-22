"""
Fuentes de demos. Ambas emiten una ruta a un .dem -> el runner llama al MISMO
ingest_demo(). No hay dos pipelines, hay dos fuentes enchufables.

    Source (ABC)
      |-- FolderSource      Camino 1: watch de carpeta
      |-- SteamAutoSource   Camino 2: auto-fetch estilo Leetify
"""

from __future__ import annotations

import abc
import time
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from cs2tracker.config import settings
from cs2tracker.db import Match, User, init_db
from cs2tracker.infra.demo_download import download_and_extract
from cs2tracker.infra.gc_client import (
    DemoExpired,
    SidecarUnavailable,
    resolve_demo,
    sidecar_healthy,
)
from cs2tracker.infra.sharecode import decode_sharecode, demo_filename, match_id_str
from cs2tracker.infra.steam_sharecodes import (
    AuthCodeInvalid,
    RateLimited,
    SharecodeChainError,
    get_next_sharecode,
)

OnDemo = Callable[[Path], None]


class Source(abc.ABC):
    @abc.abstractmethod
    def poll(self) -> Iterator[Path]:
        """Rutas de .dem nuevos desde la última llamada."""
        raise NotImplementedError

    def run(self, on_demo: OnDemo, interval: float = 5.0) -> None:
        print(f"[{type(self).__name__}] escuchando (cada {interval}s)...")
        while True:
            for dem in self.poll():
                try:
                    on_demo(dem)
                except Exception as e:  # noqa: BLE001 - una falla no tumba el loop
                    print(f"[error] ingiriendo {dem.name}: {e}")
            time.sleep(interval)


class FolderSource(Source):
    """Camino 1: vigila una carpeta; cada .dem/.dem.bz2 nuevo se ingesta."""

    def __init__(self, folder: Path):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self._seen: set[str] = set()

    def poll(self) -> Iterator[Path]:
        candidates = sorted(self.folder.glob("*.dem")) + sorted(self.folder.glob("*.dem.bz2"))
        for p in candidates:
            if p.name in self._seen or not self._is_stable(p):
                continue
            self._seen.add(p.name)
            yield p

    @staticmethod
    def _is_stable(p: Path, wait: float = 1.0) -> bool:
        try:
            s1 = p.stat().st_size
            time.sleep(wait)
            return p.stat().st_size == s1 and s1 > 0
        except OSError:
            return False

    def scan_existing(self) -> list[Path]:
        return list(self.poll())


class SteamAutoSource(Source):
    """
    Camino 2 (modelo Leetify): por cada usuario vinculado avanza su cadena de
    sharecodes (Web API), resuelve la URL vía gc-sidecar (GC) y descarga el
    .dem. NUNCA maneja credenciales de Steam del usuario: solo el auth code
    de match history que él mismo generó en Steam.

    Reglas de avance de la cadena (last_sharecode): solo tras descarga
    exitosa o skip deliberado (demo expirado / partida ya en DB). Con el
    sidecar caído o un fallo de descarga NO se avanza: cero pérdida, se
    reintenta en el próximo ciclo.
    """

    def __init__(
        self,
        download_dir: Path | None = None,
        *,
        api_key: str | None = None,
        sidecar_url: str | None = None,
        max_per_cycle: int | None = None,
        request_spacing: float | None = None,
    ):
        self.download_dir = Path(download_dir or (settings.demos_dir / "autofetch"))
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.api_key = api_key if api_key is not None else settings.steam_api_key
        self.sidecar_url = sidecar_url or settings.gc_sidecar_url
        self.max_per_cycle = max_per_cycle or settings.autofetch_max_per_cycle
        self.request_spacing = (
            request_spacing if request_spacing is not None else settings.autofetch_request_spacing
        )
        # archivo descargado -> steamid dueño de la cadena que lo trajo
        # (para matches.ingested_by_steamid, auditoría).
        self._owners: dict[str, str] = {}
        # archivo descargado -> matchtime del GC en ISO (matches.played_at).
        self._played_at: dict[str, str] = {}

    def owner_of(self, dem: Path) -> str | None:
        return self._owners.get(dem.name)

    def played_at_of(self, dem: Path) -> str | None:
        return self._played_at.get(dem.name)

    def poll(self) -> Iterator[Path]:
        engine = init_db()
        if not self.api_key:
            print("[autofetch] sin CS2_STEAM_API_KEY; ciclo omitido")
            self._mark_cycle_skipped(engine, "missing CS2_STEAM_API_KEY")
            return
        if not sidecar_healthy(base_url=self.sidecar_url):
            print("[autofetch] gc-sidecar no disponible; ciclo omitido")
            self._mark_cycle_skipped(engine, "gc-sidecar unreachable")
            return
        with Session(engine) as s:
            users = s.execute(select(User).where(User.autofetch_status == "active")).scalars().all()
            for user in users:
                try:
                    yield from self._poll_user(s, user)
                except RateLimited:
                    # Afecta a la API key global: cortar el ciclo ENTERO.
                    print("[autofetch] rate limit de Steam; corto el ciclo")
                    user.last_polled_at = datetime.now(UTC).isoformat()
                    user.autofetch_error = "rate limited by Steam"
                    s.commit()
                    return
                except SharecodeChainError as e:
                    print(f"[autofetch] {user.steamid}: {e}")
                    s.commit()

    def _mark_cycle_skipped(self, engine: Engine, reason: str) -> None:
        """Deja rastro de que el poller sigue vivo aunque el ciclo se haya
        saltado entero, para que /autofetch/status distinga "nunca corrió"
        de "corrió pero no había nada nuevo"."""
        with Session(engine) as s:
            users = s.execute(select(User).where(User.autofetch_status == "active")).scalars().all()
            now = datetime.now(UTC).isoformat()
            for user in users:
                user.last_polled_at = now
                user.autofetch_error = reason
            s.commit()

    def _poll_user(self, s: Session, user: User) -> Iterator[Path]:
        user.last_polled_at = datetime.now(UTC).isoformat()
        user.autofetch_error = None
        for step in range(self.max_per_cycle):
            if step > 0 and self.request_spacing > 0:
                time.sleep(self.request_spacing)
            try:
                nxt = get_next_sharecode(
                    user.steamid,
                    user.steam_auth_code or "",
                    user.last_sharecode or "",
                    api_key=self.api_key or "",
                )
            except AuthCodeInvalid as e:
                # El usuario revocó/regeneró su auth code: requiere re-link.
                user.autofetch_status = "revoked"
                user.autofetch_error = str(e)
                s.commit()
                return
            if nxt is None:  # al día
                break

            decoded = decode_sharecode(nxt)
            dest = self.download_dir / demo_filename(decoded)
            # Dedup ANTES de gastar GC: otro usuario pudo traer la misma
            # partida, o el archivo ya está descargado.
            if s.get(Match, match_id_str(decoded)) is not None or dest.exists():
                user.last_sharecode = nxt
                s.commit()
                continue

            try:
                url, match_time = resolve_demo(nxt, base_url=self.sidecar_url)
            except DemoExpired:
                print(f"[autofetch] {dest.name}: demo expirado (~30 días); salto")
                user.last_sharecode = nxt
                s.commit()
                continue
            except SidecarUnavailable as e:
                print(f"[autofetch] sidecar no disponible ({e}); reintento en el próximo ciclo")
                s.commit()
                return

            try:
                dem = download_and_extract(url, dest)
            except Exception as e:  # noqa: BLE001 - fallo transitorio: no avanzar
                print(f"[autofetch] fallo descargando {dest.name}: {e}")
                s.commit()
                return

            self._owners[dem.name] = user.steamid
            if match_time:
                self._played_at[dem.name] = datetime.fromtimestamp(match_time, UTC).isoformat()
            user.last_sharecode = nxt
            user.last_fetched_at = datetime.now(UTC).isoformat()
            # Avanzar ANTES del yield es seguro: el .dem ya está en disco;
            # si la ingesta falla se re-ingesta a mano, la partida no se pierde.
            s.commit()
            yield dem
        s.commit()
