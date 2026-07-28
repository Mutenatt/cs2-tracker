"""Configuración central. Se lee de variables de entorno (prefijo CS2_)."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # extra="ignore": una var CS2_* vieja en el .env (p.ej. del spike de
    # sharecodes ya retirado) no debe tirar abajo el arranque.
    model_config = SettingsConfigDict(env_prefix="CS2_", env_file=".env", extra="ignore")

    # DB local del usuario (nunca en el repo). SQLite para MVP.
    db_url: str = "sqlite:///cs2.sqlite"

    # Carpeta que vigila FolderSource (Camino 1).
    demos_dir: Path = Path("demos")

    # Salida de clips renderizados (MP4, gitignored -- regenerables).
    clips_dir: Path = Path("clips")

    # Submuestreo de posiciones (Fase 3): 1 de cada N ticks.
    positions_tick_stride: int = 16

    # API
    api_host: str = "127.0.0.1"
    api_port: int = 8000

    # URL pública de la API (Steam OpenID exige return_to/realm absolutos) y
    # del frontend (a dónde redirigir después de loguear). OJO: mismo host
    # ("localhost") que el frontend a propósito -- la cookie de sesión se
    # setea en la respuesta directa de /auth/callback (fuera del proxy de
    # Vite), y las cookies escopean por host, no por puerto; si acá dijera
    # "127.0.0.1" en vez de "localhost" el navegador no la mandaría de vuelta
    # en los requests a través del proxy (localhost:5173 -> localhost:8000).
    api_public_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"

    # Firma de la cookie de sesión. Si no se define, se genera una al arrancar
    # el proceso (ver auth.py) -- las sesiones no sobreviven un restart, pero
    # nunca hay un secreto débil hardcodeado en el repo.
    session_secret: str | None = None

    # Steam Web API key (https://steamcommunity.com/dev/apikey), opcional:
    # sin ella el login funciona igual, pero no se resuelve display_name/avatar.
    steam_api_key: str | None = None

    # Auto-fetch (modelo Leetify). La API key de arriba es global del
    # servicio; los auth codes y sharecodes son POR USUARIO (tabla users).
    # URL del gc-sidecar (Parte B: sharecode -> URL del demo vía GC); las
    # credenciales de la cuenta bot viven SOLO en el .env del sidecar.
    gc_sidecar_url: str = "http://127.0.0.1:9001"
    # Cada cuánto recorre los usuarios con auto-fetch activo (segundos).
    autofetch_poll_interval: float = 120.0
    # Tope de sharecodes que avanza por usuario por ciclo (rate limit).
    autofetch_max_per_cycle: int = 5
    # Pausa entre llamadas consecutivas a GetNextMatchSharingCode (segundos).
    autofetch_request_spacing: float = 1.5

    # SMTP para verificación de email / reset de contraseña, opcional: sin
    # configurar, infra/mail.py imprime el link a consola (dev-friendly).
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None

    # Secreto compartido para las llamadas gc-sidecar -> backend
    # (api/internal.py: auto-accept de amistad + notificación de partida
    # lista). A propósito NO se autogenera como session_secret: son procesos
    # separados y un secreto efímero por restart del backend rompería la
    # sincronía con el sidecar. Sin configurar, /internal/* responde 401.
    internal_shared_secret: str | None = None

    # Pro scene (Home). Twitch Helix para streams LATAM: credenciales de una
    # app en dev.twitch.tv/console (client credentials, gratis). Sin ellas el
    # bloque de streams responde "no configurado" sin romper nada.
    twitch_client_id: str | None = None
    twitch_client_secret: str | None = None
    # Ídem para Kick (app en kick.com → Settings → Developer, requiere 2FA).
    kick_client_id: str | None = None
    kick_client_secret: str | None = None
    # TTLs del cache in-memory. El ranking de HLTV rota 1 vez por semana, así
    # que 6 h de cache = ~4 requests/día contra Cloudflare (clave para no
    # comernos un ban). Si ninguna fuente respondió, se reintenta antes.
    ranking_cache_ttl: float = 21600.0
    ranking_error_ttl: float = 300.0
    streams_cache_ttl: float = 180.0

    # TZ fija para el feature "Resumen Semanal" (Home): la ventana Lun-Dom y
    # el bucket "partidas por día" se calculan en esta TZ. Global, no por
    # usuario (descartado para v1).
    app_tz: str = "America/Argentina/Cordoba"


settings = Settings()
