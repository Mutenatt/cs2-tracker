import { useEffect, useState } from "react";
import { resendVerification } from "../api";
import { Button } from "../components/Button";
import { Logo } from "../components/Logo";

interface Props {
  email: string | null;
  onVerified: () => void;
  onLogout: () => void;
}

// Sondeo del estado de verificación: no hay evento del backend hacia el
// frontend, solo polling contra getMe() hasta que email_verified_at se
// setee (el click en el link de mail pasa por otra pestaña/dispositivo).
const POLL_MS = 5000;

export function EmailVerificationPendingView({ email, onVerified, onLogout }: Props) {
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const id = setInterval(onVerified, POLL_MS);
    return () => clearInterval(id);
  }, [onVerified]);

  const handleResend = async () => {
    setBusy(true);
    setError(null);
    try {
      await resendVerification();
      setSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo reenviar.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="onb-shell">
      <div className="onb-topbar">
        <Logo size={20} />
      </div>
      <div className="onb-card">
        <h2>Verificá tu email</h2>
        <p className="onb-sub">
          Te mandamos un link a <b>{email}</b>. Abrilo para seguir con el registro — esta pantalla
          se actualiza sola apenas lo confirmes.
        </p>
        <div className="onb-actions">
          <Button onClick={handleResend} disabled={busy}>
            {busy ? "Enviando…" : sent ? "Reenviado" : "Reenviar email"}
          </Button>
        </div>
        {error && <p className="af-error">{error}</p>}
        <button type="button" className="af-btn ghost" onClick={onLogout}>
          Salir
        </button>
      </div>
    </div>
  );
}
