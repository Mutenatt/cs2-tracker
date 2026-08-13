// Overlay de lineups: ventana transparente, sin bordes, siempre-arriba, que
// se superpone al juego. Dos atajos globales (funcionan aunque CS2 tenga el
// foco, a diferencia de un atajo normal de la ventana), configurables desde
// Avanzado (ver store.js hideShortcut/clickThroughShortcut):
//   default Ctrl+Alt+L -> mostrar/ocultar
//   default Ctrl+Alt+K -> click-through (la ventana deja de capturar el
//                         mouse, así se puede seguir apuntando/disparando
//                         con el overlay visible encima)
const { app, BrowserWindow, globalShortcut, ipcMain, screen } = require("electron");
const path = require("node:path");
const store = require("./store");

// Los clips de lineup son cortos y livianos -- no vale la pena pelearle el
// motor de decode por hardware a CS2, que lo usa en simultáneo para
// renderizar (ahí es donde medimos el bajón de FPS). Decode por software
// mueve ese costo a CPU, que en partida suele tener más margen que la GPU.
app.commandLine.appendSwitch("disable-accelerated-video-decode");

let mainWindow = null;
let clickThrough = false;

function createWindow() {
  const { width: screenW } = screen.getPrimaryDisplay().workAreaSize;
  const width = 380;
  const height = 640;

  mainWindow = new BrowserWindow({
    width,
    height,
    x: screenW - width - 24,
    y: 24,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: true,
    skipTaskbar: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // "screen-saver" queda por encima de la mayoría de los juegos en
  // ventana/borderless -- el nivel "normal" de alwaysOnTop no siempre gana
  // contra CS2 en modo fullscreen-borderless.
  mainWindow.setAlwaysOnTop(true, "screen-saver");
  mainWindow.loadFile(path.join(__dirname, "renderer", "index.html"));

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

function toggleVisibility() {
  if (!mainWindow) return;
  if (mainWindow.isVisible()) {
    mainWindow.hide();
  } else {
    mainWindow.show();
  }
}

function toggleClickThrough() {
  if (!mainWindow) return;
  clickThrough = !clickThrough;
  // forward: true deja pasar los eventos de mouse al juego pero sigue
  // mandando mousemove al renderer, así la UI puede seguir reaccionando a
  // hover si hace falta en el futuro.
  mainWindow.setIgnoreMouseEvents(clickThrough, { forward: true });
  mainWindow.webContents.send("clickthrough:changed", clickThrough);
}

// action -> { accelerator, handler }, así registerShortcut/setShortcut no
// duplican la lista de qué atajo hace qué.
const SHORTCUT_ACTIONS = {
  hide: { settingsKey: "hideShortcut", handler: toggleVisibility },
  clickThrough: { settingsKey: "clickThroughShortcut", handler: toggleClickThrough },
};

function registerShortcut(action) {
  const { settingsKey, handler } = SHORTCUT_ACTIONS[action];
  const accelerator = store.load()[settingsKey];
  globalShortcut.register(accelerator, handler);
}

app.whenReady().then(() => {
  createWindow();

  for (const action of Object.keys(SHORTCUT_ACTIONS)) registerShortcut(action);

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("will-quit", () => {
  globalShortcut.unregisterAll();
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

ipcMain.handle("settings:get", () => store.load());
ipcMain.handle("settings:set", (_event, patch) => store.save(patch));

// El GET a la API corre en el proceso principal, no en el renderer: un
// fetch() del renderer (aunque sea file://) queda sujeto a la política CORS
// de Chromium, y el backend solo whitelistea el origin de la web (ver
// CORSMiddleware en api/main.py) -- no tiene sentido debilitar esa política
// para el sitio real solo para que el overlay pueda pegarle. El proceso
// principal es Node puro, no un contexto de browser, así que no aplica.
ipcMain.handle("api:get", async (_event, path) => {
  const { apiBaseUrl, apiToken } = store.load();
  if (!apiToken) return { status: 401, body: null };
  try {
    const res = await fetch(`${apiBaseUrl}${path}`, {
      headers: { Authorization: `Bearer ${apiToken}` },
    });
    const body = await res.json().catch(() => null);
    return { status: res.status, body };
  } catch (err) {
    return { status: 0, body: null, error: String(err) };
  }
});
// Login del overlay: mismo email+password de la cuenta monkeyStats (ver
// POST /auth/desktop-login en el backend) -- devuelve un token de API que
// se guarda solo, así el usuario nunca tiene que copiar/pegar nada. Corre
// en el proceso principal por el mismo motivo que api:get (CORS).
ipcMain.handle("auth:login", async (_event, { email, password, totpCode }) => {
  const { apiBaseUrl } = store.load();
  try {
    const res = await fetch(`${apiBaseUrl}/auth/desktop-login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, totp_code: totpCode || null }),
    });
    const body = await res.json().catch(() => null);
    if (res.ok && body?.token) {
      store.save({ apiToken: body.token, accountEmail: email });
    }
    return { status: res.status, body };
  } catch (err) {
    return { status: 0, body: null, error: String(err) };
  }
});
ipcMain.handle("clickthrough:toggle", () => {
  toggleClickThrough();
  return clickThrough;
});
ipcMain.handle("overlay:hide", () => {
  mainWindow?.hide();
});
// Minimize real a la barra de tareas -- distinto de "hide" (Ctrl+Alt+L), que
// saca la ventana del todo y solo se recupera con el atajo global.
ipcMain.handle("overlay:minimize", () => {
  mainWindow?.minimize();
});

// Rebindeo de atajos globales desde el panel de Avanzado. Valida que el
// accelerator nuevo no choque con el otro atajo propio y que Electron/el SO
// lo hayan podido registrar (puede estar tomado por otro programa) antes de
// persistirlo -- si falla, deja el anterior funcionando.
ipcMain.handle("shortcuts:set", (_event, { action, accelerator }) => {
  const entry = SHORTCUT_ACTIONS[action];
  if (!entry) return { ok: false, error: "acción desconocida" };

  const current = store.load();
  const otherAction = Object.keys(SHORTCUT_ACTIONS).find((a) => a !== action);
  if (current[SHORTCUT_ACTIONS[otherAction].settingsKey] === accelerator) {
    return { ok: false, error: "ya está usado por el otro atajo" };
  }

  const previous = current[entry.settingsKey];
  globalShortcut.unregister(previous);
  globalShortcut.register(accelerator, entry.handler);
  if (!globalShortcut.isRegistered(accelerator)) {
    // Tomado por otro programa (o el SO lo reserva) -- revertimos.
    globalShortcut.register(previous, entry.handler);
    return { ok: false, error: "esa combinación ya la usa otro programa" };
  }

  store.save({ [entry.settingsKey]: accelerator });
  return { ok: true };
});
