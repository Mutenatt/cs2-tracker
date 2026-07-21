import { useEffect, useState } from "react";
import type { StreamDto } from "../types";

// Carrusel hero 3D de streams (Twitch + Kick mezclados). Restricción clave:
// SOLO el slide activo monta un <iframe> del player — los demás renderizan la
// thumbnail estática (varios players simultáneos matan al navegador).

const AUTOPLAY_MS = 6000;
const viewersFmt = new Intl.NumberFormat("es-AR");

function playerUrl(s: StreamDto): string {
  if (s.platform === "kick") {
    return `https://player.kick.com/${s.channel_slug}?muted=true`;
  }
  // El player de Twitch exige declarar el host que lo embebe (parent):
  // dinámico para cubrir dev (localhost) y producción.
  return `https://player.twitch.tv/?channel=${s.channel_slug}&parent=${window.location.hostname}&autoplay=true&muted=true`;
}

// Posición del slide i relativa al activo, con wrap-around circular.
function slideClass(i: number, active: number, n: number): string {
  if (i === active) return "carousel-slide slide-active";
  if (i === (active + 1) % n) return "carousel-slide slide-next";
  if (i === (active - 1 + n) % n) return "carousel-slide slide-prev";
  return "carousel-slide slide-hidden";
}

export function HeroStreamCarousel({ streams }: { streams: StreamDto[] }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [hovered, setHovered] = useState(false);
  // El player de Twitch rechaza el autoplay si el iframe se inicializa con
  // opacidad/escala parciales ("minimum requirements: style visibility"), así
  // que el iframe se monta recién cuando la transición CSS (0.5s) terminó;
  // hasta entonces el slide activo muestra la thumbnail.
  const [playerLive, setPlayerLive] = useState(false);
  const n = streams.length;

  // Si la lista cambia (refetch) y el índice quedó fuera de rango, resetear.
  useEffect(() => {
    if (activeIndex >= n) setActiveIndex(0);
  }, [n, activeIndex]);

  useEffect(() => {
    setPlayerLive(false);
    const id = setTimeout(() => setPlayerLive(true), 600);
    return () => clearTimeout(id);
  }, [activeIndex]);

  useEffect(() => {
    if (n < 2 || hovered) return;
    const id = setInterval(() => setActiveIndex((i) => (i + 1) % n), AUTOPLAY_MS);
    return () => clearInterval(id);
  }, [n, hovered]);

  if (n === 0) return null;
  const active = streams[Math.min(activeIndex, n - 1)];

  return (
    <div
      className="carousel-container"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {streams.map((s, i) => {
        const cls = slideClass(i, activeIndex, n);
        const isActive = cls.includes("slide-active");
        return (
          <div
            key={s.url}
            className={cls}
            onClick={isActive ? undefined : () => setActiveIndex(i)}
            role={isActive ? undefined : "button"}
            aria-label={isActive ? undefined : `Ver stream de ${s.channel}`}
          >
            {isActive && playerLive ? (
              <iframe
                className="carousel-player"
                src={playerUrl(s)}
                title={s.channel}
                allow="autoplay; fullscreen"
                allowFullScreen
              />
            ) : (
              <>
                <img className="carousel-thumb" src={s.thumbnail_url} alt={s.channel} />
                {!isActive && <div className="carousel-dim" />}
              </>
            )}
          </div>
        );
      })}

      <div className="carousel-info">
        <div className="carousel-info-top">
          <span className={`platform-badge ${active.platform}`}>
            {active.platform.toUpperCase()}
          </span>
          <a className="carousel-channel" href={active.url} target="_blank" rel="noreferrer">
            {active.channel}
          </a>
          <span className="stream-lang">{active.language.toUpperCase()}</span>
        </div>
        <span className="carousel-title">{active.title}</span>
        <span className="carousel-viewers">● {viewersFmt.format(active.viewers)} espectadores</span>
      </div>

      {n > 1 && (
        <>
          <button
            className="carousel-arrow left"
            aria-label="Stream anterior"
            onClick={() => setActiveIndex((i) => (i - 1 + n) % n)}
          >
            ‹
          </button>
          <button
            className="carousel-arrow right"
            aria-label="Stream siguiente"
            onClick={() => setActiveIndex((i) => (i + 1) % n)}
          >
            ›
          </button>
        </>
      )}
    </div>
  );
}
