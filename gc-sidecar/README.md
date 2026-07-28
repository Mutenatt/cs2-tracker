# gc-sidecar

Microservicio Node que resuelve **match sharecodes → URL del demo** contra el
Game Coordinator de CS2. Es la "Parte B" del auto-fetch estilo Leetify: la
cadena de sharecodes (Parte A) vive en el backend Python
(`cs2tracker/infra/steam_sharecodes.py`); este sidecar solo convierte cada
sharecode en una URL `http://replay{N}.valve.net/730/....dem.bz2`.

Una **única cuenta bot** del servicio sirve a todos los usuarios: el
sharecode en sí es la autorización. La bot no necesita poseer CS2 ni Prime,
y **nunca** se piden credenciales de Steam a los usuarios.

## Setup

1. Crear una cuenta de Steam **dedicada** (no usar una personal: la sesión
   del bot ocupa el "slot" de CS2 de esa cuenta).
2. `cp .env.example .env` y completar `STEAM_BOT_USERNAME` / `STEAM_BOT_PASSWORD`.
   Para el onboarding (auto-accept de amistad + notificación de partida
   lista) completar también `CS2_BACKEND_INTERNAL_URL` (default
   `http://127.0.0.1:8000`) y `GC_SIDECAR_INTERNAL_SECRET`, que debe
   matchear `CS2_INTERNAL_SHARED_SECRET` del `.env` del backend. Sin estas
   dos, el sidecar sigue funcionando para `/resolve` y `/profile`, pero
   nunca auto-acepta amistades ni manda `/notify`.
3. `npm install`
4. `npm start` — el primer arranque puede pedir el código de Steam Guard por
   consola; después queda persistido un refresh token en `data/` y no vuelve
   a pedirlo.

## API (solo 127.0.0.1)

- `GET /health` → `{steam, gc, botSteamId}`; 200 si hay sesión GC, 503 si no.
- `POST /resolve` body `{"sharecode": "CSGO-..."}` →
  - 200 `{demoUrl, matchId, reservationId, tvPort, matchTime}`
  - 400 `BAD_SHARECODE` — formato inválido
  - 404 `DEMO_EXPIRED` — el GC no tiene URL (replays expiran ~30 días)
  - 503 `GC_NOT_READY` — sin sesión con el GC todavía (reintentá)
  - 502 `GC_ERROR` — timeout u otro fallo hablando con el GC
- `POST /notify` body `{"steamid": "...", "message": "..."}` — manda un
  mensaje de chat de Steam (requiere ser amigos; ver auto-accept abajo) →
  200 `{ok: true}` / 400 `BAD_STEAMID`/`BAD_MESSAGE` / 503 `GC_NOT_READY` /
  502 `SEND_FAILED`.

Los requests al GC van serializados (uno por vez, ≥1s de espacio): es el
comportamiento esperado por Valve y evita bans de la cuenta bot.

## Amistad con el bot

Cuando llega una solicitud de amistad entrante, el sidecar le pregunta al
backend (`GET /internal/steam-users/{steamid}/registered`, con el secreto
compartido) si ese steamid es un usuario registrado del sitio; si lo es, la
acepta automáticamente y avisa al backend
(`POST /internal/steam-users/{steamid}/bot-friend-confirmed`). Solicitudes
de cuentas que no están registradas quedan pendientes, sin rechazo
explícito.
