# CS2 Tracker

Panel de estadísticas de Counter-Strike 2 a partir de demos `.dem`. Parsea la
demo localmente, guarda en SQLite y muestra un panel estilo tracker.network.

Single-user local por ahora (ver `ROADMAP.md` en la raíz del proyecto anterior).

## Estructura (monorepo)

```
cs2-tracker/
├── backend/                 # Paquete Python instalable
│   ├── pyproject.toml
│   ├── cs2tracker/
│   │   ├── config.py        # Configuración (env)
│   │   ├── db/              # SQLAlchemy: modelos + sesión
│   │   ├── domain/          # Lógica de stats PURA y testeable
│   │   ├── infra/           # Parser de demos + fuentes (folder/steam)
│   │   └── api/             # FastAPI + schemas Pydantic
│   └── tests/               # pytest
├── gc-sidecar/              # Node: sharecode -> URL del demo (Game Coordinator)
└── frontend/                # Vite + React + TypeScript
```

Separación de capas: `domain` no sabe de SQLAlchemy ni de FastAPI; `infra` y
`api` dependen de `domain`, nunca al revés.

## Backend — desarrollo

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

pytest            # tests
ruff check .      # lint
ruff format .     # format
```

### Base de datos (Postgres local)

```bash
cd ..   # cs2-tracker/
docker compose up -d          # Postgres local, ver docker-compose.yml
cd backend
cp .env.example .env          # ajustar CS2_DB_URL si hace falta
alembic upgrade head
```

Los tests siguen usando SQLite en memoria (no necesitan Postgres corriendo). El
`db_url` por defecto (sin `.env`) sigue siendo `sqlite:///cs2.sqlite` para uso
local sin Docker.

## Frontend — desarrollo

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173 (proxya /api -> backend :8000)
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

## Estado

- [x] Esqueleto + capa de dominio (stats) + modelos SQLAlchemy
- [x] Migrar ingesta / fuentes / API al paquete
- [x] Alembic (migraciones)
- [x] Frontend Vite + React + TS (con pulido de alineación)
- [x] CI (GitHub Actions: ruff + pytest + build front)
- [x] Camino 2: auto-fetch estilo Leetify (sharecode chain + gc-sidecar)
- [ ] Migrar `team_num` (split T/CT) y marcador final
- [ ] Fase 3: heatmaps posicionales
