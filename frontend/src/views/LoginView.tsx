import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "motion/react";
import { Lock, Mail } from "lucide-react";
import { login } from "../api";
import { Logo } from "../components/Logo";

interface Props {
  onLoggedIn: () => void;
}

function SteamGlyph() {
  return (
    <svg className="hud-steam-btn-icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="10.5" stroke="currentColor" strokeWidth="1.4" />
      <circle cx="8.7" cy="14.6" r="2.1" stroke="currentColor" strokeWidth="1.4" />
      <path d="M8.7 14.6 12.5 11" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      <circle cx="14.3" cy="9" r="1.9" fill="currentColor" />
    </svg>
  );
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
    <motion.div
      className="onb-shell"
      initial={{ opacity: 0, y: 15, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
    >
      <div className="onb-topbar">
        <Logo size={20} />
      </div>
      <div className="hud-card-wrap">
        <div className="hud-glow" aria-hidden="true" />
        <div className="hud-card">
          <span className="hud-corner hud-corner-tl" aria-hidden="true" />
          <span className="hud-corner hud-corner-tr" aria-hidden="true" />
          <span className="hud-corner hud-corner-bl" aria-hidden="true" />
          <span className="hud-corner hud-corner-br" aria-hidden="true" />

          <div className="hud-status-bar">
            <span className="hud-led hud-led-cyan" />[ AUTH_GATEWAY // SECURE_LOGIN ]
          </div>

          <h2>Iniciar sesión</h2>

          {/* /auth/steam/link exige una sesión de signup pendiente con email
              verificado (ver api/account.py::auth_steam_link) -- no hay hoy un
              login directo por Steam para una cuenta ya creada, así que el
              botón queda deshabilitado en vez de romper el flujo real. */}
          <button type="button" className="hud-steam-btn" disabled title="Próximamente">
            <SteamGlyph />
            INICIAR SESIÓN CON STEAM
            <span className="hud-steam-btn-soon">PRÓXIMAMENTE</span>
          </button>

          <div className="hud-divider">
            <span className="hud-divider-label">O INGRESA CON EMAIL</span>
          </div>

          <form onSubmit={handleSubmit}>
            <div className="onb-field">
              <label>Email</label>
              <div className="hud-input-group">
                <Mail className="hud-input-icon" />
                <input
                  className="onb-select hud-field-input"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>
            </div>
            <div className="onb-field">
              <label>Contraseña</label>
              <div className="hud-input-group">
                <Lock className="hud-input-icon" />
                <input
                  className="onb-select hud-field-input"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>
            </div>
            <div className="onb-actions">
              <motion.button
                type="submit"
                className="hud-cta"
                disabled={busy}
                whileHover={busy ? undefined : { scale: 1.02 }}
                whileTap={busy ? undefined : { scale: 0.98 }}
              >
                {busy ? "ACCEDIENDO…" : "ACCEDER A LA PLATAFORMA"}
              </motion.button>
            </div>
          </form>
          {error && <p className="af-error">{error}</p>}
          <p className="onb-sub">
            <Link to="/forgot-password">Olvidé mi contraseña</Link> ·{" "}
            <span>¿No tenés cuenta? </span>
            <Link to="/register">Crear cuenta</Link>
          </p>
        </div>
      </div>
    </motion.div>
  );
}
