# monkeyStats — Overlay de lineups

App de escritorio (Electron) que muestra los lineups de granadas guardados
en monkeyStats mientras jugás, en una ventana transparente y siempre-arriba sobre
CS2. No tiene su propia base de datos ni copia de contenido: lee la misma
tabla `lineups` que ve la web, vía `GET /lineups` del backend.

## Por qué un proceso aparte y no una ventana del navegador

CS2 en modo fullscreen (no borderless) no deja ver otras ventanas por
encima. Un overlay de escritorio con `alwaysOnTop` en modo "screen-saver" sí
puede superponerse a un juego en fullscreen-borderless o ventana — el mismo
mecanismo que usan overlays tipo Discord/Steam.

## Setup

```bash
cd app
npm install
npm start
```

Al primer arranque se abre el panel de configuración (⚙) porque todavía no
hay token guardado. Necesitás:

1. **API base URL**: dónde corre el backend de monkeyStats (por defecto
   `http://localhost:8000` en dev).
2. **Asset base URL**: de dónde se sirven los `.mp4` de los lineups —hoy
   viven en `frontend/public/lineups/...`, así que en dev es el propio Vite
   (`http://localhost:5173`); en producción, el dominio del sitio.
3. **Token**: generalo desde la web en **Configuración → App de
   escritorio → Generar token**. Se muestra una única vez — copialo antes
   de cerrar ese panel. Podés revocarlo en cualquier momento desde ahí sin
   afectar tu sesión del navegador (son mecanismos independientes, ver
   `backend/cs2tracker/api_tokens.py`).

Los settings (incluido el token, en texto plano) quedan en
`app.getPath("userData")/settings.json` — local a tu máquina, mismo modelo
de confianza que una API key de cualquier CLI.

## Atajos globales

Funcionan aunque CS2 tenga el foco (a diferencia de un atajo normal de
ventana):

| Atajo          | Acción                                                    |
| -------------- | ---------------------------------------------------------- |
| `Ctrl+Alt+L`   | Mostrar / ocultar el overlay                               |
| `Ctrl+Alt+K`   | Click-through: la ventana deja de capturar el mouse (podés seguir apuntando/disparando con el overlay visible) |

## Empaquetado

Todavía no hay build de instalador (`electron-builder`/`electron-forge`) —
por ahora es `npm start` desde el checkout. Si hace falta distribuir un
`.exe`, es el siguiente paso natural sobre este mismo `main.js`.
