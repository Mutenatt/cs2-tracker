import { FormEvent, useEffect, useState } from "react";
import { getAutofetchStatus, linkAutofetch, unlinkAutofetch } from "../api";
import type { AutofetchStatus } from "../types";

const VALVE_CODES_URL =
  "https://help.steampowered.com/en/wizard/HelpWithGameIssue/?appid=730&issueid=128";

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return isNaN(d.getTime()) ? "—" : d.toLocaleString();
}

// Card de vinculación del auto-fetch (solo visible en el perfil propio):
// el usuario pega su Game Authentication Code + un sharecode y sus partidas
// de matchmaking se ingieren solas. Nunca se piden credenciales de Steam.
export function AutoFetchSettings() {
  const [status, setStatus] = useState<AutofetchStatus | null>(null);
  const [authCode, setAuthCode] = useState("");
  const [sharecode, setSharecode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        setStatus(await getAutofetchStatus());
      } catch {
        setStatus(null);
      }
    })();
  }, []);

  const handleLink = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setStatus(await linkAutofetch(authCode.trim(), sharecode.trim()));
      setAuthCode("");
      setSharecode("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo vincular.");
    } finally {
      setBusy(false);
    }
  };

  const handleUnlink = async () => {
    setBusy(true);
    setError(null);
    try {
      setStatus(await unlinkAutofetch());
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo desvincular.");
    } finally {
      setBusy(false);
    }
  };

  const active = status?.linked && status.status === "active";
  const broken = status?.linked && status.status !== "active";

  return (
    <>
      <div className="section-head">
        <span className="display">Auto-fetch de partidas</span>
        <span className="rule" />
      </div>
      <div className="legend-card af-card">
        {status === null ? (
          <p className="muted">Cargando…</p>
        ) : active ? (
          <>
            <div className="af-row">
              <span className="af-chip on">ACTIVO</span>
              <span className="af-meta">
                Último chequeo: {fmtDate(status.last_polled_at)} · Última partida traída:{" "}
                {fmtDate(status.last_fetched_at)}
              </span>
            </div>
            <p className="section-note">
              Tus partidas de matchmaking se descargan e ingieren solas. Los replays de Valve
              expiran a los ~30 días: jugá y listo.
            </p>
            <button type="button" className="af-btn ghost" onClick={handleUnlink} disabled={busy}>
              Desvincular
            </button>
          </>
        ) : (
          <>
            {broken && (
              <div className="af-row">
                <span className="af-chip off">
                  {status?.status === "revoked" ? "CÓDIGO REVOCADO" : "ERROR"}
                </span>
                <span className="af-meta">
                  {status?.error ?? "Volvé a vincular tus códigos para retomar."}
                </span>
              </div>
            )}
            {!broken && (
              <ol className="af-steps">
                <li>
                  Abrí la{" "}
                  <a href={VALVE_CODES_URL} target="_blank" rel="noreferrer">
                    página oficial de Valve
                  </a>{" "}
                  (inicia sesión en Steam, no acá).
                </li>
                <li>
                  Creá tu <b>Game Authentication Code</b> y copiá también un <b>match sharecode</b>{" "}
                  (elegí el más viejo para importar historial: hasta 8 partidas hacia atrás).
                </li>
                <li>Pegá los dos acá. Nunca te pedimos tu contraseña de Steam.</li>
              </ol>
            )}
            <form className="af-form" onSubmit={handleLink}>
              <input
                className="af-input mono"
                placeholder="AAAA-AAAAA-AAAA"
                value={authCode}
                onChange={(e) => setAuthCode(e.target.value)}
                aria-label="Game Authentication Code"
                required
              />
              <input
                className="af-input mono"
                placeholder="CSGO-XXXXX-XXXXX-XXXXX-XXXXX-XXXXX (o el link steam:// entero)"
                value={sharecode}
                onChange={(e) => setSharecode(e.target.value)}
                aria-label="Match sharecode"
                required
              />
              <button type="submit" className="af-btn" disabled={busy}>
                {busy ? "Vinculando…" : broken ? "Volver a vincular" : "Activar auto-fetch"}
              </button>
            </form>
            {error && <p className="af-error">{error}</p>}
          </>
        )}
      </div>
    </>
  );
}
