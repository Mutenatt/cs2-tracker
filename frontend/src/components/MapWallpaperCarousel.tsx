import { useEffect, useState } from "react";

// Rota entre todas las variantes de wallpaper disponibles para un mapa
// (frontend/public/maps-wallpaper/${map}_png.png, _1_, _2_, ...) con un
// crossfade. La cantidad de variantes no es fija por mapa, así que se
// sondean en runtime probando a cargar cada índice hasta el primer fallo.
const ROTATE_MS = 6000;
const MAX_VARIANTS = 8;

function probeImage(src: string): Promise<boolean> {
  return new Promise((resolve) => {
    const img = new Image();
    img.onload = () => resolve(true);
    img.onerror = () => resolve(false);
    img.src = src;
  });
}

export function MapWallpaperCarousel({ map }: { map: string }) {
  const [images, setImages] = useState<string[]>([]);
  const [active, setActive] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setImages([]);
    setActive(0);

    async function probe() {
      const found: string[] = [];
      const base = `/maps-wallpaper/${map}_png.png`;
      if (await probeImage(base)) found.push(base);
      for (let i = 1; i <= MAX_VARIANTS; i++) {
        if (cancelled) return;
        const src = `/maps-wallpaper/${map}_${i}_png.png`;
        if (!(await probeImage(src))) break;
        found.push(src);
      }
      if (!cancelled) setImages(found);
    }
    probe();

    return () => {
      cancelled = true;
    };
  }, [map]);

  useEffect(() => {
    if (images.length < 2) return;
    const id = setInterval(() => {
      setActive((a) => (a + 1) % images.length);
    }, ROTATE_MS);
    return () => clearInterval(id);
  }, [images]);

  return (
    <>
      {images.map((src, i) => (
        <img key={src} src={src} alt="" className={`wallpaper-frame${i === active ? " active" : ""}`} />
      ))}
    </>
  );
}
