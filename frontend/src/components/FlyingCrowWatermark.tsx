import { useEffect, useRef } from "react";

// Watermark de fondo del profile-hero: "Flying Crow" de MD. MURADUZZAMAN
// (IconScout), exportado como mp4 -- no el JSON de Lottie, así que se
// reproduce como <video> en vez de con lottie-player. El clip trae fondo
// blanco y el cuervo aleteando en el lugar (no se desplaza en el archivo
// fuente); el desplazamiento de izquierda a derecha por toda la tarjeta lo
// pone la animación CSS (.eagle-icon, eagle-flight en styles.css), y el
// blend "multiply" es lo que hace desaparecer el fondo blanco del clip
// contra el degradado morado (mix-blend-mode: screen/overlay no serviría
// acá porque lo que sobra es blanco, no negro).
export function FlyingCrowWatermark() {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      videoRef.current?.pause();
    }
  }, []);

  return (
    <div className="profile-hero-eagle" aria-hidden="true">
      {/* eagle-frame trae el recorrido (left + fade) y el vignette (mask-image)
          que difumina el borde recto del clip -- el fondo blanco del video
          desaparece con "multiply", pero la compresión del mp4 deja un
          resto de recuadro que sin este mask se nota como un "cuadrado"
          cruzando la tarjeta. */}
      <div className="eagle-frame">
        <video
          ref={videoRef}
          className="eagle-icon"
          src="/media/flying-crow.mp4"
          autoPlay
          loop
          muted
          playsInline
        />
        {/* Tiñe el cuervo con --tier-accent (la misma variable que pinta el
            fondo del hero, ver tierClass en RankBadge.tsx): mix-blend-mode:
            color toma el matiz/saturación de esta capa y conserva la
            luminosidad del video de abajo, el truco clásico de "duotono". */}
        <div className="eagle-tint" />
      </div>
    </div>
  );
}
