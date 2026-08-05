export type ZoneGlow = "go" | "recon" | "none";

export interface ZoneVisual {
  color: string;
  glow: ZoneGlow;
}

interface Props {
  head: ZoneVisual;
  body: ZoneVisual;
  legs: ZoneVisual;
}

function filterFor(glow: ZoneGlow): string | undefined {
  if (glow === "go") return "url(#accuracy-glow-go)";
  if (glow === "recon") return "url(#accuracy-glow-recon)";
  return undefined;
}

// Silueta propia (no es un asset del juego), zonas como <polygon> separados
// para poder colorear y aplicar glow cada uno por código según cuál
// concentra más impactos (ver AccuracyPanel::zoneVisuals).
export function AccuracySilhouette({ head, body, legs }: Props) {
  const bodyOpacity = body.glow === "none" ? 0.4 : 1;
  const legsOpacity = legs.glow === "none" ? 0.4 : 1;
  const headOpacity = head.glow === "none" ? 0.4 : 1;

  return (
    <svg viewBox="0 0 60 130" style={{ width: 44, height: 96, flex: "0 0 auto" }}>
      <defs>
        <filter id="accuracy-glow-go" x="-60%" y="-60%" width="220%" height="220%">
          <feDropShadow
            dx="0"
            dy="0"
            stdDeviation="1.6"
            floodColor="var(--go)"
            floodOpacity="0.8"
          />
        </filter>
        <filter id="accuracy-glow-recon" x="-60%" y="-60%" width="220%" height="220%">
          <feDropShadow
            dx="0"
            dy="0"
            stdDeviation="1.6"
            floodColor="var(--recon)"
            floodOpacity="0.8"
          />
        </filter>
      </defs>

      <polygon
        points="26,13 34,13 37,20 35,27 25,27 23,20"
        fill={head.color}
        fillOpacity={headOpacity}
        filter={filterFor(head.glow)}
      />
      <polygon
        points="25,31 35,31 39,43 37,71 30,84 23,71 21,43"
        fill={body.color}
        fillOpacity={bodyOpacity}
        filter={filterFor(body.glow)}
      />
      <polygon
        points="23.5,31 14,39 12,71 21,72 19,44"
        fill={body.color}
        fillOpacity={bodyOpacity}
        filter={filterFor(body.glow)}
      />
      <polygon
        points="36.5,31 46,39 48,71 39,72 41,44"
        fill={body.color}
        fillOpacity={bodyOpacity}
        filter={filterFor(body.glow)}
      />
      <polygon
        points="22,73 29,86 26,125 19,125"
        fill={legs.color}
        fillOpacity={legsOpacity}
        filter={filterFor(legs.glow)}
      />
      <polygon
        points="38,73 31,86 34,125 41,125"
        fill={legs.color}
        fillOpacity={legsOpacity}
        filter={filterFor(legs.glow)}
      />
    </svg>
  );
}
