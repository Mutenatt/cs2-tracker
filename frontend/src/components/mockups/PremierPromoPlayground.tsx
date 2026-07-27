import { useState } from "react";
import { PremierRankUpEffect } from "../PremierRankUpEffect";
import { tierClass } from "../RankBadge";
import { isPromotionalMatch } from "../../lib/premierRating";

// Playground TEMPORAL para validar isPromotionalMatch() contra el cartel
// real (.premier-hero, mismas clases que ProfileView.tsx). Permite mover el
// rating a mano y confirmar que las flechas solo aparecen en X,999. Borrar
// esta carpeta + la ruta temporal en App.tsx una vez confirmado.

const PRESETS = [19850, 19999, 20000, 4999, 24999, 30000];

// Mismos colores que .profile-hero.t1..t7 en styles.css -- se define acá
// aparte porque el playground no vive dentro de .profile-hero.
const TIER_ACCENT: Record<string, string> = {
  t1: "#b0c3d9",
  t2: "#5e98d9",
  t3: "#6a8bff",
  t4: "#a86aff",
  t5: "#d32ce6",
  t6: "#eb4b4b",
  t7: "#e4ae39",
};

export function PremierPromoPlayground() {
  const [rating, setRating] = useState(19999);
  const isPromo = isPromotionalMatch(rating);
  const tier = tierClass(Math.max(rating, 0));

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 24,
        padding: "60px 20px",
        background: "#0a0a0f",
        fontFamily: "'IBM Plex Mono', monospace",
        color: "#cbd0d8",
      }}
    >
      <h1 style={{ fontSize: 15, letterSpacing: "0.08em", textTransform: "uppercase", color: "#8b93a1" }}>
        Playground — Partida de Ascenso (isPromotionalMatch)
      </h1>

      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <label>
          Rating:{" "}
          <input
            type="number"
            value={rating}
            onChange={(e) => setRating(Number(e.target.value) || 0)}
            style={{
              width: 110,
              padding: "4px 8px",
              background: "#14141c",
              border: "1px solid #333",
              borderRadius: 4,
              color: "#cbd0d8",
              fontFamily: "inherit",
            }}
          />
        </label>
        {PRESETS.map((p) => (
          <button
            key={p}
            onClick={() => setRating(p)}
            style={{
              padding: "4px 10px",
              background: rating === p ? "#a86aff" : "#14141c",
              border: "1px solid #333",
              borderRadius: 4,
              color: rating === p ? "#0a0a0f" : "#cbd0d8",
              fontFamily: "inherit",
              cursor: "pointer",
            }}
          >
            {p.toLocaleString("en-US")}
          </button>
        ))}
      </div>

      <div
        style={{
          fontSize: 12,
          color: isPromo ? "#7CFC8C" : "#8b93a1",
        }}
      >
        isPromotionalMatch({rating.toLocaleString("en-US")}) ={" "}
        <b>{String(isPromo)}</b> {isPromo && "→ ¡partida de ascenso, siguiente umbral a la vista!"}
      </div>

      <div className="premier-hero-row" style={{ ["--tier-accent" as string]: TIER_ACCENT[tier] } as React.CSSProperties}>
        <div className="premier-hero">
          {isPromo && <PremierRankUpEffect />}
          <span className={`ph-num mono ${tier}`}>{rating.toLocaleString("en-US")}</span>
        </div>
        <span className="ph-unit mono">CS RATING</span>
      </div>
    </div>
  );
}
