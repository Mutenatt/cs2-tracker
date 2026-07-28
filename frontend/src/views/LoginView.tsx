import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { login } from "../api";
import { Button } from "../components/Button";
import { Logo } from "../components/Logo";

interface Props {
  onLoggedIn: () => void;
}

// Sirve tanto para cuentas ya vinculadas a Steam como para retomar un
// registro a medio terminar (pending) -- ver api/account.py::auth_login.
export function LoginView({ onLoggedIn }: Props) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await login(email.trim(), password);
      onLoggedIn();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo iniciar sesión.");
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
        <h2>Iniciar sesión</h2>
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
              required
            />
          </div>
          <div className="onb-actions">
            <Button disabled={busy}>{busy ? "Entrando…" : "Iniciar sesión"}</Button>
          </div>
        </form>
        {error && <p className="af-error">{error}</p>}
        <p className="onb-sub">
          <Link to="/forgot-password">Olvidé mi contraseña</Link> ·{" "}
          <Link to="/register">Crear cuenta</Link>
        </p>
      </div>
    </div>
  );
}
