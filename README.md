# CS2 Tracker

Panel de estadísticas de Counter-Strike 2 a partir de demos `.dem`. Parsea la
demo, guarda los eventos en una base relacional y muestra un panel estilo
tracker.network (K/D/ADR/KAST/rating, scoreboard, weapon breakdown, heatmaps
de rendimiento).

Producto multi-usuario: cada usuario se autentica (Steam OpenID o email +
password) y ve las partidas donde aparece su steamid, sin importar quién las
subió. Ver `ROADMAP.md` en la raíz del proyecto anterior para el plan de
fases original.

## Estructura (monorepo)

```
cs2-tracker/
├── backend/                 # Paquete Python instalable
│   ├── pyproject.toml
│   ├── cs2tracker/
│   │   ├── config.py          # Configuración (env, pydantic-settings)
│   │   ├── auth.py            # Steam OpenID + cookies firmadas (session_epoch)
│   │   ├── auth_password.py   # Login email/password, tokens (verify/reset/relink/etc.)
│   │   ├── rate_limit.py      # Rate limiting y lockout de cuenta, backed por DB
│   │   ├── ingest.py          # Orquesta parser -> domain -> DB
│   │   ├── maps.py            # Transforms de coordenadas de radar por mapa
│   │   ├── db/                # SQLAlchemy 2.0: modelos + sesión (Postgres/SQLite)
│   │   ├── domain/             # Lógica de stats PURA y testeable (sin DB/framework)
│   │   ├── infra/               # Parser de demos (demoparser2) + fuentes (folder/steam)
│   │   ├── api/                # FastAPI + schemas Pydantic + queries
│   │   └── tools/               # killmap.py y otros scripts standalone
│   ├── alembic/               # Migraciones de DB
│   └── tests/                  # pytest
├── gc-sidecar/               # Node: sharecode -> URL del demo (Game Coordinator)
└── frontend/                 # Vite + React + TypeScript
    └── src/
        ├── views/             # Landing, login/registro, perfil, settings, partidas...
        ├── components/        # Scoreboard, Heatmap, Weapons, lineups, etc.
        └── api.ts / types.ts  # Cliente HTTP tipado hacia el backend
```

Separación de capas: `domain` no sabe de SQLAlchemy ni de FastAPI; `infra` y
`api` dependen de `domain`, nunca al revés.

## Autenticación

Login híbrido: Steam OpenID (recomendado, verificación server-to-server sin
tocar credenciales de Steam del usuario) o registro con email + password.
Sesión vía cookie firmada (`itsdangerous`, no JWT). Incluye:

- Rate limiting y bloqueo de cuenta tras intentos fallidos (`rate_limit.py`).
- 2FA/TOTP opcional con códigos de respaldo de un solo uso.
- Logout remoto ("cerrar sesión en todos los dispositivos").
- Audit log de logins + notificación por email ante IP nueva.
- Cambio de password/email in-place, cambio de cuenta de Steam vinculada,
  borrado de cuenta (preservando el historial compartido de otros jugadores).
- Headers de seguridad (HSTS, X-Frame-Options, CSP report-only) y backstop
  de CSRF por Origin/Referer en los endpoints sensibles.

## Backend — desarrollo

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

pytest              # tests
ruff check .        # lint
ruff format .       # format
mypy .              # type check (no corre en CI, pero está configurado)

cs2-ingest --demo path/to/x.dem                     # ingesta un demo
cs2-ingest --source folder --demos ./demos --once    # ingesta lo que haya y sale
cs2-api                                               # FastAPI en http://127.0.0.1:8000
```

### Base de datos (Postgres local)

```bash
cd ..   # cs2-tracker/
docker compose up -d          # Postgres local, ver docker-compose.yml
cd backend
cp .env.example .env          # ajustar CS2_DB_URL / CS2_SESSION_SECRET si hace falta
alembic upgrade head
```

Los tests siguen usando SQLite en memoria (no necesitan Postgres corriendo). El
`db_url` por defecto (sin `.env`) sigue siendo `sqlite:///cs2.sqlite` para uso
local sin Docker. Los modelos son dialecto-agnósticos a propósito.

## Frontend — desarrollo

```bash
cd frontend
npm install
npm run dev          # http://localhost:5173 (proxya /api -> backend :8000)
npm run build         # tsc -b && vite build (lo que corre CI)
npm run lint           # eslint + prettier --check
```

Levantá el backend (`cs2-api`) en paralelo para datos en vivo.

## Auto-fetch de partidas (Camino 2, modelo Leetify)

Cada usuario vincula desde su perfil dos códigos que él mismo genera en
[la página oficial de Valve](https://help.steampowered.com/en/wizard/HelpWithGameIssue/?appid=730&issueid=128):
su **Game Authentication Code** y un **match sharecode** inicial. **Nunca se
piden credenciales de Steam del usuario** — el auth code solo da acceso a su
historial de partidas vía Web API.

Piezas y flujo:

1. `POST /autofetch/link` guarda los códigos por-usuario (tabla `users`).
2. El worker (`cs2-ingest --source steam`) avanza la cadena de sharecodes de
   cada usuario activo con `GetNextMatchSharingCode` (necesita
   `CS2_STEAM_API_KEY`).
3. El `gc-sidecar/` (Node, cuenta bot del servicio conectada al Game
   Coordinator) resuelve cada sharecode a la URL del replay — ver su README.
4. Se descarga el `.dem.bz2`, se descomprime a `demos/autofetch/` y entra por
   el mismo `ingest_demo` de siempre (dedup por match_id incluido).

```bash
# terminal 1: sidecar (ver gc-sidecar/README.md para el setup de la bot)
cd gc-sidecar && npm install && npm start
# terminal 2: worker
cd backend && cs2-ingest --source steam
```

Los replays de Valve expiran ~30 días y solo hay sharecodes de las últimas 8
partidas de matchmaking/Premier/Wingman.

## Herramientas / índices del proyecto

Cada mitad del monorepo tiene un `PROJECT_INDEX.md` auto-generado (módulos,
dependencias, inventario de archivos) que conviene mirar antes de explorar el
código a mano:

```bash
cd backend && python tools/build_index.py     # backend/PROJECT_INDEX.md
cd frontend && npm run build:index             # frontend/PROJECT_INDEX.md
```

Regenerarlos después de tocar imports/exports o agregar archivos.

## CI (`.github/workflows/ci.yml`)

Dos jobs independientes: `backend` (`ruff check`, `ruff format --check`,
`pytest`) y `frontend` (`npm run build`). Correlos localmente antes de pushear.

## Estado

- [x] Esqueleto + capa de dominio (stats) + modelos SQLAlchemy
- [x] Migrar ingesta / fuentes / API al paquete
- [x] Alembic (migraciones)
- [x] Frontend Vite + React + TS (con pulido de alineación)
- [x] CI (GitHub Actions: ruff + pytest + build front)
- [x] Camino 2: auto-fetch estilo Leetify (sharecode chain + gc-sidecar)
- [x] Multi-tenancy (Steam OpenID + login por email, visibilidad por pertenencia)
- [x] Login robusto: rate limiting, 2FA/TOTP, logout remoto, audit log, headers de seguridad
- [ ] Migrar `team_num` (split T/CT) y marcador final
- [ ] Fase 3: heatmaps posicionales
