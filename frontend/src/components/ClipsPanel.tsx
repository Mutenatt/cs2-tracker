import { useCallback, useEffect, useState } from "react";
import { clipDownloadUrl, createClip, getClips, getHighlights } from "../api";
import type { ClipJob, HighlightMoment } from "../types";

const POLL_MS = 4000;

const STATUS_LABEL: Record<ClipJob["status"], string> = {
  pending: "En cola…",
  rendering: "Renderizando…",
  done: "Listo",
  error: "Error",
};

// Momentos destacados del PROPIO usuario -> clips MP4 9:16 listos para
// redes (render 2D de radar server-side; ver backend infra/clips.py).
// Solo se monta en el perfil propio (el endpoint es privado, como monthly).
export function ClipsPanel({ steamid }: { steamid: string }) {
  const [moments, setMoments] = useState<HighlightMoment[] | null>(null);
  const [clips, setClips] = useState<ClipJob[]>([]);
  const [creating, setCreating] = useState<string | null>(null);

  const refreshClips = useCallback(() => {
    getClips(steamid)
      .then((r) => setClips(r.clips))
      .catch(() => undefined);
  }, [steamid]);

  useEffect(() => {
    setMoments(null);
    getHighlights(steamid)
      .then((r) => setMoments(r.moments))
      .catch(() => setMoments([]));
    refreshClips();
  }, [steamid, refreshClips]);

  // Mientras haya renders en curso, refrescar el estado periódicamente.
  const hayPendientes = clips.some((c) => c.status === "pending" || c.status === "rendering");
  useEffect(() => {
    if (!hayPendientes) return;
    const t = setInterval(refreshClips, POLL_MS);
    return () => clearInterval(t);
  }, [hayPendientes, refreshClips]);

  // Feature en desarrollo: se oculta el panel real y se muestra un placeholder
  // hasta que esté listo para producción. Reactivar cambiando a `true`.
  const CLIPS_ENABLED = false as boolean;
  if (!CLIPS_ENABLED) {
    return (
      <div className="panel-card">
        <div className="panel-title">Clips</div>
        <div className="panel-subtitle">En desarrollo — todavía no disponible.</div>
      </div>
    );
  }

  if (!moments || moments.length === 0) return null;

  const jobFor = (m: HighlightMoment) =>
    clips.find((c) => c.match_id === m.match_id && c.round_num === m.round_num);

  const generar = async (m: HighlightMoment) => {
    const key = `${m.match_id}:${m.round_num}`;
    setCreating(key);
    try {
      await createClip(steamid, m.match_id, m.round_num);
      refreshClips();
    } finally {
      setCreating(null);
    }
  };

  return (
    <div className="panel-card">
      <div className="panel-title">Clips</div>
      <div className="panel-subtitle">
        Tus momentos destacados, renderizados en 9:16 listos para subir
      </div>
      <div className="clip-rows">
        {moments.map((m) => {
          const job = jobFor(m);
          const key = `${m.match_id}:${m.round_num}`;
          return (
            <div className="clip-row" key={key}>
              <div>
                <div className="clip-label">{m.label}</div>
                <div className="clip-sub">
                  {(m.map ?? "—").toUpperCase()} · Ronda {m.round_num + 1}
                </div>
              </div>
              <div className="clip-action">
                {job?.status === "done" ? (
                  <a className="clip-btn" href={clipDownloadUrl(job.id)}>
                    Descargar
                  </a>
                ) : job && job.status !== "error" ? (
                  <span className="clip-status">{STATUS_LABEL[job.status]}</span>
                ) : m.demo_available ? (
                  <button
                    className="clip-btn"
                    disabled={creating === key}
                    onClick={() => generar(m)}
                  >
                    {job?.status === "error" ? "Reintentar" : "Generar clip"}
                  </button>
                ) : (
                  <span className="clip-status" title="El replay de Valve ya expiró">
                    demo expirado
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
