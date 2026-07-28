import { FormEvent, useState } from "react";
import { clearCustomBackground, setCustomBackground } from "../api";
import { useUpdateUser, useUser } from "../context/UserContext";

// Fondo de página elegido a mano por el usuario. Tiene prioridad sobre el
// fondo auto-scrapeado del perfil de Steam (ver useSteamBackground en
// ProfileView) -- existe porque ese scraping puede fallar (rate-limit 429
// de Steam) o porque el usuario simplemente prefiere elegir su imagen.
export function BackgroundSettings() {
  const user = useUser();
  const updateUser = useUpdateUser();
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const me = await setCustomBackground(url.trim());
      updateUser({
        ...user,
        steam_background_url: me.steam_background_url,
        custom_background_url: me.custom_background_url,
      });
      setUrl("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo guardar el fondo.");
    } finally {
      setBusy(false);
    }
  };

  const handleClear = async () => {
    setBusy(true);
    setError(null);
    try {
      const me = await clearCustomBackground();
      updateUser({
        ...user,
        steam_background_url: me.steam_background_url,
        custom_background_url: me.custom_background_url,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo quitar el fondo.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="section-head">
        <span className="display">Fondo de página</span>
        <span className="rule" />
      </div>
      <div className="legend-card af-card">
        {user.custom_background_url ? (
          <>
            <div className="af-row">
              <span className="af-chip on">ACTIVO</span>
              <span className="af-meta">Estás usando una imagen propia como fondo.</span>
            </div>
            <button type="button" className="af-btn ghost" onClick={handleClear} disabled={busy}>
              Quitar
            </button>
          </>
        ) : (
          <>
            <p className="section-note">
              Pegá la URL de una imagen para usarla como fondo de la página, en vez del fondo de tu
              perfil de Steam (o la cuadrícula por defecto si tampoco se pudo traer).
            </p>
            <form className="af-form" onSubmit={handleSave}>
              <input
                className="af-input mono"
                placeholder="https://..."
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                aria-label="URL de imagen de fondo"
                required
              />
              <button type="submit" className="af-btn" disabled={busy}>
                {busy ? "Guardando…" : "Guardar"}
              </button>
            </form>
            {error && <p className="af-error">{error}</p>}
          </>
        )}
      </div>
    </>
  );
}
