import { useEffect, useRef, useState } from "react";
import { getKills } from "../api";
import type { KillPoint } from "../types";

const SIZE = 512;

// Dibuja el heatmap de muertes sobre el radar del mapa en un <canvas>.
export function Heatmap({ map, matchId }: { map: string | null; matchId: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [msg, setMsg] = useState<string | null>("Cargando heatmap…");

  useEffect(() => {
    if (!map) return;
    let cancelled = false;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const img = new Image();
    let kills: KillPoint[] = [];
    let imgReady = false;

    function render() {
      if (!imgReady || cancelled || !ctx) return;
      ctx.clearRect(0, 0, SIZE, SIZE);
      ctx.globalAlpha = 0.5;
      ctx.drawImage(img, 0, 0, SIZE, SIZE);
      ctx.globalAlpha = 1;

      // capa de calor (aditiva)
      ctx.globalCompositeOperation = "lighter";
      for (const k of kills) {
        const x = k.u * SIZE;
        const y = k.v * SIZE;
        const g = ctx.createRadialGradient(x, y, 0, x, y, 26);
        g.addColorStop(0, "rgba(255,90,0,0.32)");
        g.addColorStop(1, "rgba(255,90,0,0)");
        ctx.fillStyle = g;
        ctx.beginPath();
        ctx.arc(x, y, 26, 0, Math.PI * 2);
        ctx.fill();
      }

      // puntos individuales (HS en blanco lleno)
      ctx.globalCompositeOperation = "source-over";
      for (const k of kills) {
        const x = k.u * SIZE;
        const y = k.v * SIZE;
        ctx.fillStyle = k.headshot ? "#ffffff" : "rgba(255,255,255,0.65)";
        ctx.beginPath();
        ctx.arc(x, y, 2.3, 0, Math.PI * 2);
        ctx.fill();
      }
      setMsg(kills.length ? null : "Sin datos de posición");
    }

    img.onload = () => {
      imgReady = true;
      render();
    };
    img.onerror = () => setMsg(`Sin radar para ${map}`);
    img.src = `/maps/${map}.png`;

    getKills(matchId)
      .then((r) => {
        if (cancelled) return;
        kills = r.kills;
        if (!r.has_radar) setMsg(`Sin radar para ${map}`);
        render();
      })
      .catch(() => setMsg("No se pudieron cargar las muertes"));

    return () => {
      cancelled = true;
    };
  }, [map, matchId]);

  if (!map) return null;
  return (
    <div className="card">
      <h3>Heatmap de muertes · {map}</h3>
      <div style={{ position: "relative", width: "100%", maxWidth: SIZE, margin: "0 auto" }}>
        <canvas
          ref={canvasRef}
          width={SIZE}
          height={SIZE}
          style={{ width: "100%", aspectRatio: "1 / 1", borderRadius: 8, display: "block" }}
        />
        {msg && (
          <div className="muted" style={{ position: "absolute", top: 8, left: 10 }}>
            {msg}
          </div>
        )}
      </div>
      <p className="muted" style={{ marginTop: 10 }}>
        Punto blanco lleno = headshot. Zonas cálidas = más muertes.
      </p>
    </div>
  );
}
