# cStats — Arquitectura y estado actual

Documento de referencia del monorepo `cs2-tracker/`. Describe qué hay hoy en
la rama de trabajo, no el plan futuro (para eso ver `ROADMAP.md` en la raíz).

Fecha del snapshot: 2026-07-28 · rama `videos_lineups`.

---

## 1. Qué es

cStats parsea demos (`.dem`) de Counter-Strike 2, persiste los eventos en una
base relacional y sirve un panel de estadísticas estilo tracker.network:
scoreboard, K/D/ADR/KAST/rating, desglose por arma, heatmaps, duelos,
economía, badges, highlights/clips, resumen mensual, perfil de jugador y una
sección de line ups en video.

Nació como herramienta local monousuario y hoy es un producto multiusuario con
registro por email + contraseña, vínculo obligatorio a Steam e ingesta
automática de partidas.

Los comentarios y docstrings del código están en español.

---

## 2. Topología del repo

```
cs2-tracker/
├── backend/          FastAPI + SQLAlchemy 2.0 + Alembic (paquete cs2tracker)
├── frontend/         Vite + React + TypeScript
├── gc-sidecar/       Servicio Node que habla con el Steam Game Coordinator
├── docker-compose.yml
└── .github/workflows/ci.yml
```

Los `.py` en la raíz del repo (fuera de `cs2-tracker/`) son el MVP
pre-monorepo: referencia histórica, no se extienden.

### Servicios en `docker-compose.yml`

| Servicio           | Qué hace                                                  |
| ------------------ | --------------------------------------------------------- |
| `db`               | PostgreSQL 16 (alpine)                                     |
| `api`              | FastAPI (`cs2-api`)                                        |
| `autofetch-worker` | Loop de ingesta automática por usuario                     |
| `gc-sidecar`       | Node, puente al Steam Game Coordinator (puerto 9001)       |
| `frontend`         | Build de Vite servido estático                             |

---

## 3. Backend

### 3.1 Regla de capas

Dependencia estrictamente unidireccional:
**`domain` no depende de nada del proyecto; `infra` y `api` dependen de
`domain`, nunca al revés.**

### 3.2 `domain/` — lógica pura, sin DB ni framework

Recibe dicts/primitivos y devuelve dataclasses o dicts. Es lo que se testea
unitariamente aislado.

| Módulo           | Responsabilidad                                                    |
| ---------------- | ------------------------------------------------------------------ |
| `stats.py`       | K/D/A, HS%, daño, ADR por jugador                                   |
| `kast.py`        | KAST%, incluye detección de trade kills por ventana de ticks        |
| `rounds.py`      | Entry kills/deaths, multikills (2K–5K), clutches                    |
| `rating.py`      | Aproximación al rating HLTV 2.0 desde KPR/DPR/APR/ADR/KAST          |
| `teams.py`       | Qué roster ganó cada ronda (correcto a través de cambios de bando)  |
| `duels.py`       | Matriz de duelos jugador vs jugador                                 |
| `economia.py`    | Economía por ronda (buys, eco, force)                               |
| `utility.py`     | Uso de granadas, flashes, friendly flashes                          |
| `loadouts.py`    | Armamento por ronda                                                 |
| `roles.py`       | Inferencia de rol                                                   |
| `lurker.py`      | Detección de comportamiento lurker                                  |
| `highlights.py`  | Selección de momentos destacables (base de los clips)               |
| `coach.py`       | Sugerencias derivadas de las métricas                               |
| `percentiles.py` | Percentiles contra `global_metric_stats`                            |
| `monthly.py`     | Agregados del resumen mensual                                       |
| `profile.py`     | Composición del perfil de jugador                                   |
| `social.py`      | Squad / compañeros frecuentes                                       |
| `badges/`        | Catálogo, evaluador y render de insignias por partida               |

### 3.3 `infra/` — único lugar que toca sistemas externos

| Módulo                 | Responsabilidad                                                     |
| ---------------------- | ------------------------------------------------------------------- |
| `parser.py`            | Envuelve `demoparser2`; extrae eventos crudos a un `ParsedDemo`      |
| `sources.py`           | Fuentes de demos enchufables (`FolderSource`, fuente Steam)          |
| `gc_client.py`         | Cliente HTTP del `gc-sidecar`                                        |
| `sharecode.py`         | Decodificación de share codes de CS2                                 |
| `steam_sharecodes.py`  | Obtención de share codes nuevos por usuario                          |
| `demo_download.py`     | Descarga del `.dem` desde la URL de la partida                       |
| `clips.py`             | Generación de clips de highlights (`clip_jobs`)                      |
| `mail.py`              | SMTP: verificación de email y reset de contraseña                    |
| `twitch.py`/`kick.py`  | Streams en vivo de la escena; `streams_common.py` normaliza          |
| `hltv_ranking.py`      | Ranking de equipos                                                   |
| `steam_news.py`        | Novedades de CS2                                                     |
| `ttl_cache.py`         | Caché en memoria con TTL usada por los módulos de escena             |

### 3.4 `ingest.py`

Orquesta parser → domain → DB. Punto de entrada único (`ingest_demo`) para
todas las fuentes. Idempotente por `match_id` (derivado del ID de reserva en
el nombre del archivo): reingerir purga y reemplaza salvo que ya exista.

Convención: **parsear la demo una vez, persistir, consultar muchas.** Si
cambia una fórmula, se recomputa desde las tablas de eventos, no se
re-parsea.

### 3.5 `db/` — modelos (SQLAlchemy 2.0, dialect-agnostic)

Tablas de identidad y catálogo:
`users` (PK steamid; email/password, verificación, onboarding, demografía,
autofetch, premier rating actual), `account_signups`, `players`, `matches`,
`match_players` (incluye rank), `rounds`.

Tablas de eventos crudos:
`kills`, `damages`, `grenades`, `blinds`, `round_economy`,
`player_map_events` (fan-out por jugador: kill/death/entry/trade/utility, con
`place` y `seconds_into_round`).

Tablas de caché (siempre reconstruibles desde los eventos):
`player_match_stats`, `player_map_zones`, `player_clutches`,
`player_profile_tags`, `global_metric_stats`.

Operacional: `clip_jobs`.

Migraciones en `backend/alembic/versions/` (~21 revisiones; la más reciente
introduce login por email+contraseña, onboarding/demografía y premier rating).

### 3.6 `api/` — FastAPI

- `main.py` — app y endpoints de partidas/jugadores.
- `account.py` (`/auth/*`) — registro, verificación de email, login, logout,
  forgot/reset password, link a Steam y callback OpenID, `/me`.
- `onboarding.py` — estado, demografía y cierre del onboarding.
- `autofetch.py` — status, vincular y desvincular la ingesta automática.
- `scene.py` — ranking de equipos y streams en vivo.
- `internal.py` — endpoints de servicio para el `gc-sidecar`
  (protegidos por `internal_shared_secret`).
- `queries.py` — consultas cross-match para heatmaps; lee `player_map_zones`
  (fast path) con `MIN_SAMPLE = 5` filtrado en lectura, no en escritura.
- `schemas.py` — Pydantic; el frontend los espeja en `types.ts`.

Endpoints principales:

```
GET  /matches                              GET  /matches/{id}
GET  /matches/{id}/kills                   GET  /matches/{id}/duels
GET  /matches/{id}/weapons                 GET  /matches/{id}/badges
GET  /matches/{id}/clutches                GET  /matches/{id}/economy
GET  /players/{steamid}/heatmaps/{deaths|entries|trades|utility}
GET  /players/{steamid}/profile            GET  /players/{steamid}/profile-tags
GET  /players/{steamid}/weapons-detail     GET  /players/{steamid}/monthly
GET  /players/{steamid}/rivals             GET  /players/{a}/compare/{b}
GET  /players/{steamid}/highlights         POST /players/{steamid}/clips
GET  /players/{steamid}/clips              GET  /clips/{job_id}/download
GET  /news/cs2                             GET  /scene/ranking  /scene/streams
```

### 3.7 Autenticación y visibilidad

Registro con email + contraseña (`auth_password.py`), verificación por mail y
**vínculo a Steam obligatorio** vía OpenID (`auth.py`): el usuario se loguea
en steamcommunity.com y se verifica el callback firmado server-to-server —
ninguna credencial de Steam pasa por el servidor. Sesión = cookie firmada con
`itsdangerous` (no JWT). Sin `CS2_SESSION_SECRET` se genera una aleatoria por
proceso.

Visibilidad **por pertenencia**, no por propiedad: un usuario ve una partida
si su steamid aparece en `match_players` (`queries.shares_a_match`).
`matches.ingested_by_steamid` es sólo auditoría.

### 3.8 Configuración

`config.py` (pydantic-settings, prefijo `CS2_`, lee `.env`). Claves: `db_url`
(cae a SQLite local sin `.env`), `demos_dir`, `clips_dir`,
`positions_tick_stride`, URLs pública/frontend, `session_secret`,
`steam_api_key`, `gc_sidecar_url`, parámetros de autofetch, SMTP,
`internal_shared_secret`, credenciales Twitch/Kick, TTLs de caché y `app_tz`.

---

## 4. Ingesta automática (autofetch)

```
gc-sidecar (Node, Steam GC)  →  share codes nuevos
        ↓
infra/steam_sharecodes.py → sharecode.py → demo_download.py
        ↓
ingest.py  →  domain/*  →  DB
```

El worker `autofetch-worker` corre el loop (`autofetch_poll_interval`,
`autofetch_max_per_cycle`, `autofetch_request_spacing`). El sidecar confirma
la amistad con el bot vía `/internal/steam-users/{steamid}/*`.

---

## 5. Frontend

Vite + React + TypeScript + react-router. `api.ts` es la única capa de
llamadas; `types.ts` espeja los schemas Pydantic. `UserContext` mantiene la
sesión.

Rutas públicas: `/`, `/register`, `/login`, `/forgot-password`,
`/reset-password` (más pantallas de verificación pendiente y onboarding).

Rutas autenticadas: `/`, `/lineups`, `/profile/:steamid`,
`/profile/:steamid/weapons`, `/match/:matchId`, `/settings`.

Componentes destacados: `Scoreboard`, `Weapons` + `WeaponSilhouette`,
`Heatmap`, `DuelMatrix`, `ClutchTimeline`, `EconomyTimeline`, `BadgeStrip`,
`CoachCorner`, `ClipsPanel`, `AccuracyPanel`, `RankBadge` /
`RankHistoryCard`, `SquadCard`, `HeroStreamCarousel`, `MapWallpaperCarousel`
y el set `monthly/`.

### Line Ups (trabajo en curso, sin commitear)

`views/LineUps.tsx` consume `src/data/lineups.ts`, que castea
`src/data/lineups.json`. Ese JSON lo genera
`backend/scripts/upload_lineups.py` a partir del nombre de cada `.mp4` en
`frontend/public/lineups/<mapa>/` (carpeta gitignoreada), parseando la
gramática `<granada>-<bando>-<callout>[-calificadores]`. Emite además
`backend/manifest_lineups.json` (metadata completa: título SEO, descripción,
tags), que sí se versiona. `de_mirage` está excluida a propósito: se procesó
a mano y su naming no sigue la gramática. Cubierto por
`backend/tests/test_lineups_manifest.py`.

---

## 6. Convenciones

- `team_num`: `2` = T, `3` = CT (convención de CS2, usada en DB, domain y API).
- Coordenadas: `maps.py::MAP_TRANSFORMS` proyecta mundo → radar normalizado
  `(u, v)`; las celdas de grilla de los heatmaps derivan de esa misma
  proyección.
- La tabla pesada `positions` por tick **no** existe: está deferida hasta que
  una feature la necesite.
- `demos/`, `*.dem`, `*.sqlite` y `.env` están gitignoreados.

---

## 7. Comandos

```bash
# Backend (cs2-tracker/backend)
pip install -e ".[dev]"
pytest                 # ruff check . / ruff format --check . / mypy .
cs2-ingest --demo path/to/x.dem
cs2-ingest --source folder --demos ./demos --once
cs2-api                # http://127.0.0.1:8000
alembic upgrade head

# Frontend (cs2-tracker/frontend)
npm install && npm run dev      # http://localhost:5173, proxy /api -> :8000
npm run build                   # lo que corre CI
npm run lint

# Infra
docker compose up -d
```

CI (`.github/workflows/ci.yml`): dos jobs independientes — `backend`
(ruff check, ruff format --check, pytest) y `frontend` (npm run build).

---

## 8. Estado actual

**Funcionando:** parseo e ingesta idempotente; todo el cálculo de dominio;
API completa de partida/jugador; auth email+password con verificación, reset
y vínculo Steam obligatorio; onboarding; autofetch con sidecar GC; escena
(ranking, streams, news); clips de highlights; frontend con todas las vistas
listadas. ~40 archivos de test en `backend/tests/` más e2e con Playwright en
`frontend/e2e/`.

**En curso (sin commitear en `videos_lineups`):** la sección Line Ups —
generador `upload_lineups.py`, `manifest_lineups.json`, `lineups.json` /
`lineups.ts` y la vista `LineUps.tsx`.

**Pendiente / deuda:** la tabla `positions` por tick sigue diferida;
`tools/killmap.py` es un prototipo standalone fuera del flujo API/frontend;
`mypy` está configurado pero no corre en CI.
