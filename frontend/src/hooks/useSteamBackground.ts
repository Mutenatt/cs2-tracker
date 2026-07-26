import { useEffect } from "react";

// Los backgrounds animados de Steam (Points Shop) vienen como .webm/.mp4 en
// vez de una imagen estática -- ver auth.py::_ProfileBackgroundParser.
const VIDEO_URL_RE = /\.(webm|mp4)(\?.*)?$/i;

const OVERLAY_GRADIENT = "linear-gradient(120deg, rgba(6, 12, 20, 0.9) 0%, rgba(6, 12, 20, 0.72) 100%)";

/**
 * Aplica el background de perfil de Steam del usuario logueado al <body>
 * mientras el componente que llama a este hook está montado, y lo limpia al
 * desmontar (navegar a otra vista). Pensado para usarse solo en las vistas
 * donde queremos ese fondo (Perfil), no globalmente en App.tsx.
 *
 * Soporta tanto imágenes estáticas (background-image en el body) como
 * backgrounds animados (video de fondo fixed detrás del contenido).
 */
export function useSteamBackground(url: string | null): void {
  useEffect(() => {
    const body = document.body;

    if (!url) return;

    if (VIDEO_URL_RE.test(url)) {
      const video = document.createElement("video");
      video.src = url;
      video.autoplay = true;
      video.muted = true;
      video.loop = true;
      video.playsInline = true;
      Object.assign(video.style, {
        position: "fixed",
        inset: "0",
        width: "100vw",
        height: "100vh",
        objectFit: "cover",
        // No usar un z-index negativo: el fondo propio del <body> se pinta
        // por encima y oculta el video. #root queda en la capa 1 (styles.css).
        zIndex: "0",
        pointerEvents: "none",
      });

      const overlay = document.createElement("div");
      Object.assign(overlay.style, {
        position: "fixed",
        inset: "0",
        background: OVERLAY_GRADIENT,
        zIndex: "0",
        pointerEvents: "none",
      });

      body.style.backgroundColor = "var(--ink)";
      body.prepend(overlay);
      body.prepend(video);

      return () => {
        video.remove();
        overlay.remove();
        body.style.backgroundColor = "";
      };
    }

    body.style.backgroundImage = `${OVERLAY_GRADIENT}, url(${url})`;
    body.style.backgroundColor = "var(--ink)";
    body.style.backgroundSize = "cover";
    body.style.backgroundPosition = "center";
    body.style.backgroundRepeat = "no-repeat";
    body.style.backgroundAttachment = "fixed";

    return () => {
      body.style.backgroundImage = "";
      body.style.backgroundColor = "";
      body.style.backgroundSize = "";
      body.style.backgroundPosition = "";
      body.style.backgroundRepeat = "";
      body.style.backgroundAttachment = "";
    };
  }, [url]);
}
