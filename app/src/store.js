// Persistencia de settings sin dependencias externas (nada de electron-store):
// un JSON chico en userData alcanza -- apiBaseUrl y el token personal
// generado desde /settings en la web (ver backend/cs2tracker/api_tokens.py).
// El token vive en texto plano en disco local del usuario, mismo modelo de
// confianza que un archivo .netrc o una API key de CLI.
const fs = require("node:fs");
const path = require("node:path");
const { app } = require("electron");

const DEFAULTS = {
  apiBaseUrl: "http://localhost:8000",
  apiToken: "",
  // Solo para mostrar "conectado como ..." en el panel -- la identidad real
  // la da el token, esto es puramente cosmético.
  accountEmail: "",
  // Atajos globales (funcionan aunque CS2 tenga el foco) -- formato
  // Accelerator de Electron. Configurables desde Avanzado por si chocan con
  // otro programa o el bind del propio juego.
  hideShortcut: "Control+Alt+L",
  clickThroughShortcut: "Control+Alt+K",
};

function storePath() {
  return path.join(app.getPath("userData"), "settings.json");
}

function load() {
  try {
    const raw = fs.readFileSync(storePath(), "utf-8");
    return { ...DEFAULTS, ...JSON.parse(raw) };
  } catch {
    return { ...DEFAULTS };
  }
}

function save(settings) {
  const merged = { ...load(), ...settings };
  fs.mkdirSync(path.dirname(storePath()), { recursive: true });
  fs.writeFileSync(storePath(), JSON.stringify(merged, null, 2), "utf-8");
  return merged;
}

module.exports = { load, save };
