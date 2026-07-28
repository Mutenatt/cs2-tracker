import { FormEvent, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { resetPassword } from "../api";
import { Button } from "../components/Button";
import { Logo } from "../components/Logo";

export function ResetPasswordView() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (password !== confirm) {
      setError("Las contraseñas no coinciden.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await resetPassword(token, password);
      navigate("/login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo restablecer la contraseña.");
    } finally {
      setBusy(false);
    }
  };

  if (!token) {
    return (
      <div className="onb-shell">
        <div className="onb-card">
          <p className="af-error">
            Falta el token del link. Pedí uno nuevo desde "Olvidé mi contraseña".
          </p>
          <Link to="/forgot-password">Ir ahí</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="onb-shell">
      <div className="onb-topbar">
        <Logo size={20} />
      </div>
      <div className="onb-card">
        <h2>Elegí una nueva contraseña</h2>
        <form onSubmit={handleSubmit}>
          <div className="onb-field">
            <label>Nueva contraseña</label>
            <input
              className="onb-select"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={8}
              required
            />
          </div>
          <div className="onb-field">
            <label>Confirmar contraseña</label>
            <input
              className="onb-select"
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              minLength={8}
              required
            />
          </div>
          <div className="onb-actions">
            <Button disabled={busy}>{busy ? "Guardando…" : "Guardar"}</Button>
          </div>
        </form>
        {error && <p className="af-error">{error}</p>}
      </div>
    </div>
  );
}
