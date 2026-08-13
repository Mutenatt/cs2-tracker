import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { forgotPassword } from "../api";
import { Button } from "../components/Button";
import { Logo } from "../components/Logo";

// Respuesta siempre genérica (ver api/account.py::auth_forgot_password):
// nunca revela si el email existe, para no dar pie a enumeración.
export function ForgotPasswordView() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      await forgotPassword(email.trim());
    } finally {
      setBusy(false);
      setSent(true);
    }
  };

  return (
    <div className="onb-shell">
      <div className="onb-topbar">
        <Logo size={20} />
      </div>
      <div className="onb-card">
        <h2>Restablecer contraseña</h2>
        {sent ? (
          <p className="onb-sub">
            Si ese email existe en monkeyStats, te mandamos un link para elegir una nueva
            contraseña.
          </p>
        ) : (
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
            <div className="onb-actions">
              <Button disabled={busy}>{busy ? "Enviando…" : "Enviar link"}</Button>
            </div>
          </form>
        )}
        <p className="onb-sub">
          <Link to="/login">Volver a iniciar sesión</Link>
        </p>
      </div>
    </div>
  );
}
