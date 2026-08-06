import { useEffect, useState } from "react";
import {
  changeEmail,
  changePassword,
  deleteAccount,
  forgotPassword,
  getLoginHistory,
  logoutAll,
  requestSteamRelink,
  totpActivate,
  totpDisable,
  totpEnroll,
} from "../api";
import { AutoFetchSettings } from "../components/AutoFetchSettings";
import { Button } from "../components/Button";
import { SmoothScroll } from "../components/motion/SmoothScroll";
import { useUser } from "../context/UserContext";
import type { LoginHistoryEntry } from "../types";

export function SettingsView() {
  const user = useUser();
  const [forgotBusy, setForgotBusy] = useState(false);
  const [forgotSent, setForgotSent] = useState(false);
  const [loggingOutAll, setLoggingOutAll] = useState(false);
  const [loggedOutAll, setLoggedOutAll] = useState(false);
  const [loginHistory, setLoginHistory] = useState<LoginHistoryEntry[]>([]);

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [changeBusy, setChangeBusy] = useState(false);
  const [changeError, setChangeError] = useState<string | null>(null);
  const [changeDone, setChangeDone] = useState(false);

  useEffect(() => {
    getLoginHistory()
      .then((r) => setLoginHistory(r.events))
      .catch(() => setLoginHistory([]));
  }, []);

  const handleSubmitChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setChangeError(null);
    if (newPassword.length < 8) {
      setChangeError("La contraseña nueva tiene que tener al menos 8 caracteres");
      return;
    }
    if (newPassword !== confirmPassword) {
      setChangeError("Las contraseñas nuevas no coinciden");
      return;
    }
    setChangeBusy(true);
    try {
      await changePassword(currentPassword, newPassword);
      setChangeDone(true);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (err) {
      setChangeError(err instanceof Error ? err.message : "no se pudo cambiar la contraseña");
    } finally {
      setChangeBusy(false);
    }
  };

  const [newEmail, setNewEmail] = useState("");
  const [emailPassword, setEmailPassword] = useState("");
  const [emailBusy, setEmailBusy] = useState(false);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [emailSent, setEmailSent] = useState(false);

  const handleSubmitChangeEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    setEmailError(null);
    setEmailBusy(true);
    try {
      await changeEmail(newEmail, emailPassword);
      setEmailSent(true);
      setNewEmail("");
      setEmailPassword("");
    } catch (err) {
      setEmailError(err instanceof Error ? err.message : "no se pudo cambiar el email");
    } finally {
      setEmailBusy(false);
    }
  };

  const handleForgotPassword = async () => {
    if (!user.email) return;
    setForgotBusy(true);
    try {
      await forgotPassword(user.email);
      setForgotSent(true);
    } finally {
      setForgotBusy(false);
    }
  };

  const [relinkPassword, setRelinkPassword] = useState("");
  const [relinkBusy, setRelinkBusy] = useState(false);
  const [relinkError, setRelinkError] = useState<string | null>(null);
  const [showRelinkForm, setShowRelinkForm] = useState(false);

  const handleSubmitRelink = async (e: React.FormEvent) => {
    e.preventDefault();
    setRelinkError(null);
    setRelinkBusy(true);
    try {
      const { redirect_url } = await requestSteamRelink(relinkPassword);
      window.location.href = redirect_url;
    } catch (err) {
      setRelinkError(err instanceof Error ? err.message : "no se pudo iniciar el cambio");
      setRelinkBusy(false);
    }
  };

  const [totpEnabled, setTotpEnabled] = useState(user.totp_enabled);
  const [totpStep, setTotpStep] = useState<"idle" | "enrolling" | "confirming" | "backup_codes">(
    "idle"
  );
  const [totpQr, setTotpQr] = useState<string | null>(null);
  const [totpSecret, setTotpSecret] = useState<string | null>(null);
  const [totpCode, setTotpCode] = useState("");
  const [totpBusy, setTotpBusy] = useState(false);
  const [totpError, setTotpError] = useState<string | null>(null);
  const [totpBackupCodes, setTotpBackupCodes] = useState<string[]>([]);
  const [totpBackupCodesSaved, setTotpBackupCodesSaved] = useState(false);
  const [totpDisablePassword, setTotpDisablePassword] = useState("");
  const [totpDisableBusy, setTotpDisableBusy] = useState(false);
  const [totpDisableError, setTotpDisableError] = useState<string | null>(null);

  const handleStartTotpEnroll = async () => {
    setTotpError(null);
    setTotpBusy(true);
    try {
      const r = await totpEnroll();
      setTotpQr(r.qr_png_base64);
      setTotpSecret(r.secret);
      setTotpStep("enrolling");
    } catch (err) {
      setTotpError(err instanceof Error ? err.message : "no se pudo iniciar el enrollment");
    } finally {
      setTotpBusy(false);
    }
  };

  const handleSubmitTotpActivate = async (e: React.FormEvent) => {
    e.preventDefault();
    setTotpError(null);
    setTotpBusy(true);
    try {
      const r = await totpActivate(totpCode);
      setTotpBackupCodes(r.backup_codes);
      setTotpStep("backup_codes");
      setTotpEnabled(true);
      setTotpCode("");
    } catch (err) {
      setTotpError(err instanceof Error ? err.message : "código inválido");
    } finally {
      setTotpBusy(false);
    }
  };

  const handleFinishTotpEnroll = () => {
    setTotpStep("idle");
    setTotpQr(null);
    setTotpSecret(null);
    setTotpBackupCodes([]);
    setTotpBackupCodesSaved(false);
  };

  const handleSubmitTotpDisable = async (e: React.FormEvent) => {
    e.preventDefault();
    setTotpDisableError(null);
    setTotpDisableBusy(true);
    try {
      await totpDisable(totpDisablePassword);
      setTotpEnabled(false);
      setTotpDisablePassword("");
    } catch (err) {
      setTotpDisableError(err instanceof Error ? err.message : "no se pudo desactivar 2FA");
    } finally {
      setTotpDisableBusy(false);
    }
  };

  const handleLogoutAll = async () => {
    if (!window.confirm("¿Cerrar sesión en todos los demás dispositivos?")) return;
    setLoggingOutAll(true);
    try {
      await logoutAll();
      setLoggedOutAll(true);
    } finally {
      setLoggingOutAll(false);
    }
  };

  const [deletePassword, setDeletePassword] = useState("");
  const [deleteConfirmText, setDeleteConfirmText] = useState("");
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handleSubmitDeleteAccount = async (e: React.FormEvent) => {
    e.preventDefault();
    setDeleteError(null);
    if (deleteConfirmText !== "ELIMINAR") {
      setDeleteError('Escribí "ELIMINAR" para confirmar');
      return;
    }
    if (!window.confirm("Esto borra tu cuenta de forma permanente. ¿Estás seguro?")) return;
    setDeleteBusy(true);
    try {
      await deleteAccount(deletePassword);
      window.location.href = "/";
    } catch (err) {
      setDeleteError(err instanceof Error ? err.message : "no se pudo borrar la cuenta");
      setDeleteBusy(false);
    }
  };

  return (
    <SmoothScroll>
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
        <form
          onSubmit={handleSubmitChangePassword}
          className="af-row"
          style={{ flexDirection: "column", gap: "0.5rem" }}
        >
          <input
            type="password"
            placeholder="Contraseña actual"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
          <input
            type="password"
            placeholder="Contraseña nueva"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            autoComplete="new-password"
            minLength={8}
            required
          />
          <input
            type="password"
            placeholder="Confirmar contraseña nueva"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            autoComplete="new-password"
            minLength={8}
            required
          />
          {changeError && <p className="af-meta error">{changeError}</p>}
          {changeDone && <p className="af-meta">Contraseña actualizada.</p>}
          <Button type="submit" disabled={changeBusy}>
            {changeBusy ? "Cambiando…" : "Cambiar contraseña"}
          </Button>
        </form>
        <Button onClick={handleForgotPassword} disabled={forgotBusy}>
          {forgotBusy
            ? "Enviando…"
            : forgotSent
              ? "Revisá tu email"
              : "¿Olvidaste tu contraseña actual?"}
        </Button>

        <form
          onSubmit={handleSubmitChangeEmail}
          className="af-row"
          style={{ flexDirection: "column", gap: "0.5rem", marginTop: "1rem" }}
        >
          <input
            type="email"
            placeholder="Email nuevo"
            value={newEmail}
            onChange={(e) => setNewEmail(e.target.value)}
            autoComplete="email"
            required
          />
          <input
            type="password"
            placeholder="Contraseña actual"
            value={emailPassword}
            onChange={(e) => setEmailPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
          {emailError && <p className="af-meta error">{emailError}</p>}
          {emailSent && <p className="af-meta">Revisá tu email nuevo para confirmar el cambio.</p>}
          <Button type="submit" disabled={emailBusy}>
            {emailBusy ? "Enviando…" : "Cambiar email"}
          </Button>
        </form>
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

        {!showRelinkForm ? (
          <Button onClick={() => setShowRelinkForm(true)}>Cambiar cuenta de Steam</Button>
        ) : (
          <form
            onSubmit={handleSubmitRelink}
            className="af-row"
            style={{ flexDirection: "column", gap: "0.5rem" }}
          >
            <p className="af-meta">
              Vas a autenticar una cuenta de Steam distinta; reemplaza a la actual.
            </p>
            <input
              type="password"
              placeholder="Contraseña actual"
              value={relinkPassword}
              onChange={(e) => setRelinkPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
            {relinkError && <p className="af-meta error">{relinkError}</p>}
            <Button type="submit" disabled={relinkBusy}>
              {relinkBusy ? "Redirigiendo…" : "Continuar con Steam"}
            </Button>
          </form>
        )}
      </div>

      <div className="section-head">
        <span className="display">Seguridad</span>
        <span className="rule" />
      </div>

      <div className="legend-card af-card">
        <p className="af-meta">Autenticación en dos pasos (2FA)</p>

        {totpStep === "idle" && !totpEnabled && (
          <>
            <Button onClick={handleStartTotpEnroll} disabled={totpBusy}>
              {totpBusy ? "Iniciando…" : "Activar 2FA"}
            </Button>
            {totpError && <p className="af-meta error">{totpError}</p>}
          </>
        )}

        {totpStep === "enrolling" && totpQr && (
          <form
            onSubmit={handleSubmitTotpActivate}
            className="af-row"
            style={{ flexDirection: "column", gap: "0.5rem" }}
          >
            <p className="af-meta">Escaneá este código con tu app de autenticación:</p>
            <img
              src={`data:image/png;base64,${totpQr}`}
              alt="Código QR de 2FA"
              width={180}
              height={180}
            />
            {totpSecret && (
              <p className="af-meta mono">
                ¿No podés escanear? Ingresá el código manualmente: {totpSecret}
              </p>
            )}
            <input
              type="text"
              inputMode="numeric"
              placeholder="Código de 6 dígitos"
              value={totpCode}
              onChange={(e) => setTotpCode(e.target.value)}
              required
            />
            {totpError && <p className="af-meta error">{totpError}</p>}
            <Button type="submit" disabled={totpBusy}>
              {totpBusy ? "Confirmando…" : "Confirmar"}
            </Button>
          </form>
        )}

        {totpStep === "backup_codes" && (
          <div className="af-row" style={{ flexDirection: "column", gap: "0.5rem" }}>
            <p className="af-meta">
              Guardá estos códigos de respaldo en un lugar seguro. Cada uno sirve para un solo login
              si perdés acceso a tu app de autenticación. No se muestran de nuevo.
            </p>
            <ul className="mono">
              {totpBackupCodes.map((code) => (
                <li key={code}>{code}</li>
              ))}
            </ul>
            <label className="af-row">
              <input
                type="checkbox"
                checked={totpBackupCodesSaved}
                onChange={(e) => setTotpBackupCodesSaved(e.target.checked)}
              />
              Ya los guardé
            </label>
            <Button onClick={handleFinishTotpEnroll} disabled={!totpBackupCodesSaved}>
              Listo
            </Button>
          </div>
        )}

        {totpStep === "idle" && totpEnabled && (
          <form
            onSubmit={handleSubmitTotpDisable}
            className="af-row"
            style={{ flexDirection: "column", gap: "0.5rem" }}
          >
            <p className="af-meta">2FA está activo en tu cuenta.</p>
            <input
              type="password"
              placeholder="Contraseña"
              value={totpDisablePassword}
              onChange={(e) => setTotpDisablePassword(e.target.value)}
              autoComplete="current-password"
              required
            />
            {totpDisableError && <p className="af-meta error">{totpDisableError}</p>}
            <Button type="submit" disabled={totpDisableBusy}>
              {totpDisableBusy ? "Desactivando…" : "Desactivar 2FA"}
            </Button>
          </form>
        )}
      </div>

      <div className="legend-card af-card">
        <Button onClick={handleLogoutAll} disabled={loggingOutAll}>
          {loggingOutAll
            ? "Cerrando sesiones…"
            : loggedOutAll
              ? "Listo"
              : "Cerrar sesión en todos los demás dispositivos"}
        </Button>
      </div>

      {loginHistory.length > 0 && (
        <div className="legend-card af-card">
          <p className="af-meta">Actividad reciente de inicio de sesión</p>
          <table className="mono" style={{ width: "100%", fontSize: "0.85em" }}>
            <tbody>
              {loginHistory.map((e, i) => (
                <tr key={i}>
                  <td>{new Date(e.occurred_at).toLocaleString()}</td>
                  <td>{e.ip ?? "—"}</td>
                  <td>{e.success ? "✓" : `✗ (${e.reason ?? "?"})`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="section-head">
        <span className="display">Zona de peligro</span>
        <span className="rule" />
      </div>
      <div className="legend-card af-card">
        <form
          onSubmit={handleSubmitDeleteAccount}
          className="af-row"
          style={{ flexDirection: "column", gap: "0.5rem" }}
        >
          <p className="af-meta">
            Esto borra tu cuenta de forma permanente. El historial de partidas compartidas con otros
            jugadores no se ve afectado.
          </p>
          <input
            type="password"
            placeholder="Contraseña"
            value={deletePassword}
            onChange={(e) => setDeletePassword(e.target.value)}
            autoComplete="current-password"
            required
          />
          <input
            type="text"
            placeholder='Escribí "ELIMINAR" para confirmar'
            value={deleteConfirmText}
            onChange={(e) => setDeleteConfirmText(e.target.value)}
            required
          />
          {deleteError && <p className="af-meta error">{deleteError}</p>}
          <Button type="submit" disabled={deleteBusy}>
            {deleteBusy ? "Borrando…" : "Borrar mi cuenta"}
          </Button>
        </form>
      </div>

      <AutoFetchSettings />
    </SmoothScroll>
  );
}
