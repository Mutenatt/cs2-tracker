import { FormEvent, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { motion } from "motion/react";
import { Lock, Mail } from "lucide-react";
import { register } from "../api";
import { Logo } from "../components/Logo";

interface Props {
  onRegistered: () => void;
}

type StrengthTier = "idle" | "weak" | "secure" | "military";

// Heurística simple (no criptográfica): solo maneja el copy del medidor
// "NIVEL DE ENCRIPTACIÓN", no valida seguridad real de la contraseña.
function getPasswordStrength(password: string): { tier: StrengthTier; label: string; segments: number } {
  if (password.length === 0) return { tier: "idle", label: "", segments: 0 };
  const variety = [/[a-z]/, /[A-Z]/, /[0-9]/, /[^a-zA-Z0-9]/].filter((re) => re.test(password)).length;
  if (password.length >= 12 && variety >= 3) return { tier: "military", label: "MILITAR", segments: 3 };
  if (password.length >= 8 && variety >= 2) return { tier: "secure", label: "SEGURO", segments: 2 };
  return { tier: "weak", label: "DÉBIL", segments: 1 };
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

  const strength = useMemo(() => getPasswordStrength(password), [password]);

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
      <div className="hud-card-wrap">
        <div className="hud-glow" aria-hidden="true" />
        <div className="hud-card">
          <span className="hud-corner hud-corner-tl" aria-hidden="true" />
          <span className="hud-corner hud-corner-tr" aria-hidden="true" />
          <span className="hud-corner hud-corner-bl" aria-hidden="true" />
          <span className="hud-corner hud-corner-br" aria-hidden="true" />

          <div className="hud-status-bar">
            <span className="hud-led" />
            [ SYSTEM_STATUS // ENCRYPTED_CONNECTION ]
          </div>

          <h2>Crear cuenta</h2>
          <p className="onb-sub">Siguiente paso: vincular tu cuenta de Steam.</p>
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
                  minLength={8}
                  required
                />
              </div>
              {strength.tier !== "idle" && (
                <div className="hud-strength">
                  <div className="hud-strength-bar">
                    {[0, 1, 2].map((i) => (
                      <span
                        key={i}
                        className={`hud-strength-seg${i < strength.segments ? ` filled tier-${strength.tier}` : ""}`}
                      />
                    ))}
                  </div>
                  <span className={`hud-strength-label tier-${strength.tier}`}>
                    NIVEL DE ENCRIPTACIÓN: {strength.label}
                  </span>
                </div>
              )}
            </div>
            <div className="onb-field">
              <label>Confirmar contraseña</label>
              <div className="hud-input-group">
                <Lock className="hud-input-icon" />
                <input
                  className="onb-select hud-field-input"
                  type="password"
                  value={confirm}
                  onChange={(e) => setConfirm(e.target.value)}
                  minLength={8}
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
                {busy ? "INICIALIZANDO…" : "INICIALIZAR OPERADOR"}
              </motion.button>
            </div>
          </form>
          {error && <p className="af-error">{error}</p>}
          <p className="onb-sub">
            ¿Ya tenés cuenta? <Link to="/login">Iniciar sesión</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
