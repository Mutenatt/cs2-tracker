import { useEffect, useState } from "react";
import { getAutofetchStatus, unlinkAutofetch } from "../api";
import type { AutofetchStatus } from "../types";
import { AutofetchLinkForm } from "./AutofetchLinkForm";

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return isNaN(d.getTime()) ? "—" : d.toLocaleString();
}

// Card de vinculación del auto-fetch (solo visible en el perfil propio):
// gestiona/revincula un auto-fetch que ya se dio de alta en el onboarding
// (ver views/OnboardingView.tsx, que usa el mismo AutofetchLinkForm).
export function AutoFetchSettings() {
  const [status, setStatus] = useState<AutofetchStatus | null>(null);
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
            {error && <p className="af-error">{error}</p>}
          </>
        ) : (
          <AutofetchLinkForm status={status} onLinked={setStatus} />
        )}
      </div>
    </>
  );
}
