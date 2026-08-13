// Vanilla JS a propósito: es una ventana chica de settings + lista, no
// justifica un bundler/framework propio separado del frontend principal.

const CATEGORY_LABEL = { smoke: "Humo", flash: "Flash", molotov: "Molotov", he: "HE" };
// SVG en vez de emoji: los emoji dependen de la fuente del SO y no se pueden
// themear -- ver regla "no-emoji-icons" del skill de UI/UX.
const CATEGORY_ICON = {
  smoke: `<svg viewBox="0 0 20 20" fill="currentColor"><circle cx="7" cy="11" r="3.2"/><circle cx="11.5" cy="9.5" r="3.8"/><circle cx="14.5" cy="12" r="2.6"/><rect x="5" y="11" width="11" height="3.5" rx="1.75"/></svg>`,
  flash: `<svg viewBox="0 0 20 20" fill="currentColor"><polygon points="12,1 5,11 10,11 8,19 15,9 10,9"/></svg>`,
  molotov: `<svg viewBox="0 0 20 20" fill="currentColor"><path d="M10 2C7 6 5 9 5 12a5 5 0 0 0 10 0c0-2-1-3-2-4 .3 2-1 3-2 3-1.2 0-2-1-2-2.2C9 7.2 10 5 10 2Z"/></svg>`,
  he: `<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="10" cy="10" r="7"/><circle cx="10" cy="10" r="3.2" fill="currentColor" stroke="none"/></svg>`,
};
const CATEGORY_COLOR = {
  smoke: "var(--text-dim)",
  flash: "var(--gold)",
  molotov: "var(--signal)",
  he: "var(--alert)",
};
const WARNING_ICON = `<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><path d="M10 2 1 17h18L10 2Z"/><line x1="10" y1="8" x2="10" y2="12"/><circle cx="10" cy="14.5" r="0.9" fill="currentColor" stroke="none"/></svg>`;
const EMPTY_ICON = `<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.4"><rect x="3" y="4" width="14" height="12" rx="2"/><path d="M3 13l3.5-3.5a1.5 1.5 0 0 1 2.1 0L12 13" stroke-linecap="round" stroke-linejoin="round"/><circle cx="13" cy="7.5" r="1.3"/></svg>`;

const SHORTCUT_SETTINGS_KEY = { hide: "hideShortcut", clickThrough: "clickThroughShortcut" };
const SPECIAL_KEY_NAMES = {
  " ": "Space",
  Escape: "Escape",
  Tab: "Tab",
  Enter: "Enter",
  Backspace: "Backspace",
  Delete: "Delete",
  ArrowUp: "Up",
  ArrowDown: "Down",
  ArrowLeft: "Left",
  ArrowRight: "Right",
  Home: "Home",
  End: "End",
  PageUp: "PageUp",
  PageDown: "PageDown",
  Insert: "Insert",
};

// Traduce un KeyboardEvent a un Accelerator de Electron (p.ej. "Control+Alt+L").
// Devuelve null mientras la combinación todavía no es válida -- exigimos al
// menos un modificador para no pisar una tecla normal del teclado.
function acceleratorFromEvent(e) {
  if (["Control", "Alt", "Shift", "Meta"].includes(e.key)) return null;

  const mods = [];
  if (e.ctrlKey) mods.push("Control");
  if (e.altKey) mods.push("Alt");
  if (e.shiftKey) mods.push("Shift");
  if (e.metaKey) mods.push("Super");
  if (mods.length === 0) return null;

  let key;
  if (SPECIAL_KEY_NAMES[e.key]) {
    key = SPECIAL_KEY_NAMES[e.key];
  } else if (/^F([1-9]|1[0-9]|2[0-4])$/.test(e.key)) {
    key = e.key;
  } else if (e.key.length === 1) {
    key = e.key.toUpperCase();
  } else {
    return null; // tecla que no sabemos mapear a un nombre de Accelerator
  }
  return [...mods, key].join("+");
}

// El proceso principal nunca manda el apiToken en claro por IPC (ver
// sanitizeSettings en main.js) -- acá solo llega hasToken, un booleano.
let settings = { apiBaseUrl: "", hasToken: false };
let state = { map: null, team: "T", category: "smoke" };

const $ = (sel) => document.querySelector(sel);

function setStatus(kind) {
  // kind: "idle" | "online" | "error" -- refleja si la última llamada a la
  // API salió bien, para que el usuario vea de un vistazo si el overlay
  // sigue conectado sin tener que abrir el panel de settings.
  const dot = $("#status-dot");
  dot.classList.toggle("online", kind === "online");
  dot.classList.toggle("error", kind === "error");
}

function showError(message) {
  const el = $("#error-banner");
  if (!message) {
    el.classList.add("hidden");
    el.innerHTML = "";
    return;
  }
  el.innerHTML = `${WARNING_ICON}<span>${message}</span>`;
  el.classList.remove("hidden");
  setStatus("error");
}

async function apiFetch(path) {
  if (!settings.hasToken) {
    throw new Error("Iniciá sesión (⚙ Configuración)");
  }
  // El fetch real corre en el proceso principal (ver main.js) para no
  // pisar la política CORS del backend -- acá solo se interpreta el
  // resultado.
  const { status, body, error } = await window.overlay.apiGet(path);
  if (status === 0) {
    throw new Error(error || `No se pudo conectar a ${settings.apiBaseUrl}`);
  }
  if (status === 401) {
    // El token que teníamos guardado ya no sirve (revocado desde la web,
    // o nunca llegó a existir) -- hay que volver a loguearse, no solo
    // mostrar el error.
    settings = await window.overlay.setSettings({ apiToken: "", accountEmail: "" });
    showLoggedOutUI();
    $("#settings-panel").classList.remove("hidden");
    throw new Error("Tu sesión venció -- iniciá sesión de nuevo");
  }
  if (status < 200 || status >= 300) {
    throw new Error(`${path} -> ${status}`);
  }
  return body;
}

async function loadMaps() {
  const { maps } = await apiFetch("/lineups/maps");
  const select = $("#map-select");
  select.innerHTML = "";
  for (const m of maps) {
    const opt = document.createElement("option");
    opt.value = m.map;
    opt.textContent = `${m.map.replace("de_", "")} (${m.count})`;
    select.appendChild(opt);
  }
  if (maps.length > 0) {
    state.map = maps.find((m) => m.map === "de_mirage")?.map ?? maps[0].map;
    select.value = state.map;
  }
}

function renderLineups(items) {
  const list = $("#lineup-list");
  list.innerHTML = "";
  if (items.length === 0) {
    list.innerHTML = `<div class="empty">${EMPTY_ICON}<p>Sin lineups para este filtro.</p></div>`;
    return;
  }
  for (const item of items) {
    const card = document.createElement("article");
    card.className = "lineup-card";
    card.style.setProperty("--cat-color", CATEGORY_COLOR[item.category] ?? "var(--text-faint)");

    const head = document.createElement("button");
    head.className = "lineup-head";
    head.type = "button";
    head.setAttribute("aria-expanded", "false");
    head.innerHTML = `<span class="cat-badge">${CATEGORY_ICON[item.category] ?? ""}</span>
      <span class="lineup-label">${item.label}</span>
      <span class="lineup-cat">${CATEGORY_LABEL[item.category] ?? item.category}</span>
      <svg class="lineup-chevron" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="5 7.5 10 12.5 15 7.5"/></svg>`;

    const collapse = document.createElement("div");
    collapse.className = "lineup-collapse";
    const body = document.createElement("div");
    body.className = "lineup-body";
    const notes = [item.instructions, item.crosshair_note].filter(Boolean).join(" — ");
    body.innerHTML = `
      ${notes ? `<p class="lineup-notes">${notes}</p>` : ""}
      <div class="video-wrap">
        <video controls loop muted playsinline preload="none"
          src="${item.video_url}"></video>
      </div>
    `;
    collapse.appendChild(body);
    const video = body.querySelector("video");

    head.addEventListener("click", () => {
      const isOpen = collapse.classList.contains("open");
      // Un solo clip reproduciendo a la vez -- pausa/cierra cualquier otro abierto.
      document.querySelectorAll(".lineup-body video").forEach((v) => v.pause());
      document.querySelectorAll(".lineup-collapse.open").forEach((c) => c.classList.remove("open"));
      document.querySelectorAll('.lineup-head[aria-expanded="true"]').forEach((h) => h.setAttribute("aria-expanded", "false"));
      if (!isOpen) {
        collapse.classList.add("open");
        head.setAttribute("aria-expanded", "true");
        // Autoplay al abrir -- el video está muted, así que Chromium lo deja
        // arrancar sin gesto extra del usuario. Si igual lo bloquea (o el
        // clip no cargó todavía), no rompe nada: quedan los controles nativos.
        video.play().catch(() => {});
        // Espera a que termine de expandirse (o el reduced-motion "instantáneo")
        // antes de hacer scroll -- si no, calcula la posición con la altura
        // vieja y el video queda tapado en ventanas chicas con varios lineups.
        collapse.addEventListener(
          "transitionend",
          () => card.scrollIntoView({ behavior: "smooth", block: "start" }),
          { once: true },
        );
      }
    });

    card.append(head, collapse);
    list.appendChild(card);
  }
}

async function refresh() {
  if (!state.map) return;
  $("#lineup-list").innerHTML = `<div class="loading-row"><span class="spinner"></span>Cargando lineups…</div>`;
  try {
    const qs = new URLSearchParams({ map: state.map, team: state.team });
    if (state.category) qs.set("category", state.category);
    const items = await apiFetch(`/lineups?${qs}`);
    showError(null);
    setStatus("online");
    renderLineups(items);
  } catch (err) {
    showError(err.message);
    $("#lineup-list").innerHTML = "";
  }
}

function showLoggedInUI() {
  $("#account-view").classList.remove("hidden");
  $("#login-view").classList.add("hidden");
  $("#account-email").textContent = settings.accountEmail || "";
}

function showLoggedOutUI() {
  $("#account-view").classList.add("hidden");
  $("#login-view").classList.remove("hidden");
  $("#totp-field").classList.add("hidden");
  $("#loginPassword").value = "";
  $("#loginTotp").value = "";
  setStatus("idle");
}

function setLoginStatus(message, isError) {
  const el = $("#login-status");
  el.textContent = message;
  el.classList.toggle("error", Boolean(isError));
}

function updateShortcutDisplays() {
  $("#shortcut-hide-display").textContent = settings.hideShortcut;
  $("#shortcut-clickThrough-display").textContent = settings.clickThroughShortcut;
  $("#hide-btn").title = `Ocultar (${settings.hideShortcut})`;
  $("#clickthrough-btn").title = `Click-through (${settings.clickThroughShortcut})`;
}

function startShortcutRecording(action) {
  const btn = $(`.shortcut-edit-btn[data-action="${action}"]`);
  const statusEl = $("#shortcut-status");
  btn.classList.add("recording");
  btn.textContent = "Presioná una tecla…";
  statusEl.textContent = "";
  statusEl.classList.remove("error");

  const cleanup = () => {
    document.removeEventListener("keydown", onKeydown, true);
    btn.classList.remove("recording");
    btn.textContent = "Cambiar";
  };

  const onKeydown = async (e) => {
    e.preventDefault();
    if (e.key === "Escape") {
      cleanup();
      return;
    }
    const accelerator = acceleratorFromEvent(e);
    if (!accelerator) return; // todavía no soltó una combinación válida

    cleanup();
    const result = await window.overlay.setShortcut(action, accelerator);
    if (result.ok) {
      settings[SHORTCUT_SETTINGS_KEY[action]] = accelerator;
      updateShortcutDisplays();
      statusEl.textContent = "Guardado";
      setTimeout(() => (statusEl.textContent = ""), 2000);
    } else {
      statusEl.textContent = result.error;
      statusEl.classList.add("error");
    }
  };

  document.addEventListener("keydown", onKeydown, true);
}

async function init() {
  settings = await window.overlay.getSettings();
  updateShortcutDisplays();

  if (settings.hasToken) {
    showLoggedInUI();
  } else {
    showLoggedOutUI();
    $("#settings-panel").classList.remove("hidden");
  }

  try {
    await loadMaps();
    await refresh();
  } catch (err) {
    showError(err.message);
  }

  $("#settings-btn").addEventListener("click", () => {
    $("#settings-panel").classList.toggle("hidden");
  });

  $("#hide-btn").addEventListener("click", () => window.overlay.hide());
  $("#minimize-btn").addEventListener("click", () => window.overlay.minimize());

  $("#clickthrough-btn").addEventListener("click", () => window.overlay.toggleClickThrough());
  window.overlay.onClickThroughChanged((active) => {
    $("#clickthrough-btn").classList.toggle("active", active);
  });

  $("#toggle-password-btn").addEventListener("click", () => {
    const input = $("#loginPassword");
    const shown = input.type === "text";
    input.type = shown ? "password" : "text";
    $("#toggle-password-btn").setAttribute("aria-pressed", String(!shown));
    $("#toggle-password-btn").setAttribute("aria-label", shown ? "Mostrar contraseña" : "Ocultar contraseña");
  });

  $("#login-view").addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = $("#loginEmail").value.trim();
    const password = $("#loginPassword").value;
    const totpCode = $("#loginTotp").value.trim();
    if (!email || !password) {
      setLoginStatus("Completá email y contraseña", true);
      return;
    }

    setLoginStatus("Conectando…", false);
    const { status, body, error } = await window.overlay.login({ email, password, totpCode });

    if (status === 0) {
      setLoginStatus(error || `No se pudo conectar a ${settings.apiBaseUrl}`, true);
      return;
    }
    if (status === 200 && body?.mfa_required) {
      $("#totp-field").classList.remove("hidden");
      setLoginStatus("Ingresá el código de tu app de autenticación", false);
      return;
    }
    if (status !== 200 || !body?.hasToken) {
      const message =
        body?.detail ||
        (status === 423 ? "cuenta bloqueada temporalmente, probá de nuevo en unos minutos" : null) ||
        (status === 401 ? "credenciales inválidas" : null) ||
        `error al iniciar sesión (${status})`;
      setLoginStatus(message, true);
      return;
    }

    settings = await window.overlay.getSettings();
    setLoginStatus("", false);
    showLoggedInUI();
    try {
      await loadMaps();
      await refresh();
      $("#settings-panel").classList.add("hidden");
    } catch (err) {
      showError(err.message);
    }
  });

  $("#logout-btn").addEventListener("click", async () => {
    settings = await window.overlay.setSettings({ apiToken: "", accountEmail: "" });
    showLoggedOutUI();
    $("#lineup-list").innerHTML = "";
    showError(null);
  });

  document.querySelectorAll(".shortcut-edit-btn").forEach((btn) => {
    btn.addEventListener("click", () => startShortcutRecording(btn.dataset.action));
  });

  $("#map-select").addEventListener("change", (e) => {
    state.map = e.target.value;
    refresh();
  });

  document.querySelectorAll(".team-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".team-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.team = btn.dataset.team;
      // El contorno de las categorías (Humo/Flash/...) sigue este color -- ver
      // #filters[data-team="CT"] en styles.css.
      $("#filters").dataset.team = state.team;
      refresh();
    });
  });

  document.querySelectorAll(".cat-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".cat-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.category = btn.dataset.category;
      refresh();
    });
  });
}

init();
