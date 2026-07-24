// Sidecar del Game Coordinator: sharecode -> URL del .dem.
//
// Escucha SOLO en 127.0.0.1 y no autentica: nunca exponerlo fuera de la
// máquina. El backend Python (infra/gc_client.py) es su único cliente.

import "dotenv/config";
import express from "express";

import {
  DemoExpiredError,
  GcNotReadyError,
  GcSession,
  ProfileUnavailableError,
} from "./gc.js";

const port = Number(process.env.GC_SIDECAR_PORT ?? 9001);
// 127.0.0.1 salvo en Docker (el Dockerfile setea 0.0.0.0; el mapeo de puerto
// del compose igual publica solo en 127.0.0.1 del host).
const host = process.env.GC_SIDECAR_HOST ?? "127.0.0.1";
const { STEAM_BOT_USERNAME, STEAM_BOT_PASSWORD } = process.env;

if (!STEAM_BOT_USERNAME || !STEAM_BOT_PASSWORD) {
  console.error("Faltan STEAM_BOT_USERNAME / STEAM_BOT_PASSWORD en el .env");
  process.exit(1);
}

const gc = new GcSession({
  accountName: STEAM_BOT_USERNAME,
  password: STEAM_BOT_PASSWORD,
  dataDir: process.env.GC_SIDECAR_DATA_DIR ?? "data",
});
gc.logOn();

const app = express();
app.use(express.json());

app.get("/health", (_req, res) => {
  const body = {
    steam: gc.user.steamID !== null,
    gc: gc.csgo.haveGCSession,
    // El usuario tiene que agregar este steamid de amigo para que /profile
    // devuelva su rating Premier (ver Capa 2).
    botSteamId: gc.user.steamID ? gc.user.steamID.getSteamID64() : null,
  };
  res.status(body.steam && body.gc ? 200 : 503).json(body);
});

app.post("/profile", async (req, res) => {
  const steamid = req.body?.steamid;
  if (typeof steamid !== "string" || !/^\d{17}$/.test(steamid)) {
    return res.status(400).json({ error: "BAD_STEAMID" });
  }
  try {
    res.json(await gc.profile(steamid));
  } catch (err) {
    if (err instanceof GcNotReadyError) return res.status(503).json({ error: "GC_NOT_READY" });
    // No amigo / offline / sin Premier: 404 (esperable, no es error del server).
    if (err instanceof ProfileUnavailableError)
      return res.status(404).json({ error: "PROFILE_UNAVAILABLE", detail: err.message });
    console.error("[profile] fallo:", err.message);
    res.status(502).json({ error: "GC_ERROR", detail: err.message });
  }
});

app.post("/resolve", async (req, res) => {
  const shareCode = req.body?.sharecode;
  if (typeof shareCode !== "string" || !/^CSGO(-[A-Za-z0-9]{5}){5}$/.test(shareCode)) {
    return res.status(400).json({ error: "BAD_SHARECODE" });
  }
  try {
    res.json(await gc.resolve(shareCode));
  } catch (err) {
    if (err instanceof DemoExpiredError) return res.status(404).json({ error: "DEMO_EXPIRED" });
    if (err instanceof GcNotReadyError) return res.status(503).json({ error: "GC_NOT_READY" });
    console.error("[resolve] fallo:", err.message);
    res.status(502).json({ error: "GC_ERROR", detail: err.message });
  }
});

app.listen(port, host, () => {
  console.log(`[sidecar] escuchando en http://${host}:${port}`);
});
