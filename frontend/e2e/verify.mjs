// Driver de verificación visual manual (no es parte de CI).
//
// Loguea con una cookie de sesión inyectada (evita el flow real de Steam),
// navega a cada ruta pedida, chequea errores de consola/página, y deja
// screenshots en frontend/e2e/shots/ para comparar a mano contra el mockup
// aprobado antes de dar una fase por terminada.
//
// Uso:
//   COOKIE=<valor de cs2_session> node e2e/verify.mjs [ruta1 ruta2 ...]
// El valor de COOKIE se genera con (desde backend/, venv activado):
//   python -c "from cs2tracker.auth import create_session_cookie as c; print(c('<steamid>'))"
// Requiere que el backend haya arrancado con el mismo CS2_SESSION_SECRET
// que usó ese script (ver backend/.env).
import { chromium } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SHOTS_DIR = path.join(__dirname, "shots");
mkdirSync(SHOTS_DIR, { recursive: true });

const BASE_URL = "http://localhost:5173";
const cookieValue = process.env.COOKIE;
const routes = process.argv.slice(2).length ? process.argv.slice(2) : ["/"];

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });

  if (cookieValue) {
    await context.addCookies([
      {
        name: "cs2_session",
        value: cookieValue,
        domain: "localhost",
        path: "/",
        httpOnly: true,
        sameSite: "Lax",
      },
    ]);
  }

  const page = await context.newPage();
  let hadErrors = false;
  page.on("console", (msg) => {
    if (msg.type() === "error") {
      hadErrors = true;
      console.error(`[console.error] ${msg.text()}`);
    }
  });
  page.on("pageerror", (err) => {
    hadErrors = true;
    console.error(`[pageerror] ${err.message}`);
  });

  for (const route of routes) {
    const name = route === "/" ? "root" : route.replace(/^\//, "").replace(/\//g, "-");
    await page.goto(`${BASE_URL}${route}`, { waitUntil: "networkidle" });
    await page.waitForTimeout(400); // deja terminar fetch/render async
    const shotPath = path.join(SHOTS_DIR, `${name}.png`);
    await page.screenshot({ path: shotPath, fullPage: true });
    console.log(`screenshot: ${shotPath}`);
  }

  await browser.close();
  if (hadErrors) {
    console.error("HUBO ERRORES DE CONSOLA/PÁGINA -- ver arriba.");
    process.exit(1);
  }
  console.log("OK: sin errores de consola/página.");
}

main();
