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
3. `npm install`
4. `npm start` — el primer arranque puede pedir el código de Steam Guard por
   consola; después queda persistido un refresh token en `data/` y no vuelve
   a pedirlo.

## API (solo 127.0.0.1)

- `GET /health` → `{steam, gc}`; 200 si hay sesión GC, 503 si no.
- `POST /resolve` body `{"sharecode": "CSGO-..."}` →
  - 200 `{demoUrl, matchId, reservationId, tvPort, matchTime}`
  - 400 `BAD_SHARECODE` — formato inválido
  - 404 `DEMO_EXPIRED` — el GC no tiene URL (replays expiran ~30 días)
  - 503 `GC_NOT_READY` — sin sesión con el GC todavía (reintentá)
  - 502 `GC_ERROR` — timeout u otro fallo hablando con el GC

Los requests al GC van serializados (uno por vez, ≥1s de espacio): es el
comportamiento esperado por Valve y evita bans de la cuenta bot.
