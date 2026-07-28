import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { register } from "../api";
import { Button } from "../components/Button";
import { Logo } from "../components/Logo";

interface Props {
  onRegistered: () => void;
}

// Paso 1 del alta: crear la cuenta con email+contraseña, antes de vincular
// Steam. El backend crea un AccountSignup (no un User todavía) y manda el
// mail de verificación -- ver api/account.py::auth_register.
export function RegisterView({ onRegistered }: Props) {
  const [email, setEmail] = useState("");
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
      await register(email.trim(), password);
      onRegistered();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo crear la cuenta.");
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
        <h2>Crear cuenta</h2>
        <p className="onb-sub">Con tu email y una contraseña. Después vinculás tu Steam.</p>
        <form onSubmit={handleSubmit}>
          <div className="onb-field">
            <label>Email</label>
            <input
              className="onb-select"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div className="onb-field">
            <label>Contraseña</label>
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
            <Button disabled={busy}>{busy ? "Creando…" : "Crear cuenta"}</Button>
          </div>
        </form>
        {error && <p className="af-error">{error}</p>}
        <p className="onb-sub">
          ¿Ya tenés cuenta? <Link to="/login">Iniciar sesión</Link>
        </p>
      </div>
    </div>
  );
}
