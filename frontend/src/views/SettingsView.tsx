import { useState } from "react";
import { forgotPassword } from "../api";
import { AutoFetchSettings } from "../components/AutoFetchSettings";
import { Button } from "../components/Button";
import { useUser } from "../context/UserContext";

export function SettingsView() {
  const user = useUser();
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  const handleChangePassword = async () => {
    if (!user.email) return;
    setBusy(true);
    try {
      await forgotPassword(user.email);
      setSent(true);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="section-head">
        <span className="display">Configuración</span>
        <span className="rule" />
      </div>

      <div className="section-head">
        <span className="display">Cuenta</span>
        <span className="rule" />
      </div>
      <div className="legend-card af-card">
        <div className="af-row">
          <span className="af-meta">{user.email}</span>
        </div>
        <Button onClick={handleChangePassword} disabled={busy}>
          {busy ? "Enviando…" : sent ? "Revisá tu email" : "Cambiar contraseña"}
        </Button>
      </div>

      <div className="section-head">
        <span className="display">Steam</span>
        <span className="rule" />
      </div>
      <div className="legend-card af-card">
        <div className="af-row">
          {user.avatar_url ? (
            <img className="av" src={user.avatar_url} alt="" width={32} height={32} />
          ) : (
            <span className="av" />
          )}
          <span className="af-meta">{user.display_name}</span>
        </div>
        <p className="af-meta mono">{user.steamid}</p>
      </div>

      <AutoFetchSettings />
    </>
  );
}
