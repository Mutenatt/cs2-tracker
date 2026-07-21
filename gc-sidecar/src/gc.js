// Sesión única contra el Game Coordinator de CS2.
//
// Una sola cuenta bot del servicio resuelve sharecodes de CUALQUIER usuario:
// el sharecode en sí es la autorización (solo lo tiene quien jugó la partida
// o quien recibió el código). La bot inicia sesión en Steam, declara estar
// "jugando" CS2 (app 730) y con eso el GC le responde requestGame.

import fs from "node:fs";
import path from "node:path";
import readline from "node:readline";

import { decodeMatchShareCode } from "csgo-sharecode";
import GlobalOffensive from "globaloffensive";
import SteamUser from "steam-user";

const REQUEST_TIMEOUT_MS = 30_000;
const REQUEST_SPACING_MS = 1_000;
const RECONNECT_DELAY_MS = 30_000;

export class DemoExpiredError extends Error {}
export class GcNotReadyError extends Error {}

export class GcSession {
  constructor({ accountName, password, dataDir = "data" }) {
    this.accountName = accountName;
    this.password = password;
    this.dataDir = dataDir;
    this.tokenPath = path.join(dataDir, "refresh_token.txt");
    this.user = new SteamUser();
    this.csgo = new GlobalOffensive(this.user);
    // El GC atiende de a un requestGame por vez: cola serializada.
    this.queue = Promise.resolve();
    this.lastRequestAt = 0;
    this._wire();
  }

  get ready() {
    return this.user.steamID !== null && this.csgo.haveGCSession;
  }

  _wire() {
    this.user.on("loggedOn", () => {
      // Una cuenta nueva no "posee" CS2 (aunque sea F2P) hasta reclamar la
      // licencia; sin ella el Game Coordinator nunca contesta el hello.
      console.log("[steam] sesión iniciada; reclamando licencia F2P de CS2…");
      this.user.requestFreeLicense([730], (err, grantedPackages, grantedApps) => {
        if (err) {
          console.warn("[steam] requestFreeLicense falló:", err.message);
        } else {
          console.log(
            `[steam] licencia OK (apps: ${grantedApps?.length ? grantedApps.join(",") : "ya la tenía"})`
          );
        }
        console.log("[steam] lanzando CS2 headless…");
        this.user.gamesPlayed([730]);
      });
    });
    // Persistir el refresh token: los siguientes arranques no piden Steam Guard.
    this.user.on("refreshToken", (token) => {
      fs.mkdirSync(this.dataDir, { recursive: true });
      fs.writeFileSync(this.tokenPath, token, "utf8");
      console.log("[steam] refresh token guardado");
    });
    // Primer login: el código de Steam Guard se pide por consola.
    this.user.on("steamGuard", (domain, callback, lastCodeWrong) => {
      if (lastCodeWrong) {
        console.warn("[steam] el código anterior fue RECHAZADO; pedí/esperá uno nuevo");
      }
      const kind = domain ? `email (${domain})` : "app móvil";
      const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
      rl.question(`Código Steam Guard [${kind}]: `, (code) => {
        rl.close();
        console.log("[steam] código enviado; esperando respuesta de Steam…");
        callback(code.trim());
      });
    });
    this.user.on("error", (err) => {
      console.error("[steam] error:", err.message);
      setTimeout(() => this.logOn(), RECONNECT_DELAY_MS);
    });
    this.user.on("disconnected", (_eresult, msg) => {
      console.warn("[steam] desconectado:", msg ?? "");
    });
    this.csgo.on("connectedToGC", () => console.log("[gc] conectado al Game Coordinator"));
    this.csgo.on("disconnectedFromGC", (reason) => console.warn("[gc] desconectado:", reason));
    // Trazas internas de steam-user para diagnosticar logins que se quedan
    // mudos: GC_SIDECAR_DEBUG=1 npm start
    if (process.env.GC_SIDECAR_DEBUG) {
      this.user.on("debug", (msg) => console.log("[debug]", msg));
    }
  }

  logOn() {
    if (fs.existsSync(this.tokenPath)) {
      this.user.logOn({ refreshToken: fs.readFileSync(this.tokenPath, "utf8").trim() });
    } else {
      this.user.logOn({ accountName: this.accountName, password: this.password });
    }
  }

  resolve(shareCode) {
    const run = this.queue.then(() => this._resolveNow(shareCode));
    this.queue = run.catch(() => {});
    return run;
  }

  async _resolveNow(shareCode) {
    if (!this.ready) throw new GcNotReadyError("sin sesión con el Game Coordinator");
    const decoded = decodeMatchShareCode(shareCode);

    // ≥1s entre requests: el GC banea el spam, y no hay apuro.
    const wait = this.lastRequestAt + REQUEST_SPACING_MS - Date.now();
    if (wait > 0) await new Promise((r) => setTimeout(r, wait));
    this.lastRequestAt = Date.now();

    const match = await new Promise((resolveMatch, rejectMatch) => {
      const timer = setTimeout(() => {
        this.csgo.removeListener("matchList", onList);
        rejectMatch(new Error("timeout esperando matchList del GC"));
      }, REQUEST_TIMEOUT_MS);
      const onList = (matches) => {
        // matchList puede ser de otro request en vuelo: filtrar por matchid.
        const m = (matches ?? []).find((x) => String(x.matchid) === String(decoded.matchId));
        if (!m) return;
        clearTimeout(timer);
        this.csgo.removeListener("matchList", onList);
        resolveMatch(m);
      };
      this.csgo.on("matchList", onList);
      this.csgo.requestGame(shareCode);
    });

    // La URL del replay viene en el último roundstats que la tenga; si el GC
    // no la manda, el demo ya expiró (~30 días).
    const stats = match.roundstatsall ?? [];
    const withUrl = [...stats]
      .reverse()
      .find((r) => typeof r.map === "string" && r.map.startsWith("http"));
    if (!withUrl) {
      throw new DemoExpiredError("el GC no devolvió URL de replay (demo expirado)");
    }
    return {
      demoUrl: withUrl.map,
      matchId: String(decoded.matchId),
      reservationId: String(decoded.reservationId),
      tvPort: decoded.tvPort,
      matchTime: match.matchtime ?? null,
    };
  }
}
