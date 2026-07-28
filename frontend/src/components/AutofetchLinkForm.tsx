import { FormEvent, useState } from "react";
import { linkAutofetch } from "../api";
import type { AutofetchStatus } from "../types";

const VALVE_CODES_URL =
  "https://help.steampowered.com/en/wizard/HelpWithGameIssue/?appid=730&issueid=128";

interface Props {
  // Status actual, si ya existe (perfil: puede venir "revoked"/"error").
  // En el onboarding no hay status previo, se deja sin pasar.
  status?: AutofetchStatus | null;
  onLinked: (status: AutofetchStatus) => void;
}

// Form de vinculación del auto-fetch: Game Authentication Code + sharecode
// (ambos generados por el usuario en la página oficial de Valve, nunca se
// piden credenciales de Steam). Reusado por AutoFetchSettings (perfil, para
// gestionar/revincular) y por OnboardingView (alta inicial, obligatoria).
export function AutofetchLinkForm({ status = null, onLinked }: Props) {
  const [authCode, setAuthCode] = useState("");
  const [sharecode, setSharecode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const broken = !!(status?.linked && status.status !== "active");

  const handleLink = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const next = await linkAutofetch(authCode.trim(), sharecode.trim());
      setAuthCode("");
      setSharecode("");
      onLinked(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo vincular.");
    } finally {
      setBusy(false);
    }
  };

  return (
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
            Creá tu <b>Game Authentication Code</b> y copiá también un <b>match sharecode</b> (elegí
            el más viejo para importar historial: hasta 8 partidas hacia atrás).
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
  );
}
