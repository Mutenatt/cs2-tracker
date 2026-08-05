# Implementación: Clips 2D de rondas (2D Replayer)

Documenta cómo funciona hoy el generador de clips MP4 2D de rondas destacadas: qué hace cada pieza, cómo se conectan backend y frontend, y qué assets hacen falta para que todo funcione.

## Qué hace la feature

El usuario ve, en su perfil, una lista de "momentos destacados" (rondas con buen desempeño) y puede pedir que se genere un clip 2D de esa ronda: un MP4 vertical (9:16, estilo TikTok/Reels) que muestra el radar del mapa con los 10 jugadores moviéndose, sus nombres, sus armas, hacia dónde miran, las granadas que tiraron (en vuelo y al detonar) y dónde murió cada uno. El render corre en el servidor (no en el navegador) y el resultado queda disponible para descargar.

**Estado actual**: el backend está completo y probado. El panel del frontend (`ClipsPanel.tsx`) existe y funciona, pero está intencionalmente oculto (`CLIPS_ENABLED = false`) hasta que se rediseñe su UI — así que hoy la única forma de ver un clip es generándolo manualmente (ver sección "Cómo probarlo").

## Flujo end-to-end

```
Usuario pide un clip (UI, hoy oculta)
        │
        ▼
POST /players/{steamid}/clips  ─────────────────────────┐
        │                                                │
        ▼                                                │
 ClipJob en DB (status=pending) + BackgroundTask         │
        │                                                │
        ▼                                                │
 _render_clip_job(job_id)  ── arma roster (nombres) ─────┤
        │                     desde match_players+players│
        ▼                                                │
 infra/clips.py::render_clip()                           │
   ├─ demoparser2: posiciones, armas, ángulo de vista,    │
   │  eventos de granada, muertes -- TODO en vivo desde   │
   │  el .dem, no desde la DB                             │
   ├─ Pillow: dibuja cada frame sobre el radar oscuro     │
   └─ ffmpeg (vía imageio-ffmpeg): encodea a MP4           │
        │                                                │
        ▼                                                │
 ClipJob.status=done, file_path=clips/clip_N_....mp4      │
        │                                                │
        ▼                                                │
GET /clips/{job_id}/download  ◄──────────────────────────┘
        │
        ▼
Usuario descarga/reproduce el MP4
```

## Backend

### `backend/cs2tracker/infra/clips.py` — el renderer (pieza central)

Es el único módulo que sabe dibujar el clip. No toca la base de datos — recibe todo lo que necesita como parámetros o lo parsea él mismo del `.dem`.

**Fuentes de datos, todas parseadas en vivo del demo con `demoparser2` (acotado a la ventana de ticks de la ronda pedida, no se parsea la partida entera):**

| Dato | De dónde sale | Uso |
|---|---|---|
| Posición (X, Y), equipo, vida | `parser.parse_ticks(["X","Y","team_num","health",...])` | Ubicar el punto de cada jugador en el radar |
| Arma activa | `parser.parse_ticks([..., "active_weapon_name"])` | Ícono de arma/granada en mano |
| Ángulo de vista (yaw) | `parser.parse_ticks([..., "yaw"])` | Cono de dirección de mirada |
| Muertes + posición de la víctima | `parser.parse_event("player_death", player=["X","Y","Z"])` | Marcador X + killfeed |
| Detonación de granadas | `parser.parse_event(...)` sobre `flashbang_detonate`, `hegrenade_detonate`, `inferno_startburn`, `smokegrenade_detonate`, `decoy_detonate` | Posición y tick de impacto |
| Expiración real de humo/fuego | `parser.parse_event("smokegrenade_expired")` / `parser.parse_event("inferno_expire")`, matcheados por `entityid` contra la detonación | Duración real del efecto (en vez de una duración fija aproximada) |
| Lanzamiento real de granadas | `parser.parse_event("weapon_fire")`, filtrado a `weapon_flashbang/hegrenade/molotov/incgrenade/smokegrenade/decoy` | Tick y posición real de dónde se tiró (para la trayectoria) |

Cuando no hay match real (arma soltada al morir, ronda cortada, etc.) se cae a un fallback aproximado: `domain/clip_utility.py::estimate_throw_tick` (resta un tiempo de vuelo fijo por arma) y una duración fija por tipo (`UTILITY_STYLE`).

**Qué dibuja, en orden (capas, todas sobre un frame RGBA con blending real vía `ImageDraw(..., "RGBA")`):**

1. Radar oscuro de fondo (ver más abajo).
2. Título, nombre del jugador destacado, mapa y ronda.
3. Utilidad: línea punteada + ícono de la granada interpolado a lo largo de una trayectoria con un arco cosmético (seno) mientras "vuela"; al detonar, un efecto según el tipo:
   - Humo: 3-4 círculos translúcidos con blur gaussiano (nube).
   - Molotov/incendiario: blobs naranja/rojo con offset determinístico (no un círculo perfecto).
   - Flash: círculo blanco que crece y se desvanece.
   - HE: pulso corto.
   Todos con crecimiento al inicio y fade-out real en el último tramo de su duración.
4. Jugadores vivos: cono de vista (cuña sutil orientada al yaw), punto de color por equipo (naranja/celeste, verde si es el jugador destacado), ícono de arma o granada en mano, etiqueta de nombre flotante semi-transparente (se mezcla si se superponen dos).
5. Jugadores muertos: transición corta (fade) del punto hacia una X gris fija en el lugar de la muerte, con el nombre atenuado.
6. Killfeed (últimas 4 muertes) y watermark.

Cada frame armado se manda directo al `stdin` de un proceso `ffmpeg` (el binario que trae `imageio-ffmpeg`, sin necesitar ffmpeg instalado en el sistema) que va encodeando a H.264 mientras se generan los frames — no se guardan PNGs intermedios en disco.

**Assets pre-generados que usa** (no se generan en cada render, están commiteados):

- `backend/cs2tracker/infra/clip_assets/weapons/*.png` (70 íconos) — rasterizados una vez desde los SVG de `frontend/public/weapons/` con `backend/tools/rasterize_weapon_icons.py` (usa `svglib`+`reportlab`, sin depender de la librería nativa Cairo en runtime).
- `backend/cs2tracker/infra/clip_assets/radar_dark/*.png` (9 mapas del pool Premier) — versión oscura/duotono de los radares de `frontend/public/radar/`, generada una vez con `backend/tools/build_dark_radars.py`.

### `backend/cs2tracker/domain/clip_utility.py`

Única pieza de lógica pura (sin I/O) relacionada a clips: `estimate_throw_tick(detonation_tick, weapon, round_start_tick)` — aproxima el tick de lanzamiento restando un tiempo de vuelo fijo por arma, para cuando no hay un `weapon_fire` real que matchear. Testeado en `backend/tests/test_clip_utility.py`.

### `backend/cs2tracker/api/main.py` — orquestación y endpoints

- `_find_demo(demo_file)`: busca el `.dem` en disco bajo `settings.demos_dir` (los archivos de auto-fetch pueden estar en subcarpetas).
- `_render_clip_job(job_id)`: la `BackgroundTask` que corre el render. Con su propia sesión de DB (corre después de que el request original ya cerró la suya):
  1. Carga el `ClipJob`, la `Match` y el `Player` destacado.
  2. Si el `.dem` no está en disco → `status="error"`.
  3. Arma el `roster` (`{steamid: nombre}`) leyendo `match_players` + `players` de esa partida — esto es lo único que `render_clip()` necesita de la DB, todo lo demás (posiciones, armas, granadas) sale del demo.
  4. Llama a `clips_infra.render_clip(...)`.
  5. Si todo sale bien → `status="done"`, guarda `file_path`. Si algo falla → `status="error"`, guarda el mensaje.
- `POST /players/{steamid}/clips`: crea el `ClipJob` (valida que la ronda pedida sea uno de los "momentos destacados" reales del usuario) y dispara `_render_clip_job` como `BackgroundTask`.
- `GET /players/{steamid}/clips`: lista los clips (jobs) del usuario, con su estado.
- `GET /clips/{job_id}/download`: sirve el MP4. Devuelve 404 tanto si no existe como si es de otro usuario (no revela si existe un clip ajeno).
- `GET /players/{steamid}/highlights`: lista los "momentos destacados" clipeables (no genera nada, solo informa qué se puede clipear).

Todos estos endpoints son privados (`_authorize_self`): un usuario solo puede generar/ver/descargar sus propios clips.

### `backend/cs2tracker/api/queries.py`

- `highlight_moments(s, steamid)`: arma la lista de "momentos destacados" (rondas con buenas kills/clutches) combinando `player_map_events` y `player_clutches`, puntuados por `domain/highlights.py::score_moments`.
- `grenades_for_round(s, match_id, round_num)`: consulta simple a la tabla `grenades` filtrada por ronda. **Ya no la usa el renderer** (que ahora extrae las granadas directo del demo, con más detalle del que guarda la DB — `entityid`, tick de lanzamiento real, etc.) pero se deja como utilidad de consulta genérica por si se necesita en otro endpoint a futuro.

### Modelo de datos (`backend/cs2tracker/db/models.py`)

- `ClipJob`: `id, steamid, match_id, round_num, label, status (pending|rendering|done|error), error, file_path, created_at`. Es la única tabla nueva que le pertenece a esta feature — todo lo demás que usa el render (posiciones, armas, granadas) se lee del `.dem`, no de tablas propias.
- `Grenade`/`Blind`: tablas ya existentes del pipeline de ingest general (alimentan los heatmaps de utilidad), reutilizadas parcialmente pero no son la fuente principal del renderer de clips.

### Scripts de soporte (`backend/tools/`)

- `rasterize_weapon_icons.py`: corre una sola vez, convierte los SVG de armas a PNG con transparencia real. Se vuelve a correr solo si cambia el set de armas.
- `build_dark_radars.py`: corre una sola vez, genera la variante oscura/duotono de los 9 radares. Se vuelve a correr solo si cambian los radares fuente.
- `render_clip_smoketest.py`: script manual (no es un test de pytest) para generar un clip directo contra una partida/ronda ya ingerida en la DB local, sin pasar por la API/auth — es la forma de probar el renderer durante el desarrollo.

## Frontend

### `frontend/src/components/ClipsPanel.tsx`

Componente que:
1. Al montar, pide `getHighlights(steamid)` (momentos destacados) y `getClips(steamid)` (clips ya generados/en curso).
2. Mientras haya clips en estado `pending`/`rendering`, hace polling cada 4s para actualizar el estado.
3. Por cada momento destacado, muestra un botón "Generar clip" (llama `createClip`) o, si ya hay un job para esa ronda, su estado (`En cola…`, `Renderizando…`, `Listo` con link de descarga, o `Reintentar` si dio error).

**Hoy está deshabilitado a propósito**: la constante `CLIPS_ENABLED = false` hace que el componente muestre solo un placeholder ("En desarrollo"). Se mantiene así hasta que se rediseñe esta pantalla (pendiente, fuera del alcance de lo ya implementado).

Se monta en `frontend/src/views/ProfileView.tsx`, solo en el perfil propio (`user.steamid === steamid`) — es una feature privada, como el resumen mensual.

### `frontend/src/api.ts`

Funciones que hablan con los endpoints de arriba:
- `getHighlights(steamid)` → `GET /players/{steamid}/highlights`
- `getClips(steamid)` → `GET /players/{steamid}/clips`
- `createClip(steamid, matchId, roundNum)` → `POST /players/{steamid}/clips`
- `clipDownloadUrl(jobId)` → arma la URL de `GET /clips/{jobId}/download` (se usa como `href` directo, no hace un fetch)

### `frontend/src/types.ts`

Tipos que reflejan los schemas Pydantic del backend: `HighlightMoment` (match_id, round_num, score, label, map, demo_available) y `ClipJob` (id, match_id, round_num, label, status, error, created_at).

### `frontend/public/weapons/` y `frontend/public/radar/`

Son los assets **fuente** (SVG de armas, PNG de radares a color) que el frontend ya usa para otras pantallas (`WeaponSilhouette.tsx`, `Heatmap.tsx`, `DuelMatrix.tsx`). El backend no los lee en tiempo real: los scripts de `backend/tools/` los convierten una vez a las versiones que necesita el renderer (íconos con transparencia, radar oscuro) y esas copias procesadas quedan en `backend/cs2tracker/infra/clip_assets/`. Si se agregan armas o se actualiza un radar en el frontend, hay que volver a correr esos scripts para que el cambio llegue a los clips.

## Cómo probarlo hoy (sin pasar por la UI, que está oculta)

```bash
cd cs2-tracker/backend
python tools/render_clip_smoketest.py \
  --db cs2.sqlite --demos demos \
  --match <match_id> --round <round_num> \
  --out clips/mi_prueba.mp4
```

Para probar el flujo real end-to-end (API + auth + polling) hay que reactivar temporalmente `CLIPS_ENABLED = true` en `ClipsPanel.tsx` en local, generar el clip desde la UI, y revertir el flag antes de commitear.

## Qué falta / limitaciones conocidas

- **UI**: `ClipsPanel.tsx` sigue con el diseño viejo y oculto — el rediseño visual de esa pantalla es trabajo aparte, no incluido acá.
- **Trayectoria de granada**: es una aproximación cosmética (línea recta + arco senoidal), no una física real de proyectil.
- **Duración de utilidad**: real para humo/fuego (vía eventos `*_expired`/`*_expire`), aproximada por tiempo fijo para flash/HE/decoy (no tienen un evento de expiración en el demo).
- **Render 3D real** (footage del juego): descartado a propósito — requeriría CS2 corriendo con GPU vía HLAE, no puede correr headless en un server.
