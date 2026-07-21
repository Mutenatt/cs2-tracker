# Cómo cargar tus partidas (ingesta manual)

Mientras la descarga automática (Fase 5, Parte B) no está implementada, así se
cargan tus partidas a mano — es un solo paso de copiar un archivo.

## 1. Descargá la demo desde el cliente de CS2

1. Abrí CS2 → pestaña **Watch** → sub-pestaña **Your Matches**.
2. Elegí la partida que querés analizar → click en el ícono de descarga (nube).
3. Cuando termina, el archivo queda guardado automáticamente en:

```
<tu Steam library>\steamapps\common\Counter-Strike Global Offensive\game\csgo\replays\
```

En esta máquina, esa carpeta es:
```
Z:\SteamLibrary\steamapps\common\Counter-Strike Global Offensive\game\csgo\replays\
```

Nota: solo funciona con partidas de matchmaking (Premier/Competitivo), no
casual/deathmatch, y solo tenés disponibles tus últimas 8 partidas de MM.

## 2. Copiá el archivo `.dem` a la carpeta que la app vigila

La carpeta que el backend mira es `cs2-tracker/backend/demos/` (relativa,
configurable con `CS2_DEMOS_DIR` en `.env`). Copiá ahí el archivo
`match730_..._....dem` (dejá el `.dem.info` de al lado, no hace falta copiarlo).

## 3. Corré la ingesta

Con el venv del backend activado:

```bash
cd cs2-tracker/backend
cs2-ingest --source folder --demos ./demos --once
```

Esto procesa todo lo que haya en la carpeta y termina (no se queda esperando).
Si preferís que quede vigilando la carpeta todo el tiempo y procese cada demo
nueva que aparezca sola, sacá el `--once`:

```bash
cs2-ingest --source folder --demos ./demos
```

(dejalo corriendo en su propia terminal, en paralelo al backend/frontend).

## 4. Listo

Refrescá el frontend (`http://localhost:5173`) — la partida nueva ya debería
aparecer, con su scoreboard, heatmap de kills y (si jugaste vos) tu sección
"Tu performance" con datos reales.

## Backfill de rank (partidas ingeridas antes de la feature de Rank Premier)

Las partidas ingeridas antes de que existiera la columna `rank` quedan con
rank NULL ("sin dato"). Para recuperar el CS Rating de esas partidas basta
re-ingerir sus demos con `--force` (purga y reinserta esa partida, mismos
datos + rank):

```bash
cd cs2-tracker/backend
cs2-ingest --source folder --demos ./demos --once --force
```

Y si tenés algún `.dem` suelto fuera de la carpeta:

```bash
cs2-ingest --demo "C:\ruta\al\match730_..._....dem" --force
```
